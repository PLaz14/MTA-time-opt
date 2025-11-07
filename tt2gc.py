#!/usr/bin/env python3
"""
tt2gc.py
---------
Compute *real-time* Metro-North travel times to Grand Central Terminal
using the public GTFS-Realtime feed (no API key required).

Requires:
    pip install pandas requests protobuf gtfs-realtime-bindings pytz

Usage:
    python tt2gc.py
"""

import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import pytz

# --- Constants ---
# Public realtime GTFS feed (no key required)
REALTIME_FEED_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr"

# Grand Central Terminal stop identifiers usually contain "GCT"
TARGET_DEST = "Grand Central Terminal"


# --- Step 1: Fetch realtime feed ---
def fetch_realtime():
    print("📡 Fetching Metro-North real-time feed (no API key)...")
    r = requests.get(REALTIME_FEED_URL, timeout=20)
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    print(f"✅ Loaded {len(feed.entity)} real-time entities.")
    return feed


# --- Step 2: Parse GTFS-RT into a structured DataFrame ---
def parse_realtime(feed):
    rows = []
    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip = entity.trip_update.trip
            route_id = trip.route_id
            trip_id = trip.trip_id
            breakpoint()
            for stu in entity.trip_update.stop_time_update:
                stop_id = stu.stop_id
                arr = getattr(stu.arrival, "time", None)
                dep = getattr(stu.departure, "time", None)
                if arr or dep:
                    rows.append({
                        "trip_id": trip_id,
                        "route_id": route_id,
                        "stop_id": stop_id,
                        "predicted_arrival": arr,
                        "predicted_departure": dep
                    })
    df = pd.DataFrame(rows)
    print(f"✅ Parsed {len(df)} realtime stop updates.")
    return df


# --- Step 3: Compute travel times to Grand Central ---
def compute_travel_times(df):
    if df.empty:
        raise ValueError("No realtime data found!")

    # Identify destination stop IDs
    dest_ids = [sid for sid in df["stop_id"].unique() if TARGET_DEST in sid]
    if not dest_ids:
        raise ValueError(f"No stop_id containing '{TARGET_DEST}' found in feed.")

    # Get arrival times at GCT for each trip
    dests = df[df["stop_id"].isin(dest_ids)][["trip_id", "predicted_arrival"]]
    dests = dests.rename(columns={"predicted_arrival": "arrival_GCT"})

    # Merge to compute live travel times for each upstream stop
    merged = df.merge(dests, on="trip_id", how="inner")
    merged = merged[merged["predicted_arrival"] < merged["arrival_GCT"]]
    merged["travel_time_min"] = (merged["arrival_GCT"] - merged["predicted_arrival"]) / 60.0

    # Convert UNIX timestamps to readable times (Eastern Time)
    est = pytz.timezone("America/New_York")
    merged["predicted_arrival"] = pd.to_datetime(merged["predicted_arrival"], unit="s", utc=True).dt.tz_convert(est)
    merged["arrival_GCT"] = pd.to_datetime(merged["arrival_GCT"], unit="s", utc=True).dt.tz_convert(est)

    # Simplify output
    summary = (
        merged.groupby(["stop_id", "route_id"], as_index=False)
        .agg({
            "predicted_arrival": "min",
            "arrival_GCT": "min",
            "travel_time_min": "min"
        })
        .sort_values("travel_time_min")
        .reset_index(drop=True)
    )

    summary.rename(columns={
        "stop_id": "Origin_Stop_ID",
        "route_id": "Line",
        "predicted_arrival": "Departure_Time",
        "arrival_GCT": "Arrival_GCT",
        "travel_time_min": "Live_Travel_Min"
    }, inplace=True)

    print("✅ Computed live travel times successfully.")
    return summary


# --- Step 4: Main Entry Point ---
if __name__ == "__main__":
    feed = fetch_realtime()
    df = parse_realtime(feed)
    results = compute_travel_times(df)

    output_file = f"live_tt2gc_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    results.to_csv(output_file, index=False)

    print(f"\n📄 Results saved to {output_file}")
    print(results.head(15))
