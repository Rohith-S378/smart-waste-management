"""
logic/priority.py — Bin criticality identification and priority sorting
"""
from typing import List
from models.bin import Bin
from config.settings import FILL_THRESHOLD, PRIORITY


def identify_critical_bins(bins: List[Bin], threshold: float = FILL_THRESHOLD) -> List[Bin]:
    """Return bins at or above fill threshold, sorted by priority."""
    critical = [b for b in bins if b.fill_level >= threshold and not b.collected_today]
    return sort_by_priority(critical)


def sort_by_priority(bins: List[Bin]) -> List[Bin]:
    """
    Sort bins: Hazardous first, then overflow, then by fill level descending.
    """
    def key(b: Bin):
        type_prio = PRIORITY.get(b.waste_type, 4)
        overflow_bonus = 0 if b.overflow else 1
        return (overflow_bonus, type_prio, -b.fill_level)

    return sorted(bins, key=key)


def assign_priority_level(bin: Bin) -> int:
    """Recompute and return a numeric priority for a single bin."""
    if bin.overflow or bin.fill_level >= 95:
        return 1
    if bin.waste_type == "Hazardous":
        return 1
    if bin.fill_level >= 80:
        return 2
    if bin.fill_level >= FILL_THRESHOLD:
        return 3
    return 4
