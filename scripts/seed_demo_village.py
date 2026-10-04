"""Seed plans.json with a SYNTHETIC village around Yavatmal so the Village screen can be demonstrated.

Every row is flagged "demo": true and the app shows a warning when demo plans are in the roll-up.
Crops are drawn at random from what is feasible on each farmer's water supply, so the mix is NOT a claim about
what real farmers there grow. Remove with:  py -3.11 scripts/seed_demo_village.py --clear
"""

import json
import os
import random
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from krishi import recommender as R, water  # noqa: E402
from krishi.plans import PLANS_FILE, _load, _save  # noqa: E402

CENTER = (20.39, 78.13)
N = 40


def main(clear=False, season="Rabi", seed=42):
    plans = [p for p in _load(PLANS_FILE) if not p.get("demo")]
    if clear:
        _save(PLANS_FILE, plans)
        print("demo plans removed")
        return
    rng = random.Random(seed)
    ctx = {"lat": round(CENTER[0], 2), "lon": round(CENTER[1], 2), "taw": water.SOIL_TAW["black"]}
    temp = 24.5 if season == "Rabi" else 27.8
    # water supply mix of the demo village (an assumption, not data)
    mix = ["rain"] * 18 + ["till_dec"] * 10 + ["till_mar"] * 8 + ["all_year"] * 4
    cache = {}
    for i in range(N):
        level = rng.choice(mix)
        acres = round(rng.uniform(1.5, 6.0) * 2) / 2
        irrigated_share = 0.0 if level == "rain" else rng.choice([0.3, 0.5, 0.7])
        parts = [("rain", round(acres * (1 - irrigated_share) * 2) / 2)]
        if level != "rain":
            parts.append(("water", round(acres * irrigated_share * 2) / 2))
        lat = CENTER[0] + rng.uniform(-0.03, 0.03)
        lon = CENTER[1] + rng.uniform(-0.03, 0.03)
        for plot, a in parts:
            if a <= 0:
                continue
            w = "rain" if plot == "rain" else level
            if w not in cache:
                cache[w] = R.rank_crops("Maharashtra", season, R.Plot(plot, 1.0, w), {"temperature": temp}, 7.8,
                                        R.NearbySignals(), top_n=6, climate_ctx=ctx)
            opts = cache[w]
            if not opts:
                continue
            o = rng.choice(opts[:5])
            plans.append({"id": f"demo-{i}-{plot}", "farmer_id": f"demo-farmer-{i:02d}", "lat": lat, "lon": lon,
                          "season": season, "plot": plot, "crop_id": o.crop_id, "acres": a,
                          "yield_q_lo": round(o.yield_q_acre[0] * a, 1), "yield_q_hi": round(o.yield_q_acre[1] * a, 1),
                          "created_at": "2026-10-04T00:00:00", "water": level if plot == "water" else None,
                          "soil": "Black / Regur (Deccan, cotton soil)", "state": "Maharashtra", "demo": True})
    _save(PLANS_FILE, plans)
    print(f"seeded {sum(1 for p in plans if p.get('demo'))} demo plan rows for {N} synthetic farmers ({season})")


if __name__ == "__main__":
    main(clear="--clear" in sys.argv)
