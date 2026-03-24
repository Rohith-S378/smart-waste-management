"""
models/truck.py — Vehicle and Driver data structures
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class Vehicle:
    vehicle_id: str
    vehicle_type: str           # Standard / Compactor / HazMat / Mini
    max_capacity_kg: float
    fuel_tank_capacity: float   # litres
    fuel_consumption_rate: float  # litres/km
    assigned_zone: str
    driver_id: str
    available: bool = True
    current_load_kg: float = 0.0
    current_fuel: float = 0.0   # litres remaining
    odometer_km: float = 0.0    # total km — maintenance trigger
    needs_maintenance: bool = False
    route_assigned: bool = False  # prevents double assignment

    # ── helpers ───────────────────────────────────────────────────────────────
    def can_carry(self, kg: float) -> bool:
        return (self.current_load_kg + kg) <= self.max_capacity_kg

    def fuel_for_distance(self, km: float) -> float:
        return km * self.fuel_consumption_rate

    def has_fuel(self, km: float) -> bool:
        return self.current_fuel >= self.fuel_for_distance(km)

    def consume_fuel(self, km: float):
        used = self.fuel_for_distance(km)
        self.current_fuel = max(0.0, self.current_fuel - used)
        self.odometer_km += km
        if self.odometer_km >= 500:
            self.needs_maintenance = True

    def refuel(self):
        self.current_fuel = self.fuel_tank_capacity

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Vehicle":
        d.setdefault("current_load_kg", 0.0)
        d.setdefault("current_fuel", d.get("fuel_tank_capacity", 60))
        d.setdefault("odometer_km", 0.0)
        d.setdefault("needs_maintenance", False)
        d.setdefault("route_assigned", False)
        return cls(**d)


@dataclass
class Driver:
    driver_id: str
    name: str
    assigned_vehicle: str
    max_working_hours: float
    shift_start: str            # "HH:MM"
    shift_end: str
    salary_per_hour: float
    hours_worked: float = 0.0
    overtime_hours: float = 0.0
    active: bool = True

    @property
    def total_salary(self) -> float:
        normal = min(self.hours_worked, self.max_working_hours) * self.salary_per_hour
        ot = self.overtime_hours * self.salary_per_hour * 1.5
        return round(normal + ot, 2)

    def log_hours(self, hours: float):
        if self.hours_worked + hours > self.max_working_hours:
            excess = (self.hours_worked + hours) - self.max_working_hours
            self.overtime_hours += excess
            self.hours_worked = self.max_working_hours
        else:
            self.hours_worked += hours

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Driver":
        d.setdefault("hours_worked", 0.0)
        d.setdefault("overtime_hours", 0.0)
        d.setdefault("active", True)
        return cls(**d)
