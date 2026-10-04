"""Village water roll-up: add up farmers' saved crop plans into irrigation demand for a village / cluster.

This is the bottom-up version of what Atal Bhujal Yojana asks gram panchayats to do (water budgets and Water Security
Plans, demand-side measures such as crop change and drip). Demand comes from the farmers' own plans; the water that
is sustainably available is an INPUT (from a Water Security Plan or a local estimate) because no verified village
aquifer data is available to the app.
"""

from datetime import date

from krishi import crop_table, plans as plans_mod, water

DEMO_FLAG = "demo"


def plans_near(lat, lon, km=5.0, season=None):
    out = []
    for p in plans_mod._load(plans_mod.PLANS_FILE):
        if season and p["season"] != season:
            continue
        if plans_mod.haversine_km(lat, lon, p["lat"], p["lon"]) <= km:
            out.append(p)
    return out


def _duration(crop_id):
    df = crop_table.load_crops()
    return int(df[df.crop_id == crop_id].duration_days.iloc[0])


def village_water(lat, lon, km=5.0, season="Rabi", budget_m3=None, head_m=water.PUMP_HEAD_M,
                  pump_eff=water.PUMP_EFFICIENCY):
    rows = plans_near(lat, lon, km, season)
    if not rows:
        return None
    hist = water.fetch_history(round(lat, 2), round(lon, 2))
    agg = {}
    for p in rows:
        level = p.get("water") if p.get("plot") == "water" else "rain"
        level = level or "rain"
        soil = p.get("soil")
        key = (p["crop_id"], level, soil, p.get("taw"))
        a = agg.setdefault(key, {"acres": 0.0, "farmers": set(), "demo": False})
        a["acres"] += p["acres"]
        a["farmers"].add(p["farmer_id"])
        a["demo"] = a["demo"] or bool(p.get(DEMO_FLAG))
    out_rows = []
    for (crop_id, level, soil, row_taw), a in agg.items():
        taw = row_taw or water.SOIL_TAW[water.SOIL_OF_TYPE.get(soil, "unknown")]
        prof = water.climate_profile(lat, lon, crop_id, season, _duration(crop_id), taw, level, hist=hist) \
            if level != "rain" else None
        mm50 = prof["irrigation_mm_p50"] if prof else 0.0
        mm90 = prof["irrigation_mm_p90"] if prof else 0.0
        m3_50, m3_90 = mm50 * 4.047 * a["acres"], mm90 * 4.047 * a["acres"]
        kwh = water.pump_energy_kwh(m3_50, head_m, pump_eff)
        out_rows.append({"crop_id": crop_id, "water": level, "acres": a["acres"], "farmers": len(a["farmers"]),
                         "irrigation_mm_p50": mm50, "demand_m3_p50": m3_50, "demand_m3_p90": m3_90,
                         "kwh_p50": kwh, "co2_kg_p50": kwh * water.GRID_KG_CO2_PER_KWH, "demo": a["demo"]})
    out_rows.sort(key=lambda r: -r["demand_m3_p50"])
    tot = lambda k: sum(r[k] for r in out_rows)
    farmers = {p["farmer_id"] for p in rows}
    result = {
        "rows": out_rows, "farmers": len(farmers), "acres": tot("acres"),
        "irrigated_acres": sum(r["acres"] for r in out_rows if r["water"] != "rain"),
        "demand_m3_p50": tot("demand_m3_p50"), "demand_m3_p90": tot("demand_m3_p90"),
        "kwh_p50": tot("kwh_p50"), "co2_kg_p50": tot("co2_kg_p50"),
        "demo": any(r["demo"] for r in out_rows), "season": season, "radius_km": km,
    }
    if budget_m3:
        result["budget_m3"] = budget_m3
        result["gap_p50_m3"] = result["demand_m3_p50"] - budget_m3
        result["gap_p90_m3"] = result["demand_m3_p90"] - budget_m3
    return result


def swap_suggestions(lat, lon, season, rows, top_n=3):
    """For the biggest water users: a feasible, profitable crop on the same water supply that needs far less irrigation."""
    from krishi import recommender as R

    sugg = []
    for r in [r for r in rows if r["water"] != "rain"][:top_n]:
        taw = water.SOIL_TAW["unknown"]
        ctx = {"lat": round(lat, 2), "lon": round(lon, 2), "taw": taw}
        opts = R.rank_crops("Maharashtra", season, R.Plot("v", 1.0, r["water"]), {"temperature": 25.0}, 7.0,
                            R.NearbySignals(), top_n=0, climate_ctx=ctx)
        cur = next((o for o in opts if o.crop_id == r["crop_id"]), None)
        hist = water.fetch_history(round(lat, 2), round(lon, 2))
        best = None
        for o in opts:
            if o.crop_id == r["crop_id"] or o.profit_mid <= 0 or o.est:
                continue
            prof = o.climate
            if not prof or prof["irrigation_mm_p50"] >= 0.5 * r["irrigation_mm_p50"]:
                continue
            if best is None or o.profit_mid > best.profit_mid:
                best = o
        if best and cur:
            saved_mm = r["irrigation_mm_p50"] - best.climate["irrigation_mm_p50"]
            sugg.append({"from": r["crop_id"], "to": best.crop_id, "saved_m3_per_acre": saved_mm * 4.047,
                         "profit_change_per_acre": best.profit_mid - cur.profit_mid})
    return sugg
