"""
simulation/events.py — Random event generators for realistic simulation
"""
import random
from models.bin import Bin
from utils.helpers import new_id
from datetime import date


def random_overflow_event(bins: list) -> list:
    """Randomly trigger overflow on 1-3 bins."""
    candidates = [b for b in bins if not b.overflow and not b.collected_today]
    chosen = random.sample(candidates, min(random.randint(1, 3), len(candidates)))
    for b in chosen:
        b.overflow = True
        b.fill_level = 100.0
        b.priority = 1
    return chosen


def random_bin_fill_increment(bins: list, min_inc=3.0, max_inc=20.0):
    """Simulate organic fill increase during the day."""
    for b in bins:
        if not b.collected_today:
            inc = random.uniform(min_inc, max_inc)
            b.fill_level = min(100.0, b.fill_level + inc)


def generate_sample_bins(zone_names: list, bins_per_zone: int = 4) -> list:
    """Generate a deterministic set of sample bins for demo mode."""
    waste_types = ["Dry", "Wet", "Mixed", "Hazardous"]
    bins = []
    rng = random.Random(99)
    for zone in zone_names:
        for i in range(bins_per_zone):
            wt = waste_types[i % len(waste_types)]
            fill = rng.uniform(20, 100)
            cap = rng.choice([200, 300, 500])
            bid = new_id("BIN-")
            bins.append(Bin(
                bin_id=bid,
                zone_name=zone,
                waste_type=wt,
                fill_level=round(fill, 1),
                capacity_kg=cap,
                last_collection=date.today().isoformat(),
                priority=4,
                current_load_kg=round(cap * fill / 100, 2),
            ))
    return bins
