"""
logic/routing.py — Per-vehicle route optimisation
"""
from typing import Dict, List, Tuple
from utils.distance import optimized_route


def optimize_routes(
    schedule: List[dict],
    distance_matrix: Dict[str, Dict[str, float]],
    vehicles_by_id: dict,
) -> List[dict]:
    """
    Group scheduled tasks by vehicle, compute optimised route for each,
    and annotate tasks with route_order and total_route_km.
    Returns a list of route dicts ready for display / fuel calc.
    """
    vehicle_tasks: Dict[str, List[dict]] = {}
    for task in schedule:
        vid = task.get("vehicle_id")
        if vid:
            vehicle_tasks.setdefault(vid, []).append(task)

    route_plans = []
    for vid, tasks in vehicle_tasks.items():
        v = vehicles_by_id.get(vid)
        if not v:
            continue
        bin_zones = [t["zone"] for t in tasks]
        path, total_km = optimized_route(v.assigned_zone, bin_zones, distance_matrix)

        route_plans.append({
            "vehicle_id": vid,
            "driver_id": v.driver_id,
            "start_zone": v.assigned_zone,
            "path": path,
            "total_km": total_km,
            "bin_ids": [t["bin_id"] for t in tasks],
            "total_kg": round(sum(t["kg"] for t in tasks), 2),
            "fuel_needed": round(total_km * v.fuel_consumption_rate, 2),
            "fuel_cost": round(total_km * v.fuel_consumption_rate * 95.0, 2),
        })

    return route_plans
