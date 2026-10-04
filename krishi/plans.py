"""Planting registry (plans.json) and nearby market signals (other farmers' plans + vendor demand)."""

import json
import math
import os
import uuid
from datetime import datetime

from krishi.recommender import NearbySignals

ROOT = os.path.dirname(os.path.dirname(__file__))
PLANS_FILE = os.path.join(ROOT, "plans.json")
POLLS_FILE = os.path.join(ROOT, "polls.json")
VENDORS_FILE = os.path.join(ROOT, "vendors.json")

TO_QUINTAL = {"quintal": 1.0, "kg": 0.01, "ton": 10.0, "tonne": 10.0}

# Free-text product names in older polls -> crop_id
SYNONYMS = {
    "paddy": "rice", "dhan": "rice", "gehu": "wheat", "gehun": "wheat", "makka": "maize", "corn": "maize",
    "arhar": "tur", "toor": "tur", "pigeon pea": "tur", "gram": "chana", "chickpea": "chana",
    "green gram": "moong", "mung": "moong", "black gram": "urad", "lentil": "masoor", "soya": "soybean",
    "soyabean": "soybean", "peanut": "groundnut", "sarson": "mustard", "til": "sesame", "kapas": "cotton",
    "sugar cane": "sugarcane", "aloo": "potato", "potatoes": "potato", "pyaz": "onion", "kanda": "onion",
    "onions": "onion", "tamatar": "tomato", "tomatoes": "tomato", "baingan": "brinjal", "vangi": "brinjal",
    "eggplant": "brinjal", "bhindi": "okra", "ladies finger": "okra", "gobi": "cauliflower",
    "chilli": "green_chilli", "mirchi": "green_chilli", "lauki": "bottle_gourd", "dudhi": "bottle_gourd",
    "lahsun": "garlic", "haldi": "turmeric", "dhaniya": "coriander", "kela": "banana",
}


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def to_crop_id(product, known_ids):
    p = str(product or "").strip().lower()
    if p in known_ids:
        return p
    if p.replace(" ", "_") in known_ids:
        return p.replace(" ", "_")
    if p in SYNONYMS:
        return SYNONYMS[p]
    if p.rstrip("s") in known_ids:
        return p.rstrip("s")
    return None


def poll_quantity_q(poll):
    return float(poll.get("quantity", 0)) * TO_QUINTAL.get(str(poll.get("unit", "quintal")).lower(), 0)


def save_plan(farmer_id, lat, lon, season, plan, meta=None):
    """Replace this farmer's plan for the season with the new one."""
    plans = [p for p in _load(PLANS_FILE) if not (p["farmer_id"] == farmer_id and p["season"] == season)]
    now = datetime.now().isoformat()
    for r in plan.rows:
        plans.append({
            "id": str(uuid.uuid4()), "farmer_id": farmer_id, "lat": lat, "lon": lon, "season": season,
            "plot": r.plot, "crop_id": r.crop_id, "acres": r.acres,
            "yield_q_lo": r.yield_q[0], "yield_q_hi": r.yield_q[1], "created_at": now,
            "water": (meta or {}).get("water"), "soil": (meta or {}).get("soil"), "state": (meta or {}).get("state"),
            "taw": (meta or {}).get("taw"), "sow_date": (meta or {}).get("sow_date"),
            "place": (meta or {}).get("lat_label"),
        })
    _save(PLANS_FILE, plans)


def farmer_plan(farmer_id, season):
    return [p for p in _load(PLANS_FILE) if p["farmer_id"] == farmer_id and p["season"] == season]


def nearby_signals(lat, lon, season, known_ids, km=50, exclude_farmer=None):
    sig = NearbySignals()
    farmers_seen = {}
    for p in _load(PLANS_FILE):
        if p["season"] != season or p["farmer_id"] == exclude_farmer or p.get("demo"):
            continue  # synthetic demo plans must never influence real recommendations
        if haversine_km(lat, lon, p["lat"], p["lon"]) > km:
            continue
        c = p["crop_id"]
        sig.planned_acres[c] = sig.planned_acres.get(c, 0) + p["acres"]
        farmers_seen.setdefault(c, set()).add(p["farmer_id"])
    sig.n_plans = {c: len(f) for c, f in farmers_seen.items()}

    vendors = {v["id"]: v for v in _load(VENDORS_FILE)}
    for poll in _load(POLLS_FILE):
        if poll.get("status") != "open":
            continue
        v = vendors.get(poll["vendor_id"])
        if not v:
            continue
        d = haversine_km(lat, lon, v["latitude"], v["longitude"])
        if d > km:
            continue
        c = poll.get("crop_id") or to_crop_id(poll.get("product"), known_ids)
        if not c:
            continue
        committed = sum(r.get("quantity", 0) for r in poll.get("responses", [])) * TO_QUINTAL.get(
            str(poll.get("unit", "quintal")).lower(), 0)
        open_q = max(0.0, poll_quantity_q(poll) - committed)
        # Unproven vendors count at 50% (panel decision) until they have a delivery record
        sig.vendor_q[c] = sig.vendor_q.get(c, 0) + 0.5 * open_q
        sig.buyers.setdefault(c, []).append({**poll, "distance_km": round(d, 1), "open_q": open_q})
    for c in sig.buyers:
        sig.buyers[c].sort(key=lambda b: b["distance_km"])
    return sig


def supply_coming(lat, lon, season=None, km=50):
    """For vendors: planned production near them, by crop."""
    out = {}
    for p in _load(PLANS_FILE):
        if (season and p["season"] != season) or p.get("demo"):
            continue
        if haversine_km(lat, lon, p["lat"], p["lon"]) > km:
            continue
        o = out.setdefault((p["season"], p["crop_id"]), {"farms": set(), "acres": 0, "q_lo": 0, "q_hi": 0})
        o["farms"].add(p["farmer_id"])
        o["acres"] += p["acres"]
        o["q_lo"] += p.get("yield_q_lo", 0)
        o["q_hi"] += p.get("yield_q_hi", 0)
    return [{"season": s, "crop_id": c, "farms": len(v["farms"]), "acres": v["acres"],
             "q_lo": round(v["q_lo"]), "q_hi": round(v["q_hi"])} for (s, c), v in sorted(out.items())]


def farmer_rows(farmer_id):
    """Every saved plan row of this farmer (all seasons), newest sowing first."""
    rows = [p for p in _load(PLANS_FILE) if p["farmer_id"] == farmer_id]
    return sorted(rows, key=lambda p: (p.get("sow_date") or p.get("created_at") or ""), reverse=True)


def update_row(row_id, **fields):
    rows = _load(PLANS_FILE)
    for p in rows:
        if p["id"] == row_id:
            p.update(fields)
            _save(PLANS_FILE, rows)
            return True
    return False


def delete_row(row_id, farmer_id):
    rows = _load(PLANS_FILE)
    kept = [p for p in rows if not (p["id"] == row_id and p["farmer_id"] == farmer_id)]
    _save(PLANS_FILE, kept)
    return len(kept) != len(rows)
