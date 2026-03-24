"""
logic/assignment.py — Assign vehicles to bins respecting all constraints
"""
from typing import List, Dict, Optional, Tuple
from models.bin import Bin
from models.truck import Vehicle, Driver
from config.settings import MAX_DAILY_DISTANCE
import logging

log = logging.getLogger(__name__)


def assign_vehicle(
    bin_obj: Bin,
    vehicles: List[Vehicle],
    drivers: Dict[str, Driver],
    distance_to_bin: float,
) -> Optional[Vehicle]:
    """
    Pick the best available vehicle for a single bin, enforcing:
    • Capacity check
    • Fuel sufficiency
    • Hazardous waste → HazMat vehicle only
    • No double-assignment
    • Maintenance block
    • Zone preference (same zone first)
    """
    candidates = [
        v for v in vehicles
        if v.available
        and not v.route_assigned
        and not v.needs_maintenance
        and v.can_carry(bin_obj.load_kg)
        and v.has_fuel(distance_to_bin * 2)   # round-trip estimate
        and _driver_available(v.driver_id, drivers)
        and _waste_type_ok(bin_obj.waste_type, v.vehicle_type)
    ]

    if not candidates:
        return None

    # Prefer same-zone vehicles; break ties by free capacity (most free first)
    candidates.sort(
        key=lambda v: (
            0 if v.assigned_zone == bin_obj.zone_name else 1,
            v.current_load_kg / v.max_capacity_kg   # fuller → deprioritised
        )
    )
    return candidates[0]


def _driver_available(driver_id: str, drivers: Dict[str, Driver]) -> bool:
    d = drivers.get(driver_id)
    if d is None:
        return False
    return d.active and d.hours_worked < d.max_working_hours


def _waste_type_ok(waste_type: str, vehicle_type: str) -> bool:
    if waste_type == "Hazardous":
        return vehicle_type == "HazMat"
    # Non-HazMat vehicles can handle non-hazardous waste
    return True


def build_schedule(
    critical_bins: List[Bin],
    vehicles: List[Vehicle],
    drivers: Dict[str, Driver],
    distance_matrix: Dict[str, Dict[str, float]],
) -> List[dict]:
    """
    Greedy schedule builder.
    Returns list of task dicts: {bin_id, vehicle_id, driver_id, distance_km, kg}
    """
    schedule = []
    assigned_vehicles: Dict[str, float] = {}   # vehicle_id → cumulative km

    for bin_obj in critical_bins:
        if bin_obj.collected_today:
            continue

        # estimate distance from vehicle's home zone to bin zone
        best_vehicle = None
        best_dist = float("inf")

        for v in vehicles:
            if v.route_assigned or not v.available or v.needs_maintenance:
                continue
            dist = distance_matrix.get(v.assigned_zone, {}).get(bin_obj.zone_name, 10.0)
            cum = assigned_vehicles.get(v.vehicle_id, 0)
            if cum + dist * 2 > MAX_DAILY_DISTANCE:
                continue
            if dist < best_dist:
                cand = assign_vehicle(bin_obj, [v], drivers, dist)
                if cand:
                    best_vehicle = cand
                    best_dist = dist

        if best_vehicle:
            task = {
                "bin_id": bin_obj.bin_id,
                "vehicle_id": best_vehicle.vehicle_id,
                "driver_id": best_vehicle.driver_id,
                "zone": bin_obj.zone_name,
                "waste_type": bin_obj.waste_type,
                "kg": bin_obj.load_kg,
                "distance_km": round(best_dist, 2),
                "emergency": bin_obj.overflow,
                "status": "Scheduled",
            }
            schedule.append(task)
            assigned_vehicles[best_vehicle.vehicle_id] = (
                assigned_vehicles.get(best_vehicle.vehicle_id, 0) + best_dist * 2
            )
            # Temporarily mark to prevent double assignment in same pass
            best_vehicle.route_assigned = True

        else:
            schedule.append({
                "bin_id": bin_obj.bin_id,
                "vehicle_id": None,
                "driver_id": None,
                "zone": bin_obj.zone_name,
                "waste_type": bin_obj.waste_type,
                "kg": bin_obj.load_kg,
                "distance_km": 0,
                "emergency": bin_obj.overflow,
                "status": "Unassigned — no eligible vehicle",
            })

    # reset temporary route_assigned flags
    for v in vehicles:
        v.route_assigned = False

    return schedule
