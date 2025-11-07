#!/usr/bin/env python3
"""
Calculate scheduled Metro-North train travel times to Grand Central Terminal
for a specific target arrival time and date.

Prompts user for:
    - Target date (YYYY-MM-DD)
    - Target arrival time at Grand Central (HH:MM, 24-hour)

Output: metro_north_train_times_for_arrival.csv
"""

import requests
import pandas as pd
import io
import zipfile
from datetime import datetime

# --- Constants ---
GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip"
DESTINATION_NAME = "Grand Central Terminal"


def to_minutes(t):
    """Convert HH:MM:SS → minutes since midnight (handles 24h+ for overnight trips)."""
    try:
        h, m, s = map(int, t.split(":"))
        return h * 60 + m + s / 60
    except Exception:
        return None


# --- Step 1: User input ---
target_date_str = input("Enter target date (YYYY-MM-DD): ").strip()
target_time_str = input("Enter target arrival time at Grand Central (HH:MM, 24-hour): ").strip()

target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
target_time = datetime.strptime(target_time_str, "%H:%M").time()
target_arrival_min = target_time.hour * 60 + target_time.minute
weekday = target_date.strftime("%A").lower()

print(f"\nAnalyzing Metro-North schedules for trains arriving by {target_time_str} on {weekday.title()}...")

# --- Step 2: Download GTFS feed ---
r = requests.get(GTFS_URL)
r.raise_for_status()

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    stops = pd.read_csv(z.open("stops.txt"))
    stop_times = pd.read_csv(z.open("stop_times.txt"))
    trips = pd.read_csv(z.open("trips.txt"))
    routes = pd.read_csv(z.open("routes.txt"))
    calendar = pd.read_csv(z.open("calendar.txt"))

# --- Step 3: Filter for active services on target date ---
calendar["start_date"] = pd.to_datetime(calendar["start_date"], format="%Y%m%d")
calendar["end_date"] = pd.to_datetime(calendar["end_date"], format="%Y%m%d")

active_services = calendar[
    (calendar["start_date"] <= target_date)
    & (calendar["end_date"] >= target_date)
    & (calendar[weekday] == 1)
]["service_id"].unique()

trips = trips[trips["service_id"].isin(active_services)]

# --- Step 4: Merge tables ---
st = stop_times.merge(trips, on="trip_id", how="inner")
st = st.merge(routes[["route_id", "route_long_name"]], on="route_id", how="left")

# --- Step 5: Find Grand Central stop_id(s) ---
dest_ids = stops.loc[
    stops["stop_name"].str.contains(DESTINATION_NAME, case=False, na=False),
    "stop_id"
].unique()

if len(dest_ids) == 0:
    raise ValueError("Could not find Grand Central Terminal in stops.txt")

# --- Step 6: Convert times ---
st["arrival_min"] = st["arrival_time"].apply(to_minutes)
st["departure_min"] = st["departure_time"].apply(to_minutes)

# --- Step 7: Find trips that arrive at Grand Central before or at target time ---
dest_trips = st[
    (st["stop_id"].isin(dest_ids)) & (st["arrival_min"] <= target_arrival_min)
][["trip_id", "arrival_min"]].rename(columns={"arrival_min": "dest_arrival_min"})

# --- Step 8: Join and compute travel times ---
merged = st.merge(dest_trips, on="trip_id", how="inner")
merged = merged[merged["arrival_min"] < merged["dest_arrival_min"]]
merged["travel_time_min"] = merged["dest_arrival_min"] - merged["departure_min"]

# --- Step 9: Select most recent trip before target arrival per station ---
best = (
    merged.sort_values("dest_arrival_min", ascending=False)
    .groupby(["stop_id", "stop_name", "route_long_name"], as_index=False)
    .first()
)

best = best[["stop_name", "route_long_name", "departure_min", "dest_arrival_min", "travel_time_min"]]

# --- Step 10: Format for output ---
best.rename(
    columns={
        "route_long_name": "Line",
        "departure_min": "Departure_Min",
        "dest_arrival_min": "Arrival_Min",
        "travel_time_min": "Train_Travel_Min",
    },
    inplace=True,
)

best["Train_Travel_Min"] = best["Train_Travel_Min"].round(1)

def fmt_time(m):
    if pd.isna(m):
        return ""
    return f"{int(m//60):02d}:{int(m%60):02d}"

best["Scheduled_Departure"] = best["Departure_Min"].apply(fmt_time)
best["Scheduled_Arrival"] = best["Arrival_Min"].apply(fmt_time)

# --- Step 11: Clean and sort ---
best = best[~best["stop_name"].str.contains("Grand Central", case=False)]
best = best.sort_values("Train_Travel_Min").reset_index(drop=True)

# --- Step 12: Output ---
print("\nClosest scheduled trains arriving by target time:")
print(best[["stop_name", "Line", "Scheduled_Departure", "Scheduled_Arrival", "Train_Travel_Min"]].head(15))

best.to_csv("metro_north_train_times_for_arrival.csv", index=False)
print("\n✅ Saved to metro_north_train_times_for_arrival.csv")
