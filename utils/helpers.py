"""
utils/helpers.py — File persistence, validation, reporting helpers
"""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List


# ── File I/O ──────────────────────────────────────────────────────────────────

def load_json(path: str, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── ID Generation ─────────────────────────────────────────────────────────────

def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


# ── Validation ────────────────────────────────────────────────────────────────

def validate_fill_level(v) -> float:
    v = float(v)
    if not 0 <= v <= 100:
        raise ValueError("Fill level must be between 0 and 100")
    return v


def validate_positive(v, name="value") -> float:
    v = float(v)
    if v <= 0:
        raise ValueError(f"{name} must be positive")
    return v


# ── Timestamp ─────────────────────────────────────────────────────────────────

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Report helpers ────────────────────────────────────────────────────────────

def cost_summary(logs: List[dict], drivers: List[dict], fuel_price: float) -> dict:
    total_fuel_litres = sum(l.get("fuel_used", 0) for l in logs)
    fuel_cost = round(total_fuel_litres * fuel_price, 2)
    staff_cost = sum(
        min(d.get("hours_worked", 0), d.get("max_working_hours", 8)) * d.get("salary_per_hour", 150)
        + d.get("overtime_hours", 0) * d.get("salary_per_hour", 150) * 1.5
        for d in drivers
    )
    total_kg = sum(l.get("kg_collected", 0) for l in logs)
    return {
        "fuel_litres": round(total_fuel_litres, 2),
        "fuel_cost": fuel_cost,
        "staff_cost": round(staff_cost, 2),
        "total_cost": round(fuel_cost + staff_cost, 2),
        "collections": len(logs),
        "kg_collected": round(total_kg, 2),
    }


def recycling_report(logs: List[dict]) -> dict:
    totals = {"Dry": 0.0, "Wet": 0.0, "Mixed": 0.0, "Hazardous": 0.0}
    for log in logs:
        wt = log.get("waste_type", "Mixed")
        totals[wt] = totals.get(wt, 0) + log.get("kg_collected", 0)
    total = sum(totals.values()) or 1
    recyclable = totals["Dry"] + totals["Wet"] * 0.3
    landfill = totals["Mixed"] + totals["Hazardous"] + totals["Wet"] * 0.7
    return {
        "by_type": totals,
        "recyclable_kg": round(recyclable, 2),
        "landfill_kg": round(landfill, 2),
        "recycling_pct": round(recyclable / total * 100, 1),
        "total_kg": round(total, 2),
    }
