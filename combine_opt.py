#!/usr/bin/env python3
"""
Find the optimal Metro-North station to depart from,
minimizing total travel time (driving + train)
to Grand Central Terminal for a given arrival time and date.

Requires:
- metro_north_train_times_for_arrival.csv (from train script)
- OpenStreetMap driving times (computed live via OSRM)

Dependencies:
    pip install pandas geopy requests
"""

import requests
import pandas as pd
from geopy.geocoders import Nominatim
import time
from datetime import datetime

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
STATION_FILE = "metro_north_train_times_for_arrival.csv"

# --- Helper functions ---
def get_coordinates(address):
    geolocator = Nominatim(user_agent="mnr_trip_optimizer")
    location = geolocator.geocode(address)
    if not location:
        raise ValueError(f"Could not geocode address: {address}")
    return location.latitude, location.longitude


def get_osrm_time_distance(origin_lat, origin_lon, dest_lat, dest_lon):
    """Query OSRM for driving route between two coordinates."""
    url = f"{OSRM_URL}{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        route = data["routes"][0]
        return route["duration"] / 60.0, route["distance"] / 1000.0  # minutes, km
    except Exception:
        return None, None


# --- Load train data ---
train_df = pd.read_csv(STATION_FILE)

if "stop_name" not in train_df.columns or "Train_Travel_Min" not in train_df.columns:
    raise ValueError("Train CSV missing required columns. Run train script first.")

# --- Get user input ---
address = input("Enter your starting address: ").strip()
target_date_str = input("Enter target date (YYYY-MM-DD): ").strip()
target_time_str = input("Enter target arrival time at Grand Central (HH:MM, 24-hour): ").strip()

target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
target_time = datetime.strptime(target_time_str, "%H:%M").time()
target_arrival_min = target_time.hour * 60 + target_time.minute

print(f"\nCalculating best Metro-North station for arrival by {target_time_str} on {target_date_str}...")
print("Geocoding your address and computing driving times...\n")

# --- Load station data (via GTFS stops) ---
# Use the same GTFS feed for station coordinates
GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip"

import io, zipfile
r = requests.get(GTFS_URL)
r.raise_for_status()
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    stops = pd.read_csv(z.open("stops.txt"))

# Match station names from train data to stops.txt
station_coords = []
for _, row in train_df.iterrows():
    match = stops[stops["stop_name"].str.contains(row["stop_name"], case=False, na=False)]
    if not match.empty:
        station_coords.append({
            "stop_name": row["stop_name"],
            "stop_lat": match.iloc[0]["stop_lat"],
            "stop_lon": match.iloc[0]["stop_lon"],
        })
station_df = pd.DataFrame(station_coords)

# Merge with train travel times
stations = pd.merge(train_df, station_df, on="stop_name", how="left")

# --- Compute driving times ---
origin_lat, origin_lon = get_coordinates(address)
results = []

for _, row in stations.iterrows():
    if pd.isna(row["stop_lat"]) or pd.isna(row["stop_lon"]):
        continue
    drive_time, drive_dist = get_osrm_time_distance(
        origin_lat, origin_lon, row["stop_lat"], row["stop_lon"]
    )
    if drive_time is None:
        continue
    total_time = drive_time + row["Train_Travel_Min"]

    results.append({
        "Station": row["stop_name"],
        "Line": row["Line"],
        "Drive_Min": round(drive_time, 1),
        "Drive_Km": round(drive_dist, 1),
        "Train_Travel_Min": row["Train_Travel_Min"],
        "Scheduled_Departure": row.get("Scheduled_Departure", ""),
        "Scheduled_Arrival": row.get("Scheduled_Arrival", ""),
        "Total_Travel_Min": round(total_time, 1)
    })

    time.sleep(0.2)  # be gentle with OSRM server

# --- Rank and output results ---
results_df = pd.DataFrame(results)
results_df = results_df.sort_values("Total_Travel_Min").reset_index(drop=True)

print("\n🚄 Recommended routes (sorted by total travel time):")
print(results_df.head(10))

results_df.to_csv("optimal_metro_north_trip.csv", index=False)
print("\n✅ Saved full results to optimal_metro_north_trip.csv")

best = results_df.iloc[0]
print(f"\n🏆 Best Option:")
print(f"  Station: {best['Station']} ({best['Line']})")
print(f"  Drive time: {best['Drive_Min']} min")
print(f"  Train time: {best['Train_Travel_Min']} min")
print(f"  Total travel: {best['Total_Travel_Min']} min")
print(f"  Depart station by: {best['Scheduled_Departure']} → Arrive GCT at {best['Scheduled_Arrival']}")
