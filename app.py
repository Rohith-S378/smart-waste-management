"""
app.py — Flask Web Dashboard for Smart Waste Management System
"""
import json
import os
from flask import Flask, render_template, request, jsonify, session

from models import Bin, Zone, Vehicle, Driver, SimulationState, CollectionLog
from simulation.simulator import WasteSimulator
from simulation.events import generate_sample_bins
from utils.helpers import load_json, save_json, new_id
from config.settings import BINS_FILE, VEHICLES_FILE, DRIVERS_FILE, ZONES_FILE, LOGS_FILE

app = Flask(__name__)
app.secret_key = "waste-mgmt-secret-2024"

# ── Global simulator instance ──────────────────────────────────────────────
_simulator: WasteSimulator = None


def get_simulator() -> WasteSimulator:
    global _simulator
    if _simulator is None:
        _simulator = _bootstrap_simulator()
    return _simulator


def _bootstrap_simulator() -> WasteSimulator:
    """Load persisted state or seed with sample data."""
    state = SimulationState()

    raw = load_json("data/sample_data.json", {})

    # Load zones
    for zd in raw.get("zones", []):
        state.zones[zd["zone_name"]] = Zone.from_dict(zd)

    # Load vehicles
    for vd in raw.get("vehicles", []):
        state.vehicles[vd["vehicle_id"]] = Vehicle.from_dict(vd)

    # Load drivers
    for dd in raw.get("drivers", []):
        state.drivers[dd["driver_id"]] = Driver.from_dict(dd)

    sim = WasteSimulator(state)

    # Seed bins if none exist
    if not state.bins:
        zone_names = list(state.zones.keys())
        bins = generate_sample_bins(zone_names, bins_per_zone=4)
        for b in bins:
            sim.add_bin(b)

    return sim


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Snapshot ─────────────────────────────────────────────────────────────

@app.route("/api/snapshot")
def api_snapshot():
    sim = get_simulator()
    snap = sim.to_snapshot()
    # Summarise for lightweight transfer
    bins_list = []
    for b in sim.state.bins.values():
        bins_list.append({
            "bin_id": b.bin_id,
            "zone": b.zone_name,
            "waste_type": b.waste_type,
            "fill_level": b.fill_level,
            "capacity_kg": b.capacity_kg,
            "collected_today": b.collected_today,
            "overflow": b.overflow,
            "priority": b.priority,
            "load_kg": b.load_kg,
            "is_critical": b.is_critical(),
            "x": snap["coords"].get(b.zone_name, [50, 50])[0],
            "y": snap["coords"].get(b.zone_name, [50, 50])[1],
        })

    vehicles_list = []
    for v in sim.state.vehicles.values():
        vehicles_list.append({
            "vehicle_id": v.vehicle_id,
            "vehicle_type": v.vehicle_type,
            "zone": v.assigned_zone,
            "available": v.available,
            "current_load_kg": v.current_load_kg,
            "max_capacity_kg": v.max_capacity_kg,
            "current_fuel": round(v.current_fuel, 1),
            "fuel_tank": v.fuel_tank_capacity,
            "needs_maintenance": v.needs_maintenance,
            "odometer_km": round(v.odometer_km, 1),
            "driver_id": v.driver_id,
            "x": snap["coords"].get(v.assigned_zone, [50, 50])[0],
            "y": snap["coords"].get(v.assigned_zone, [50, 50])[1],
        })

    zones_list = []
    for z in sim.state.zones.values():
        bins_in = [sim.state.bins[bid] for bid in z.bin_ids if bid in sim.state.bins]
        zones_list.append({
            "zone_name": z.zone_name,
            "bin_count": len(bins_in),
            "critical_count": sum(1 for b in bins_in if b.is_critical()),
            "avg_fill": round(sum(b.fill_level for b in bins_in) / max(len(bins_in), 1), 1),
            "x": snap["coords"].get(z.zone_name, [50, 50])[0],
            "y": snap["coords"].get(z.zone_name, [50, 50])[1],
        })

    return jsonify({
        "day": snap["day"],
        "bins": bins_list,
        "vehicles": vehicles_list,
        "zones": zones_list,
        "schedule": snap["schedule"],
        "logs": [l.to_dict() for l in sim.state.logs[-20:]],
    })


