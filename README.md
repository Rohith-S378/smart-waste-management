# SmartWaste — Municipal Waste Management System

A fully modular, menu-driven smart waste collection and route management system
built in Python with a Flask web dashboard for real-time simulation.

---

## Features

| Module | Details |
|---|---|
| **Zone & Bin Management** | N zones, 4 waste types, fill history, critical detection |
| **Vehicle Management** | Capacity, fuel, maintenance, anti-double-assignment |
| **Driver & Staff** | Working hours, overtime, salary calculation |
| **Route Optimisation** | Nearest-neighbour Dijkstra, distance matrix, fuel-aware |
| **Collection Scheduling** | Priority sort, HazMat rules, zone coverage |
| **Waste Simulation** | Bin reset, load update, fuel deduction, log maintenance |
| **Emergency Handling** | Overflow trigger, nearest vehicle dispatch, schedule override |
| **Fuel & Cost Report** | Per-vehicle fuel, staff salary, daily total |
| **Recycling Report** | By type, recyclable %, landfill estimate |
| **Zone Report** | Avg fill, critical count, serviced count |

---

## Quick Start

### Web Dashboard (recommended)
```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

### Terminal CLI
```bash
python main.py
```

---

## Project Structure

```
smart-waste-management/
├── app.py               ← Flask web dashboard
├── main.py              ← Terminal menu-driven version
├── Procfile             ← Render deployment
├── requirements.txt
├── config/settings.py   ← All constants
├── models/
│   ├── bin.py           ← Bin, Zone dataclasses
│   ├── truck.py         ← Vehicle, Driver dataclasses
│   └── environment.py   ← SimulationState, CollectionLog
├── simulation/
│   ├── simulator.py     ← WasteSimulator engine
│   └── events.py        ← Random event generators
├── logic/
│   ├── priority.py      ← identifyCriticalBins, sort
│   ├── assignment.py    ← assignVehicle, buildSchedule
│   └── routing.py       ← optimizeRoutes (Dijkstra)
├── utils/
│   ├── helpers.py       ← File I/O, validation, reports
│   └── distance.py      ← Distance matrix, path algorithms
├── data/sample_data.json
└── templates/index.html ← Full dashboard UI
```

---

## Deploy to Render

1. Push to GitHub
2. Go to render.com → New Web Service
3. Connect repo, set:
   - Runtime: **Python 3**
   - Build: `pip install -r requirements.txt`
   - Start: `python app.py`
   - Region: **Singapore** (closest to Chennai)
4. Deploy!

---

## Constraints Implemented

- ✅ Vehicle cannot exceed maximum waste capacity
- ✅ Bin cannot be collected more than once per day
- ✅ Bin ID and Vehicle ID are unique
- ✅ Hazardous waste → HazMat vehicle only
- ✅ Driver hours cannot exceed daily limit (overtime tracked)
- ✅ Fuel sufficiency check before assignment
- ✅ No double-assignment of vehicle to multiple routes
- ✅ No driver assigned to multiple vehicles
- ✅ Maintenance blocks vehicle after 500 km
- ✅ Emergency bins override normal schedule
- ✅ Route distance limit per day (200 km)

---

## Algorithm — Scheduling & Route

```
1. Identify bins ≥ FILL_THRESHOLD (default 70%)
2. Sort by priority: Hazardous → Overflow → fill% desc
3. For each bin, find best vehicle:
   - Same zone preferred
   - Capacity & fuel check
   - HazMat constraint
   - Driver hours check
4. Nearest-neighbour route optimisation per vehicle
5. Simulate: update bins, vehicles, drivers, logs
6. Generate reports
```

---

## Test Cases Covered

| Scenario | Handled |
|---|---|
| No critical bins | "No critical bins" message |
| Vehicle at capacity | Skipped, "overload" in status |
| Insufficient fuel | Skipped, "insufficient fuel" status |
| Emergency overflow | Nearest vehicle dispatched |
| Driver overtime | Hours logged, capped at max |
| Maintenance blocking | Vehicle excluded from assignment |
| All bins collected | Advance Day resets state |
