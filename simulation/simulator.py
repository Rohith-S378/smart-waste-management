"""
simulation/simulator.py — Core simulation engine
"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from models import Bin, Zone, Vehicle, Driver, SimulationState, CollectionLog
from logic import identify_critical_bins, build_schedule, optimize_routes
from utils.helpers import now_str, cost_summary, recycling_report
from utils.distance import (
    generate_zone_coords, build_distance_matrix, optimized_route
)
from config.settings import FILL_THRESHOLD, FUEL_PRICE


class WasteSimulator:
    """
    Central controller.  All Flask routes talk through this object.
    """

    def __init__(self, state: SimulationState):
        self.state = state
        self._rebuild_distance_matrix()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _rebuild_distance_matrix(self):
        zone_names = list(self.state.zones.keys()) or ["Depot"]
        self.coords = generate_zone_coords(zone_names)
        self.distance_matrix = build_distance_matrix(zone_names, self.coords)

    def add_zone(self, zone: Zone):
        self.state.zones[zone.zone_name] = zone
        self._rebuild_distance_matrix()

    def add_bin(self, bin_obj: Bin):
        self.state.bins[bin_obj.bin_id] = bin_obj
        z = self.state.zones.get(bin_obj.zone_name)
        if z and bin_obj.bin_id not in z.bin_ids:
            z.bin_ids.append(bin_obj.bin_id)

    def add_vehicle(self, v: Vehicle):
        self.state.vehicles[v.vehicle_id] = v

    def add_driver(self, d: Driver):
        self.state.drivers[d.driver_id] = d

    # ── Daily Operations ──────────────────────────────────────────────────────

    def identify_critical(self, threshold: float = FILL_THRESHOLD) -> List[Bin]:
        return identify_critical_bins(list(self.state.bins.values()), threshold)

    def generate_schedule(self, threshold: float = FILL_THRESHOLD) -> List[dict]:
        critical = self.identify_critical(threshold)
        vehicles = list(self.state.vehicles.values())
        schedule = build_schedule(
            critical, vehicles, self.state.drivers, self.distance_matrix
        )
        self.state.schedule = schedule
        return schedule

    def get_route_plans(self) -> List[dict]:
        return optimize_routes(
            self.state.schedule,
            self.distance_matrix,
            self.state.vehicles,
        )

    def simulate_collection(self) -> List[dict]:
        """Execute all Scheduled tasks, update bin/vehicle/driver state."""
        results = []
        for task in self.state.schedule:
            if task.get("status") != "Scheduled":
                continue
            bin_obj  = self.state.bins.get(task["bin_id"])
            vehicle  = self.state.vehicles.get(task["vehicle_id"])
            driver   = self.state.drivers.get(task["driver_id"])

            if not (bin_obj and vehicle and driver):
                task["status"] = "Failed — missing entity"
                continue
            if bin_obj.collected_today:
                task["status"] = "Skipped — already collected"
                continue

            kg = bin_obj.load_kg
            dist = task["distance_km"]

            # capacity guard
            if not vehicle.can_carry(kg):
                task["status"] = "Failed — vehicle overload"
                continue

            # fuel guard
            fuel_needed = vehicle.fuel_for_distance(dist)
            if vehicle.current_fuel < fuel_needed:
                task["status"] = "Failed — insufficient fuel"
                continue

            # driver hours guard
            hours_needed = (dist / 30)   # assume avg 30 km/h
            if driver.hours_worked >= driver.max_working_hours:
                task["status"] = "Failed — driver hours exceeded"
                continue

            # ── Execute ────────────────────────────────────────────────────
            vehicle.current_load_kg += kg
            vehicle.consume_fuel(dist)
            driver.log_hours(hours_needed)
            bin_obj.reset_after_collection()
            task["status"] = "Completed"

            log_entry = CollectionLog(
                log_id=uuid.uuid4().hex[:8].upper(),
                bin_id=bin_obj.bin_id,
                vehicle_id=vehicle.vehicle_id,
                driver_id=driver.driver_id,
                zone=bin_obj.zone_name,
                waste_type=bin_obj.waste_type,
                kg_collected=kg,
                timestamp=now_str(),
                fuel_used=round(fuel_needed, 3),
                distance_km=dist,
                emergency=task.get("emergency", False),
            )
            self.state.logs.append(log_entry)
            results.append(log_entry.to_dict())

        return results

    # ── Emergency Handler ─────────────────────────────────────────────────────

    def trigger_emergency(self, bin_id: str) -> dict:
        bin_obj = self.state.bins.get(bin_id)
        if not bin_obj:
            return {"error": "Bin not found"}

        bin_obj.overflow = True
        bin_obj.fill_level = 100.0
        bin_obj.priority = 1

        # find nearest available vehicle
        vehicles = [
            v for v in self.state.vehicles.values()
            if v.available and not v.needs_maintenance
        ]
        if not vehicles:
            return {"error": "No vehicles available for emergency"}

        def dist_to_bin(v):
            return self.distance_matrix.get(v.assigned_zone, {}).get(bin_obj.zone_name, 999)

        nearest = min(vehicles, key=dist_to_bin)
        dist = dist_to_bin(nearest)

        # insert at front of schedule
        emergency_task = {
            "bin_id": bin_id,
            "vehicle_id": nearest.vehicle_id,
            "driver_id": nearest.driver_id,
            "zone": bin_obj.zone_name,
            "waste_type": bin_obj.waste_type,
            "kg": bin_obj.load_kg,
            "distance_km": round(dist, 2),
            "emergency": True,
            "status": "Scheduled",
        }
        self.state.schedule.insert(0, emergency_task)
        return {
            "message": f"Emergency scheduled. Vehicle {nearest.vehicle_id} dispatched.",
            "task": emergency_task,
        }

    # ── Fuel Randomised Day Advance ───────────────────────────────────────────

    def advance_day(self):
        """Reset daily flags, randomly increase bin fill levels."""
        import random
        self.state.day += 1
        self.state.schedule = []
        self.state.logs = []

        for bin_obj in self.state.bins.values():
            bin_obj.collected_today = False
            bin_obj.overflow = False
            inc = random.uniform(5, 35)
            bin_obj.fill_level = min(100.0, bin_obj.fill_level + inc)

        for v in self.state.vehicles.values():
            v.current_load_kg = 0.0
            v.route_assigned = False
            if v.current_fuel < v.fuel_tank_capacity * 0.2:
                v.refuel()

        for d in self.state.drivers.values():
            d.hours_worked = 0.0
            d.overtime_hours = 0.0

        for z in self.state.zones.values():
            z.serviced_today = False

    # ── Reports ───────────────────────────────────────────────────────────────

    def cost_report(self) -> dict:
        logs = [l.to_dict() for l in self.state.logs]
        drivers = [d.to_dict() for d in self.state.drivers.values()]
        return cost_summary(logs, drivers, FUEL_PRICE)

    def recycling_report(self) -> dict:
        logs = [l.to_dict() for l in self.state.logs]
        return recycling_report(logs)

    def zone_report(self) -> List[dict]:
        report = []
        for zone_name, zone in self.state.zones.items():
            bins_in_zone = [
                self.state.bins[bid]
                for bid in zone.bin_ids
                if bid in self.state.bins
            ]
            collected = [b for b in bins_in_zone if b.collected_today]
            critical  = [b for b in bins_in_zone if b.is_critical()]
            report.append({
                "zone": zone_name,
                "total_bins": len(bins_in_zone),
                "collected_today": len(collected),
                "critical_bins": len(critical),
                "avg_fill": round(
                    sum(b.fill_level for b in bins_in_zone) / max(len(bins_in_zone), 1), 1
                ),
            })
        return report

    # ── Serialization helpers ─────────────────────────────────────────────────

    def to_snapshot(self) -> dict:
        return {
            "day": self.state.day,
            "bins": {k: v.to_dict() for k, v in self.state.bins.items()},
            "zones": {k: v.to_dict() for k, v in self.state.zones.items()},
            "vehicles": {k: v.to_dict() for k, v in self.state.vehicles.items()},
            "drivers": {k: v.to_dict() for k, v in self.state.drivers.items()},
            "logs": [l.to_dict() for l in self.state.logs],
            "schedule": self.state.schedule,
            "coords": self.coords,
        }