# ── API: Schedule ─────────────────────────────────────────────────────────────

@app.route("/api/schedule", methods=["POST"])
def api_schedule():
    sim = get_simulator()
    data = request.get_json(silent=True) or {}
    threshold = float(data.get("threshold", 70))
    schedule = sim.generate_schedule(threshold)
    routes = sim.get_route_plans()
    return jsonify({"schedule": schedule, "routes": routes})


# ── API: Simulate collection ──────────────────────────────────────────────────

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    sim = get_simulator()
    if not sim.state.schedule:
        sim.generate_schedule()
    results = sim.simulate_collection()
    cost = sim.cost_report()
    recycle = sim.recycling_report()
    zones = sim.zone_report()
    return jsonify({
        "collected": results,
        "cost_report": cost,
        "recycling_report": recycle,
        "zone_report": zones,
    })


# ── API: Emergency ────────────────────────────────────────────────────────────

@app.route("/api/emergency", methods=["POST"])
def api_emergency():
    sim = get_simulator()
    data = request.get_json(silent=True) or {}
    bin_id = data.get("bin_id")
    if not bin_id:
        # pick a random non-collected bin
        import random
        candidates = [b for b in sim.state.bins.values() if not b.collected_today]
        if not candidates:
            return jsonify({"error": "No bins available for emergency"}), 400
        bin_id = random.choice(candidates).bin_id
    result = sim.trigger_emergency(bin_id)
    return jsonify(result)


# ── API: Advance Day ──────────────────────────────────────────────────────────

@app.route("/api/advance-day", methods=["POST"])
def api_advance_day():
    sim = get_simulator()
    sim.advance_day()
    return jsonify({"day": sim.state.day, "message": f"Advanced to Day {sim.state.day}"})


# ── API: Reports ──────────────────────────────────────────────────────────────

@app.route("/api/report/cost")
def api_cost_report():
    sim = get_simulator()
    return jsonify(sim.cost_report())


@app.route("/api/report/recycling")
def api_recycling():
    sim = get_simulator()
    return jsonify(sim.recycling_report())


@app.route("/api/report/zones")
def api_zones():
    sim = get_simulator()
    return jsonify(sim.zone_report())


# ── API: Add Bin ──────────────────────────────────────────────────────────────

@app.route("/api/bin/add", methods=["POST"])
def api_add_bin():
    sim = get_simulator()
    d = request.get_json(silent=True) or {}
    try:
        from datetime import date
        b = Bin(
            bin_id=new_id("BIN-"),
            zone_name=d["zone_name"],
            waste_type=d.get("waste_type", "Mixed"),
            fill_level=float(d.get("fill_level", 50)),
            capacity_kg=float(d.get("capacity_kg", 300)),
            last_collection=date.today().isoformat(),
            priority=int(d.get("priority", 4)),
        )
        sim.add_bin(b)
        return jsonify({"message": "Bin added", "bin": b.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── API: Refuel Vehicle ────────────────────────────────────────────────────────

@app.route("/api/vehicle/refuel", methods=["POST"])
def api_refuel():
    sim = get_simulator()
    d = request.get_json(silent=True) or {}
    vid = d.get("vehicle_id")
    v = sim.state.vehicles.get(vid)
    if not v:
        return jsonify({"error": "Vehicle not found"}), 404
    v.refuel()
    return jsonify({"message": f"{vid} refuelled to {v.fuel_tank_capacity}L"})


# ── API: Maintenance clear ────────────────────────────────────────────────────

@app.route("/api/vehicle/maintain", methods=["POST"])
def api_maintain():
    sim = get_simulator()
    d = request.get_json(silent=True) or {}
    vid = d.get("vehicle_id")
    v = sim.state.vehicles.get(vid)
    if not v:
        return jsonify({"error": "Vehicle not found"}), 404
    v.needs_maintenance = False
    v.odometer_km = 0.0
    return jsonify({"message": f"{vid} maintenance cleared"})


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
