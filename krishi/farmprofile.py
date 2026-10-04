"""The farmer's irrigation system (method, source, pump) and the waterings they actually did.

Stored per account as text/numbers in farm_profiles.json and irrigation_events.json.
Application efficiencies are typical textbook values (surface / flood about 60%, sprinkler about 75%, drip about 90%):
ASSUMPTIONS to be replaced by measured values in the pilot.
"""

import json
import os
import uuid
from datetime import date

ROOT = os.path.dirname(os.path.dirname(__file__))
PROFILES_FILE = os.path.join(ROOT, "farm_profiles.json")
EVENTS_FILE = os.path.join(ROOT, "irrigation_events.json")

METHOD_EFFICIENCY = {"flood": 0.60, "sprinkler": 0.75, "drip": 0.90}
SOURCES = ["borewell", "open_well", "canal", "river_pond", "rain_only"]
POWER = ["grid", "diesel", "solar"]
DEFAULT_PROFILE = {"method": "flood", "source": "borewell", "pump_hp": 5.0, "power": "grid", "hours_per_day": 8.0, "lift_m": 40.0}


def _load(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def get_profile(farmer_id):
    saved = _load(PROFILES_FILE).get(farmer_id)
    return {**DEFAULT_PROFILE, **(saved or {})}, bool(saved)


def save_profile(farmer_id, profile):
    data = _load(PROFILES_FILE)
    data[farmer_id] = profile
    _save(PROFILES_FILE, data)


def efficiency(profile):
    return METHOD_EFFICIENCY.get(profile.get("method", "flood"), 0.60)


def pump_flow_m3h(pump_hp, lift_m, wire_to_water_eff=0.35):
    """Water delivered per hour: hydraulic power / (rho g H). 5 HP at 40 m and 35% efficiency is about 12 m3/h."""
    if not pump_hp or not lift_m:
        return 0.0
    hydraulic_w = pump_hp * 746.0 * wire_to_water_eff
    return hydraulic_w / (9810.0 * lift_m) * 3600.0


# ---- waterings the farmer actually did (per saved plan row) ----
def events_for(row_id):
    """{date: net_mm} the farmer reported for this crop."""
    out = {}
    for e in _load(EVENTS_FILE).get(row_id, []):
        out[date.fromisoformat(e["date"])] = out.get(date.fromisoformat(e["date"]), 0.0) + e["net_mm"]
    return out


def add_event(row_id, day, net_mm):
    data = _load(EVENTS_FILE)
    data.setdefault(row_id, []).append({"id": str(uuid.uuid4()), "date": day.isoformat(), "net_mm": float(net_mm)})
    _save(EVENTS_FILE, data)


def clear_events(row_id):
    data = _load(EVENTS_FILE)
    data.pop(row_id, None)
    _save(EVENTS_FILE, data)
