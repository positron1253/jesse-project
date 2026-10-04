"""Quantified benefit simulation for the reference site (Yavatmal, Maharashtra).

Writes reports/impact_report.md and reports/impact_results.json.
Everything is a simulation over the last ~30 seasons of ERA5 weather at the site, against a STATED baseline.
It is not field evidence; the report says how to validate it in a pilot.

    py -3.11 scripts/run_impact.py
"""

import json
import os
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from krishi import crop_table, pump, recommender as R, village, water  # noqa: E402

LAT, LON = 20.39, 78.13
SOIL = "black"
TAW = water.SOIL_TAW[SOIL]
OUT_DIR = os.path.join(ROOT, "reports")
HIST = water.fetch_history(round(LAT, 2), round(LON, 2))


def duration(crop, season):
    t = crop_table.crops_for("Maharashtra", season)
    return int(t[t.crop_id == crop].iloc[0]["duration_days"])


def fmt(x, nd=0):
    return f"{x:,.{nd}f}"


def s1_scheduling():
    """Per acre per season: baseline calendar flood vs schedule-by-soil-need vs schedule + efficient method."""
    rows = []
    for crop, season in (("wheat", "Rabi"), ("chana", "Rabi"), ("mustard", "Rabi"), ("onion", "Rabi"),
                         ("tomato", "Rabi"), ("cotton", "Kharif"), ("tur", "Kharif")):
        r = water.compare_practice(LAT, LON, crop, season, duration(crop, season), TAW, "all_year", 1.0, hist=HIST)
        if not r:
            continue
        b, f, e = r["baseline"], r["sched_flood"], r["sched_efficient"]
        rows.append({"crop": crop, "season": season, "practice_irrigations": r["n_irrigations_practice"],
                     "baseline_m3": b["m3"], "baseline_yield": b["rel_yield"], "baseline_kwh": b["kwh"],
                     "flood_m3": f["m3"], "flood_yield": f["rel_yield"], "flood_saved_pct": f["saved_pct"],
                     "flood_saved_p10": f["saved_pct_p10"], "flood_saved_p90": f["saved_pct_p90"],
                     "eff_m3": e["m3"], "eff_yield": e["rel_yield"], "eff_saved_pct": e["saved_pct"],
                     "eff_saved_p10": e["saved_pct_p10"], "eff_saved_p90": e["saved_pct_p90"],
                     "eff_saved_kwh": e["saved_kwh"], "eff_saved_co2_kg": e["saved_co2_kg"],
                     "yield_change_flood_pct": f["yield_change_pct"], "yield_change_eff_pct": e["yield_change_pct"],
                     "years": r["n_years"]})
    return rows


def s2_sensitivity(crop="cotton", season="Kharif"):
    out = []
    for eff in (0.25, 0.35, 0.50):
        for head in (30, 40, 60):
            r = water.compare_practice(LAT, LON, crop, season, duration(crop, season), TAW, "all_year", 1.0,
                                       head_m=head, pump_eff=eff, hist=HIST)
            e = r["sched_efficient"]
            out.append({"pump_efficiency": eff, "head_m": head, "saved_kwh": e["saved_kwh"], "saved_co2_kg": e["saved_co2_kg"],
                        "baseline_kwh": r["baseline"]["kwh"]})
    return out


def s3_choice_matters(season="Rabi", water_level="till_mar"):
    """How much the CROP CHOICE changes irrigation water, usual profit and bad-year result on the same well."""
    opts = R.rank_crops("Maharashtra", season, R.Plot("w", 1.0, water_level), {"temperature": 24.5}, 7.8,
                        R.NearbySignals(), top_n=0, climate_ctx={"lat": round(LAT, 2), "lon": round(LON, 2), "taw": TAW})
    rows = []
    for o in opts:
        c = o.climate
        if not c:
            continue
        m3 = c["irrigation_mm_p50"] * 4.047
        rows.append({"crop": o.crop_id, "irrigation_m3_per_acre": m3, "usual_profit": o.profit_mid, "bad_year": o.profit_worst,
                     "rs_per_m3": (o.profit_mid / m3) if m3 > 1 else None, "estimated_numbers": bool(o.est),
                     "risk": o.risk, "p_poor": c["p_poor"]})
    rows.sort(key=lambda r: r["irrigation_m3_per_acre"])
    return rows


