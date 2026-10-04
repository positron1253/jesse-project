"""Seed SYNTHETIC vendors and priced buying needs around Sangareddy / Kandi (Telangana) for a demo.

Vendors are fictional businesses placed in real towns within 50 km of Kandi (17.60 N, 78.13 E). Every record is flagged
"demo": true. Offered prices are set a little above the table's mid price for the crop, never below the MSP, so they are
plausible but they are NOT real quotes. Demo vendor login: phone 9000000001-9000000006, PIN 1234.
Remove with:  py -3.11 scripts/seed_demo_vendors.py --clear
"""

import os
import sys
import uuid
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from krishi import auth, crop_table  # noqa: E402
from krishi.accounts import COMMUNITIES_FILE, FARMERS_FILE  # noqa: E402
from krishi.plans import POLLS_FILE, VENDORS_FILE, _load, _save, haversine_km  # noqa: E402

CENTER = (17.5991, 78.1266)

# name, town, lat, lon, [(crop_id, quintal, grade, from, to, pickup)]
VENDORS = [
    ("Sangareddy Agro Mart", "Sangareddy", 17.6249, 78.0867, [
        ("rice", 800, "FAQ", "2027-03-15", "2027-04-30", "vendor"),
        ("maize", 400, "FAQ", "2027-03-01", "2027-04-15", "vendor"),
    ]),
    ("Patancheru Fresh Traders", "Patancheru", 17.5300, 78.2650, [
        ("tomato", 250, "A", "2027-01-20", "2027-03-10", "vendor"),
        ("brinjal", 150, "A", "2027-01-25", "2027-03-15", "vendor"),
        ("okra", 80, "A", "2027-01-15", "2027-03-05", "farmer"),
        ("green_chilli", 100, "A", "2027-02-01", "2027-04-10", "vendor"),
    ]),
    ("Sadasivpet Farmers Co-op", "Sadasivpet", 17.6200, 77.9490, [
        ("maize", 600, "FAQ", "2027-03-01", "2027-04-20", "vendor"),
        ("chana", 300, "FAQ", "2027-02-20", "2027-04-05", "vendor"),
        ("jowar", 200, "FAQ", "2027-03-01", "2027-04-10", "farmer"),
    ]),
    ("Narsapur Oils and Pulses", "Narsapur", 17.7300, 78.2800, [
        ("groundnut", 250, "FAQ", "2027-03-10", "2027-04-25", "vendor"),
        ("masoor", 120, "FAQ", "2027-02-25", "2027-04-10", "vendor"),
        ("chana", 200, "FAQ", "2027-02-20", "2027-04-05", "vendor"),
    ]),
    ("Bowenpally Market Agents", "Bowenpally, Hyderabad", 17.4700, 78.4800, [
        ("onion", 500, "A", "2027-03-05", "2027-04-30", "vendor"),
        ("cabbage", 200, "A", "2027-01-20", "2027-03-05", "vendor"),
        ("cauliflower", 150, "A", "2027-01-20", "2027-03-05", "vendor"),
        ("coriander", 40, "A", "2027-01-10", "2027-02-28", "farmer"),
    ]),
    ("Shankarpally Feed and Rice Mill", "Shankarpally", 17.4500, 78.1300, [
        ("rice", 600, "FAQ", "2027-03-20", "2027-05-10", "vendor"),
        ("maize", 500, "FAQ", "2027-03-01", "2027-04-30", "vendor"),
    ]),
]


def _price(crop_id):
    """Offer = the table's mid price x 1.05, and never below the MSP."""
    df = crop_table.load_crops()
    g = df[df.crop_id == crop_id]
    row = (g[g.state == "Telangana"] if (g.state == "Telangana").any() else g[g.state == "*"]).iloc[0]
    msp = float(row["msp_rs_q"]) if row["msp_rs_q"] == row["msp_rs_q"] else 0.0
    return int(round(max(float(row["price_q_mid"]) * 1.05, msp * 1.02) / 50.0) * 50)


def clear():
    vendors = _load(VENDORS_FILE)
    ids = {v["id"] for v in vendors if v.get("demo")}
    _save(VENDORS_FILE, [v for v in vendors if v["id"] not in ids])
    _save(POLLS_FILE, [p for p in _load(POLLS_FILE) if p["vendor_id"] not in ids])
    _save(COMMUNITIES_FILE, [c for c in _load(COMMUNITIES_FILE) if c["vendor_id"] not in ids])
    return len(ids)


def main():
    removed = clear()
    vendors, polls, comms = _load(VENDORS_FILE), _load(POLLS_FILE), _load(COMMUNITIES_FILE)
    farmers = _load(FARMERS_FILE)
    now = datetime.now().isoformat()
    n_polls = 0
    for i, (name, town, lat, lon, needs) in enumerate(VENDORS, 1):
        vid = str(uuid.uuid4())
        km = haversine_km(CENTER[0], CENTER[1], lat, lon)
        assert km <= 50, (name, km)
        vendors.append({"id": vid, "name": name, "latitude": lat, "longitude": lon, "created_at": now,
                        "phone": f"900000000{i}", "pin_hash": auth.hash_pin("1234"), "state": "Telangana",
                        "district": "Sangareddy" if "Hyderabad" not in town else "Hyderabad", "demo": True})
        cid = str(uuid.uuid4())
        members = [{"id": vid, "name": name, "type": "vendor"}]
        for f in farmers:
            d = haversine_km(lat, lon, f["latitude"], f["longitude"])
            if d <= 50:
                members.append({"id": f["id"], "name": f["name"], "type": "farmer", "distance": round(d, 2)})
        messages = []
        for crop_id, qty, grade, d_from, d_to, pickup in needs:
            price = _price(crop_id)
            product = crop_table.crop_names(crop_id)["en"]
            polls.append({"id": str(uuid.uuid4()), "community_id": cid, "vendor_id": vid, "vendor_name": name,
                          "product": product, "quantity": qty, "unit": "quintal", "deadline": d_to, "status": "open",
                          "created_at": now, "responses": [], "crop_id": crop_id, "price_per_quintal": price,
                          "grade": grade, "delivery_from": d_from, "delivery_to": d_to, "pickup": pickup,
                          "place": town, "demo": True})
            messages.append({"id": str(uuid.uuid4()), "user_id": vid, "user_name": name, "user_type": "vendor",
                             "content": f"I need {qty} quintal of {product} at Rs {price}/quintal, delivery {d_from} to {d_to}. "
                                        f"Please respond on poll if you can contribute.", "timestamp": now})
            n_polls += 1
        comms.append({"id": cid, "name": f"{name}'s Community", "vendor_id": vid, "vendor_name": name,
                      "members": members, "messages": messages, "created_at": now, "demo": True})
        print(f"{name:34s} {town:24s} {km:5.1f} km from Kandi, {len(needs)} needs")
    _save(VENDORS_FILE, vendors)
    _save(POLLS_FILE, polls)
    _save(COMMUNITIES_FILE, comms)
    print(f"replaced {removed} old demo vendors; seeded {len(VENDORS)} vendors with {n_polls} priced needs")


if __name__ == "__main__":
    if "--clear" in sys.argv:
        print(f"removed {clear()} demo vendors")
    else:
        main()
