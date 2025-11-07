# 🗽 Metro-North Total Travel Time Optimizer

Calculate the **fastest total commute** to **Grand Central Terminal**, combining both **driving time** (via OpenStreetMap) and **scheduled train time** (from official MTA Metro-North GTFS data).

This tool determines which **station** gives you the **shortest total door-to-terminal travel time** for a given **date** and **desired arrival time** at Grand Central.

---

## 🚀 Features

- ✅ Calculates **scheduled train times** from every Metro-North station to Grand Central  
- 🚗 Computes **driving times** from any address to all Metro-North stations (via OpenStreetMap / OSRM)  
- 🧩 Combines both to find the **optimal station** for your trip  
- 📅 Supports specific **arrival dates and times** (weekday vs. weekend schedules)  
- 💾 Outputs detailed CSVs for further analysis  

---

## 🧱 Repository Structure

```
.
├── tt2gc.py                                # Builds schedule-based train times to GCT
├── optimal_combined_trip.py                 # Finds best total travel time (drive + train)
├── requirements.txt                         # Dependencies for Python 3.10
└── README.md                                # Documentation
```

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/<yourusername>/<yourrepo>.git
cd <yourrepo>

# Create a Python 3.10 virtual environment
python3.10 -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)

# Install dependencies
pip install -r requirements.txt
```

---

## 🧮 Usage

### 1️⃣ Generate Train Schedule Data
Run this first to compute train travel times to Grand Central:

```bash
python tt2gc.py
```

You’ll be prompted for:
```
Enter target date (YYYY-MM-DD):
Enter target arrival time at Grand Central (HH:MM, 24-hour):
```

This creates:
```
metro_north_train_times_for_arrival.csv
```

---

### 2️⃣ Compute Optimal Total Travel

Then, run:

```bash
python optimal_combined_trip.py
```

You’ll be prompted for:
```
Enter your starting address:
Enter target date (YYYY-MM-DD):
Enter target arrival time at Grand Central (HH:MM, 24-hour):
```

The script will:
- Geocode your address  
- Compute driving times to every Metro-North station  
- Combine them with train travel times  
- Output:

```
optimal_metro_north_trip.csv
```

and display the **best station** recommendation.

---

## 📄 Example Output

```
🏆 Best Option:
  Station: White Plains Station (Harlem Line)
  Drive time: 5.3 min
  Train time: 39.0 min
  Total travel: 44.3 min
  Depart station by: 07:49 → Arrive GCT at 08:28
```

---

## 🗺️ Data Sources

- **Train schedules:** MTA Metro-North official GTFS feed  
  https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip  
- **Driving times:** OpenStreetMap / OSRM public routing API  
  https://project-osrm.org/

---

## 🧩 Dependencies

- `pandas`  
- `geopy`  
- `requests`

Install them manually with:
```bash
pip install pandas geopy requests
```

---

## 🧠 Notes

- OSRM provides **driving time estimates** (not live traffic).  
- Train times are based on **published GTFS schedules** (not real-time).  
- Add a `.gitignore` to exclude your `venv/` and `__pycache__/` directories.  

---

## 🏗️ Future Enhancements

- Include walking or drop-off buffers  
- Add “next available train” option if you miss target arrival  
- Cache OSRM results for repeated runs  