def s4_village_range(season="Rabi", km=5):
    """Demo-village irrigation demand: planned mix vs the thirstiest vs the thriftiest profitable crop on each water supply."""
    res = village.village_water(LAT, LON, km, season)
    if not res:
        return None
    by_level = {}
    for r in res["rows"]:
        if r["water"] != "rain":
            by_level[r["water"]] = by_level.get(r["water"], 0.0) + r["acres"]
    lo = hi = 0.0
    detail = {}
    for level, acres in by_level.items():
        opts = R.rank_crops("Maharashtra", season, R.Plot("v", 1.0, level), {"temperature": 24.5}, 7.8, R.NearbySignals(),
                            top_n=0, climate_ctx={"lat": round(LAT, 2), "lon": round(LON, 2), "taw": TAW})
        feasible = [o for o in opts if o.climate and o.profit_mid > 0 and not o.est]
        if not feasible:
            continue
        mms = [o.climate["irrigation_mm_p50"] for o in feasible]
        lo += min(mms) * 4.047 * acres
        hi += max(mms) * 4.047 * acres
        detail[level] = {"acres": acres, "min_mm": min(mms), "max_mm": max(mms), "n_crops": len(feasible)}
    return {"planned_m3": res["demand_m3_p50"], "thriftiest_m3": lo, "thirstiest_m3": hi, "farmers": res["farmers"],
            "irrigated_acres": res["irrigated_acres"], "detail": detail, "demo": res["demo"]}


def s5_loss_at_stake():
    """Value of post-harvest loss per acre (NABCONS loss share x usual revenue): an upper bound on what buyers lined up could protect."""
    rows = []
    df = crop_table.crops_for("Maharashtra", "Rabi")
    for _, r in df.iterrows():
        rev = (r.yield_q_acre_lo + r.yield_q_acre_hi) / 2 * r.price_q_mid * 0.92
        rows.append({"crop": r.crop_id, "loss_frac": r.loss_frac, "revenue_per_acre": rev, "value_at_stake": rev * r.loss_frac,
                     "perishable": bool(r.perishable), "est": bool(r.cost_est)})
    rows.sort(key=lambda x: -x["value_at_stake"])
    return rows


def s6_pump_sizing():
    out = []
    for crop, season in (("wheat", "Rabi"), ("cotton", "Kharif"), ("tomato", "Rabi")):
        peak = pump.peak_demand_mm_day(LAT, LON, crop, season, duration(crop, season))
        for label, fe in (("flood", 0.6), ("drip", 0.9)):
            sz = pump.size_pump(2.0, peak, 8, 40, 0.35, fe)
            out.append({"crop": crop, "method": label, "peak_mm_day": peak, "hp": sz["hp"], "flow_m3h": sz["flow_m3h"],
                        "array_kwp": sz["array_kwp"]})
    return out


