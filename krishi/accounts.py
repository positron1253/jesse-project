"""Account helpers that touch more than one data file."""

import json
import os

from krishi.plans import haversine_km

ROOT = os.path.dirname(os.path.dirname(__file__))
FARMERS_FILE = os.path.join(ROOT, "farmers.json")
VENDORS_FILE = os.path.join(ROOT, "vendors.json")
COMMUNITIES_FILE = os.path.join(ROOT, "communities.json")


def _load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_location(user_id, user_type, lat, lon, state=None, district=None):
    """Save a new farm/shop location on the account and re-match the 50 km vendor communities.

    For a farmer: removed from every community, then added to those whose vendor is within 50 km (Haversine).
    For a vendor: the vendor's own community is rebuilt with the farmers now within 50 km.
    Returns True if the account was found.
    """
    path = FARMERS_FILE if user_type == "farmer" else VENDORS_FILE
    users = _load(path)
    me = next((u for u in users if u["id"] == user_id), None)
    if not me:
        return False
    me.update(latitude=lat, longitude=lon)
    if state:
        me["state"] = state
    if district:
        me["district"] = district
    _save(users, path)

    communities = _load(COMMUNITIES_FILE)
    if user_type == "farmer":
        vendors = {v["id"]: v for v in _load(VENDORS_FILE)}
        for c in communities:
            c["members"] = [m for m in c["members"] if m["id"] != user_id]
            v = vendors.get(c["vendor_id"])
            if v and haversine_km(v["latitude"], v["longitude"], lat, lon) <= 50:
                c["members"].append({"id": user_id, "name": me["name"], "type": "farmer",
                                     "distance": round(haversine_km(v["latitude"], v["longitude"], lat, lon), 2)})
    else:
        farmers = _load(FARMERS_FILE)
        for c in communities:
            if c["vendor_id"] != user_id:
                continue
            c["members"] = [m for m in c["members"] if m["type"] == "vendor"]
            for f in farmers:
                d = haversine_km(lat, lon, f["latitude"], f["longitude"])
                if d <= 50:
                    c["members"].append({"id": f["id"], "name": f["name"], "type": "farmer", "distance": round(d, 2)})
    _save(communities, COMMUNITIES_FILE)
    return True
