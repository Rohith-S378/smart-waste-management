"""
models/environment.py — Global simulation state
"""
from dataclasses import dataclass, field
from typing import Dict, List
from models.bin import Bin, Zone
from models.truck import Vehicle, Driver


@dataclass
class CollectionLog:
    log_id: str
    bin_id: str
    vehicle_id: str
    driver_id: str
    zone: str
    waste_type: str
    kg_collected: float
    timestamp: str
    fuel_used: float
    distance_km: float
    emergency: bool = False

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "CollectionLog":
        return cls(**d)


@dataclass
class SimulationState:
    bins: Dict[str, Bin] = field(default_factory=dict)
    zones: Dict[str, Zone] = field(default_factory=dict)
    vehicles: Dict[str, Vehicle] = field(default_factory=dict)
    drivers: Dict[str, Driver] = field(default_factory=dict)
    logs: List[CollectionLog] = field(default_factory=list)
    schedule: List[dict] = field(default_factory=list)   # planned tasks
    day: int = 1
    total_fuel_cost: float = 0.0
    total_staff_cost: float = 0.0
    recycling_stats: dict = field(default_factory=lambda: {
        "dry": 0.0, "wet": 0.0, "mixed": 0.0, "hazardous": 0.0
    })
