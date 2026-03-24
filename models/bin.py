"""
models/bin.py — Bin and Zone data structures
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import date
import uuid


@dataclass
class Bin:
    bin_id: str
    zone_name: str
    waste_type: str          # Dry / Wet / Mixed / Hazardous
    fill_level: float        # 0-100 %
    capacity_kg: float       # maximum kg capacity
    last_collection: str     # ISO date string
    priority: int            # 1=highest … 4=lowest
    current_load_kg: float = 0.0
    collected_today: bool = False
    overflow: bool = False
    fill_history: List[float] = field(default_factory=list)

    # ── computed ──────────────────────────────────────────────────────────────
    @property
    def load_kg(self) -> float:
        return round(self.capacity_kg * self.fill_level / 100, 2)

    def is_critical(self, threshold: float = 70) -> bool:
        return self.fill_level >= threshold

    def reset_after_collection(self):
        self.fill_history.append(self.fill_level)
        self.fill_level = 0.0
        self.current_load_kg = 0.0
        self.collected_today = True
        self.overflow = False
        self.last_collection = date.today().isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Bin":
        d.setdefault("fill_history", [])
        d.setdefault("collected_today", False)
        d.setdefault("overflow", False)
        d.setdefault("current_load_kg", 0.0)
        return cls(**d)


@dataclass
class Zone:
    zone_id: str
    zone_name: str
    bin_ids: List[str] = field(default_factory=list)
    serviced_today: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Zone":
        return cls(**d)
