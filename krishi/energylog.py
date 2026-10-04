"""Farmer's own pump log: hours or diesel used per watering, totals in kWh, litres and CO2.

This is the measured side of the simulation: after a season the farmer's real numbers can replace the model's
assumptions. Stored per account in energy_log.json (text only).
"""

import json
import os
import uuid
from datetime import date

from krishi import water

ROOT = os.path.dirname(os.path.dirname(__file__))
FILE = os.path.join(ROOT, "energy_log.json")


def _load():
    if os.path.exists(FILE):
        try:
            with open(FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def entries(user_id):
    return sorted(_load().get(user_id, []), key=lambda e: e["date"])


def add(user_id, day, crop_id, source, hours, pump_kw=None, litres=None, acres=None, note=""):
    """source 'grid': kWh = pump kW x hours. source 'diesel': litres entered directly."""
    kwh = (pump_kw or 0.0) * hours if source == "grid" else 0.0
    litres = (litres or 0.0) if source == "diesel" else 0.0
    entry = {"id": str(uuid.uuid4()), "date": day.isoformat() if isinstance(day, date) else day, "crop_id": crop_id,
             "source": source, "hours": float(hours), "kwh": float(kwh), "litres": float(litres),
             "acres": acres, "note": note,
             "co2_kg": kwh * water.GRID_KG_CO2_PER_KWH + litres * water.DIESEL_KG_CO2_PER_LITRE}
    data = _load()
    data.setdefault(user_id, []).append(entry)
    _save(data)
    return entry


def delete(user_id, entry_id):
    data = _load()
    data[user_id] = [e for e in data.get(user_id, []) if e["id"] != entry_id]
    _save(data)


def totals(rows):
    out = {"hours": 0.0, "kwh": 0.0, "litres": 0.0, "co2_kg": 0.0, "n": len(rows), "by_month": {}}
    for e in rows:
        out["hours"] += e["hours"]
        out["kwh"] += e["kwh"]
        out["litres"] += e["litres"]
        out["co2_kg"] += e["co2_kg"]
        m = e["date"][:7]
        b = out["by_month"].setdefault(m, {"kwh": 0.0, "litres": 0.0, "co2_kg": 0.0, "hours": 0.0})
        for k in ("kwh", "litres", "co2_kg", "hours"):
            b[k] += e[k]
    return out