def main():
    res = {"site": {"lat": LAT, "lon": LON, "soil": SOIL, "taw_mm_per_m": TAW,
                    "seasons": f"{HIST['dates'][0].year}-{HIST['dates'][-1].year - 1}", "generated": date.today().isoformat()},
           "s1": s1_scheduling(), "s2": s2_sensitivity(), "s3": s3_choice_matters(), "s4": s4_village_range(),
           "s5": s5_loss_at_stake(), "s6": s6_pump_sizing()}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "impact_results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)

    L = []
    w = L.append
    w("# Quantified benefit: reference-site simulation\n")
    w(f"*Generated {res['site']['generated']} by `scripts/run_impact.py`. Site: Yavatmal, Maharashtra ({LAT}, {LON}), black "
      f"(vertisol) soil, {res['site']['seasons']} seasons of ERA5 weather. Every figure is a **simulation against a stated "
      "baseline, not field evidence**. Section 8 says how to validate it in a pilot.*\n")
    w("## 1. Baselines and what is being measured\n")
    w("| Item | Baseline (what the farmer does today) | Our approach |\n|---|---|---|")
    w("| Irrigation timing | The crop's usual number of **flood irrigations on fixed dates** (package-of-practice count from the crop table), "
      "60 mm gross each, no rain adjustment | Water when the soil needs it, using the 7-day forecast (lever 1) |")
    w("| Application method | Flood, 60% field efficiency | Drip / micro-sprinkler, 90% (lever 2, where suitable) |")
    w("| Crop choice | Not claimed as a saving. Section 4 shows how much the choice moves water and profit | Crops ranked on the farmer's own water supply |")
    w("| Pump | 40 m lift, 35% wire-to-water efficiency (assumptions, Section 3 tests others) | Same pump, fewer hours |")
    w("| Emissions | Grid 0.727 kg CO2/kWh (CEA v19, 2023-24) | Energy saved x grid factor |\n")

    w("## 2. Irrigation scheduling and method: water, energy, CO2 and yield (per acre, per season, 30 past seasons)\n")
    w("Yield is relative to the unstressed potential (1.00 = no water stress). A water saving only counts if yield holds.\n")
    w("| Crop | Season | Usual irrigations | Baseline water m³ | Baseline yield | Lever 1 water m³ (vs baseline, P10–P90) | Lever 1 yield | Levers 1+2 water m³ (vs baseline, P10–P90) | Levers 1+2 yield | kWh saved | CO2 saved kg |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["s1"]:
        w(f"| {r['crop']} | {r['season']} | {r['practice_irrigations']} | {fmt(r['baseline_m3'])} | {r['baseline_yield']:.2f} | "
          f"{fmt(r['flood_m3'])} ({r['flood_saved_pct']:+.0f}%, {r['flood_saved_p10']:+.0f} to {r['flood_saved_p90']:+.0f}) | {r['flood_yield']:.2f} | "
          f"{fmt(r['eff_m3'])} ({r['eff_saved_pct']:+.0f}%, {r['eff_saved_p10']:+.0f} to {r['eff_saved_p90']:+.0f}) | {r['eff_yield']:.2f} | "
          f"{fmt(r['eff_saved_kwh'])} | {fmt(r['eff_saved_co2_kg'])} |")
    w("\n**Reading it honestly**")
    w("- Where the baseline already waters enough (cotton, tomato, wheat with drip), scheduling and an efficient method cut water at equal yield.")
    w("- Where the usual practice is a deliberate shortcut (chana and mustard get about 2 irrigations and reach roughly 63–66% of full yield), the "
      "scheduler uses **more** water and lifts yield. That is a yield gain, not a water saving. Negative \"saved\" figures above mean extra water.\n")

    w("## 3. Sensitivity of the energy result to pump assumptions (cotton, Kharif, levers 1+2, per acre)\n")
    w("| Pump efficiency | Lift 30 m | Lift 40 m | Lift 60 m |\n|---|---|---|---|")
    for eff in (0.25, 0.35, 0.50):
        cells = [next(x for x in res["s2"] if x["pump_efficiency"] == eff and x["head_m"] == h) for h in (30, 40, 60)]
        w(f"| {int(eff*100)}% | " + " | ".join(f"{fmt(c['saved_kwh'])} kWh ({fmt(c['saved_co2_kg'])} kg CO2)" for c in cells) + " |")
    w("\nEnergy scales with lift and inversely with efficiency, so the farmer's own pump details should replace these assumptions.\n")

    w("## 4. Crop choice on the same well: how much it moves water and money (Rabi, well lasts till March, per acre)\n")
    w("This is the size of the crop-choice lever, not a claimed saving: the farmer's alternative crop is not known.\n")
    w("| Crop | Irrigation m³ | Usual profit ₹ | Bad year ₹ | ₹ per m³ | Poor-yield seasons | Risk | Numbers estimated |\n|---|---|---|---|---|---|---|---|")
    for r in res["s3"]:
        rs = f"{r['rs_per_m3']:.0f}" if r["rs_per_m3"] is not None else "n/a (rain-fed)"
        w(f"| {r['crop']} | {fmt(r['irrigation_m3_per_acre'])} | {fmt(r['usual_profit'])} | {fmt(r['bad_year'])} | {rs} | "
          f"{r['p_poor']*100:.0f}% | {r['risk']} | {'yes' if r['estimated_numbers'] else 'no'} |")
    w("")

    w("## 5. Village roll-up (SYNTHETIC demo village, 40 farmers, 5 km radius, Rabi)\n")
    v = res["s4"]
    if v:
        w(f"- Planned crop mix: **{fmt(v['planned_m3'])} m³** of irrigation water in a usual year ({v['irrigated_acres']:.0f} irrigated acres).")
        w(f"- If every irrigated acre went to the *thriftiest* profitable crop for its water supply: {fmt(v['thriftiest_m3'])} m³.")
        w(f"- If every irrigated acre went to the *thirstiest* profitable crop: {fmt(v['thirstiest_m3'])} m³.")
        w("- The demo plans are random draws and say nothing about what real farmers grow; the point is that the roll-up exists and the range is wide. "
          "Water available per village is an input (Water Security Plan), so no gap is claimed here.\n")

    w("## 6. Post-harvest loss at stake (value per acre, upper bound)\n")
    w("Loss share (NABCONS 2022, or marked estimate) x usual revenue. This is the most that buyers lined up before sowing could protect; "
      "**the actual reduction is a hypothesis to measure in the pilot**, not a result.\n")
    w("| Crop | Loss share | Revenue ₹/acre | Value at stake ₹/acre | Perishable |\n|---|---|---|---|---|")
    for r in res["s5"][:8]:
        w(f"| {r['crop']} | {r['loss_frac']*100:.1f}% | {fmt(r['revenue_per_acre'])} | {fmt(r['value_at_stake'])} | {'yes' if r['perishable'] else 'no'} |")
    w("")

    w("## 7. Pump sizing for 2 acres (8 h window, 40 m lift, 35% pump efficiency)\n")
    w("| Crop | Method | Peak need mm/day | Smallest pump HP | Flow m³/h | Solar kWp |\n|---|---|---|---|---|---|")
    for r in res["s6"]:
        w(f"| {r['crop']} | {r['method']} | {r['peak_mm_day']:.1f} | {r['hp']} | {r['flow_m3h']:.1f} | {r['array_kwp']} |")
    w("\nDrip lets the same land run on a smaller pump and a smaller solar array. Subsidy (PM-KUSUM B: 30% central + 30% state, "
      "farmer 40%) applies to the system cost the farmer is quoted; payback uses the farmer's own tariff or diesel price.\n")

    w("## 8. Assumptions, what is verified, and how to validate\n")
    w("**Verified from published sources:** FAO-56 crop coefficients, root depths and depletion fractions; FAO-33 Ky for nine crops; IMD rain classes; "
      "grid emission factor (CEA v19, 2023-24, via a secondary summary); diesel 2.68 kg CO2/L (carbon-content derivation); PM-KUSUM B subsidy split (secondary).\n")
    w("**Assumptions, not verified:** soil water-holding capacity by soil class; stage lengths (20/25/30/25%); effective rain 85%; profile 10% depleted at sowing; "
      "60 mm gross per flood irrigation; pump lift 40 m and efficiency 35%; Ky = 1.0 for crops without a verified value; array 1.25 kWp per kW of pump; "
      "vegetable cost and price figures marked estimated in the crop table.\n")
    w("**Not modelled:** waterlogging and flooding losses, heat stress, pests and disease, market price movements in the water results, groundwater recharge.\n")
    w("**Pilot validation plan:** in one cluster, give 20 farmers the schedule and 20 matched farmers none; fit a flow meter or hour-meter on each pump; "
      "log irrigations, hours, litres of diesel or kWh, and harvest weight per acre for one season; compare against the same farmers' previous season and against the matched group. "
      "Replace every assumption above with measured values.\n")
    with open(os.path.join(OUT_DIR, "impact_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("wrote reports/impact_report.md and reports/impact_results.json")


if __name__ == "__main__":
    main()
