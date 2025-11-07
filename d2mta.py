import requests
import pandas as pd
import io
import zipfile
import time

# --- Input ---
origin_address = "123 Main St, White Plains, NY"  # Replace with your address

# --- Helper: Geocode an address using Nominatim ---
def geocode(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    r = requests.get(url, params=params, headers={"User-Agent": "MetroNorthMapper/1.0"})
    r.raise_for_status()
    data = r.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])

# --- Helper: Get driving distance & time via OSRM ---
def osrm_route(lat1, lon1, lat2, lon2):
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "false"}
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    if "routes" in data and data["routes"]:
        route = data["routes"][0]
        distance_miles = route["distance"] / 1609.34
        duration_minutes = route["duration"] / 60
        return distance_miles, duration_minutes
    return None, None

# --- Step 1: Geocode the origin address ---
origin_lat, origin_lon = geocode(origin_address)
if origin_lat is None:
    raise ValueError("Could not geocode origin address.")
print(f"Origin located at ({origin_lat:.5f}, {origin_lon:.5f})")

# --- Step 2: Download Metro-North GTFS feed ---
gtfs_url = "https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip"
r = requests.get(gtfs_url)
r.raise_for_status()

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    # Load necessary GTFS tables
    stops = pd.read_csv(z.open("stops.txt"))
    stop_times = pd.read_csv(z.open("stop_times.txt"))
    trips = pd.read_csv(z.open("trips.txt"))
    routes = pd.read_csv(z.open("routes.txt"))

# --- Step 3: Map stops → trips → routes to get line name per stop ---
# Get representative route_id per stop_id
stop_to_route = (
    stop_times.merge(trips[["trip_id", "route_id"]], on="trip_id", how="left")
    .groupby("stop_id")["route_id"]
    .agg(lambda x: x.mode().iat[0] if not x.mode().empty else None)
    .reset_index()
)

# Merge route info (line names)
stop_to_route = stop_to_route.merge(routes[["route_id", "route_long_name"]], on="route_id", how="left")

# Merge with stops to get station details
stations = stops.merge(stop_to_route, on="stop_id", how="left")

# Simplify columns
stations = stations[["stop_id", "stop_name", "stop_lat", "stop_lon", "route_long_name"]].drop_duplicates()
stations.rename(columns={"route_long_name": "Line"}, inplace=True)

# --- Step 4: Compute distances/times ---
results = []
print(f"Calculating distances to {len(stations)} stations...")

for i, row in stations.iterrows():
    name, lat, lon, line = row["stop_name"], row["stop_lat"], row["stop_lon"], row["Line"]
    try:
        dist_mi, dur_min = osrm_route(origin_lat, origin_lon, lat, lon)
        if dist_mi is not None:
            results.append({
                "Station": name,
                "Line": line,
                "Distance_mi": round(dist_mi, 2),
                "Duration_min": round(dur_min, 1)
            })
    except Exception as e:
        print(f"Error with {name}: {e}")
    time.sleep(0.2)  # gentle on API

# --- Step 5: Display results ---
df = pd.DataFrame(results).dropna()
df = df.sort_values("Distance_mi").reset_index(drop=True)

print("\nClosest 20 Metro-North stations:")
print(df.head(20))

# Save all results
df.to_csv("metro_north_full_station_distances.csv", index=False)
print("\n✅ Saved to metro_north_full_station_distances.csv")
