"""
utils/distance.py — Distance matrix and shortest-path helpers
Uses a simple (n×n) adjacency matrix; Dijkstra for shortest path.
"""
import math
import random
from typing import Dict, List, Tuple


# ── Zone coordinate map (lat-like grid positions) ──────────────────────────
# Seeded so the map is stable across reloads
_RNG = random.Random(42)

def generate_zone_coords(zone_names: List[str]) -> Dict[str, Tuple[float, float]]:
    """Assign fixed (x,y) positions to zones on a 100×100 grid."""
    coords: Dict[str, Tuple[float, float]] = {}
    for name in zone_names:
        coords[name] = (_RNG.uniform(5, 95), _RNG.uniform(5, 95))
    return coords


def euclidean_distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return round(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2) * 0.5, 2)   # scale → km


def build_distance_matrix(
    zone_names: List[str],
    coords: Dict[str, Tuple[float, float]]
) -> Dict[str, Dict[str, float]]:
    matrix: Dict[str, Dict[str, float]] = {}
    for z1 in zone_names:
        matrix[z1] = {}
        for z2 in zone_names:
            if z1 == z2:
                matrix[z1][z2] = 0.0
            else:
                matrix[z1][z2] = euclidean_distance(coords[z1], coords[z2])
    return matrix


def dijkstra(
    matrix: Dict[str, Dict[str, float]],
    start: str,
    targets: List[str]
) -> Tuple[List[str], float]:
    """
    Nearest-neighbour greedy path through `targets` starting from `start`.
    Returns (ordered_path, total_distance).
    """
    remaining = set(targets)
    path = [start]
    total_dist = 0.0
    current = start

    while remaining:
        # pick the nearest unvisited target
        nearest = min(remaining, key=lambda z: matrix[current].get(z, 1e9))
        total_dist += matrix[current].get(nearest, 0)
        path.append(nearest)
        current = nearest
        remaining.remove(nearest)

    return path, round(total_dist, 2)


def optimized_route(
    vehicle_zone: str,
    bin_zones: List[str],
    matrix: Dict[str, Dict[str, float]]
) -> Tuple[List[str], float]:
    """
    Returns the optimized collection order and total km.
    Depot → bins → depot (return leg added).
    """
    if not bin_zones:
        return [vehicle_zone], 0.0

    path, dist = dijkstra(matrix, vehicle_zone, list(set(bin_zones)))
    # add return leg
    if path:
        dist += matrix[path[-1]].get(vehicle_zone, 0)
        path.append(vehicle_zone)
    return path, dist
