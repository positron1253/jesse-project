"""Right-size a pump for a crop plan, and estimate solar payback.

Everything here is arithmetic on the farmer's own numbers. No prices are built in: tariffs, diesel price and the
quoted system cost are inputs, because they vary by state, vendor and year and I could not verify defaults.

Verified inputs:
  - PM-KUSUM Component B (standalone solar pump): 30% central + 30% state subsidy, farmer pays 40%
    (10% own + 30% bank finance)  [SBI / quickestimate summaries, secondary sources]
  - Maharashtra MSKVY 2.0 promises 8 hours of daytime power on agriculture feeders (used as the default pumping window)
  - diesel 2.68 kg CO2/litre (86% carbon, 0.85 kg/L), grid 0.727 kg CO2/kWh (CEA v19, 2023-24, secondary summary)
Assumptions (editable):
  - array size = 1.25 kWp per kW of pump input power
  - field application efficiency 60% (flood) or 90% (drip) when converting crop water need to pumped water
  - diesel gensets/pumps use about 0.35 litre per kWh of shaft energy
"""

import math

from krishi import water

STANDARD_HP = [1, 2, 3, 5, 7.5, 10, 15, 20]
KUSUM_B_SUBSIDY_SHARE = 0.60
ARRAY_KWP_PER_KW = 1.25
DIESEL_L_PER_KWH = 0.35


def peak_demand_mm_day(lat, lon, crop_id, season, duration, percentile=0.90, sow=None):
    """Peak daily crop water need (ETc, mm/day): mid-season Kc x the 90th percentile daily ET0 over past seasons."""
    hist = water.fetch_history(round(lat, 2), round(lon, 2))
    c = water.crop_water_table().loc[crop_id]
    m, dd = water.sow_md(season, sow)
    mid_lo, mid_hi = int(duration * 0.45), int(duration * 0.75)
    vals = []
    from datetime import date
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, dd))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        vals.extend(hist["et0"][i0 + mid_lo:i0 + mid_hi])
    if not vals:
        return None
    return float(c["kc_mid"]) * water._pct(vals, percentile)


def size_pump(acres, peak_mm_day, hours_per_day=8.0, head_m=40.0, wire_to_water_eff=0.35, field_eff=0.60):
    """Smallest standard pump that can deliver the peak daily need inside the available pumping window."""
    daily_m3 = peak_mm_day / field_eff * 4.047 * acres
    flow_m3h = daily_m3 / hours_per_day
    hydraulic_kw = 9.81 * (flow_m3h / 3600.0) * head_m
    input_kw = hydraulic_kw / wire_to_water_eff
    hp_needed = input_kw / 0.746
    hp = next((h for h in STANDARD_HP if h >= hp_needed), math.ceil(hp_needed))
    return {"daily_m3": daily_m3, "flow_m3h": flow_m3h, "input_kw": input_kw, "hp_needed": hp_needed,
            "hp": hp, "array_kwp": round(hp * 0.746 * ARRAY_KWP_PER_KW, 1)}


def solar_payback(system_cost_rs, annual_kwh, source="grid", grid_tariff_rs_kwh=None, diesel_price_rs_l=None,
                  subsidy_share=KUSUM_B_SUBSIDY_SHARE):
    """Years for the farmer's own share to be repaid by avoided energy cost. Needs the farmer's own prices."""
    farmer_share = system_cost_rs * (1 - subsidy_share)
    out = {"farmer_share_rs": farmer_share, "subsidy_rs": system_cost_rs * subsidy_share}
    if source == "diesel":
        litres = annual_kwh * DIESEL_L_PER_KWH
        out["annual_litres"] = litres
        out["annual_saving_rs"] = litres * diesel_price_rs_l if diesel_price_rs_l else None
        out["annual_co2_kg"] = litres * water.DIESEL_KG_CO2_PER_LITRE
    else:
        out["annual_saving_rs"] = annual_kwh * grid_tariff_rs_kwh if grid_tariff_rs_kwh else None
        out["annual_co2_kg"] = annual_kwh * water.GRID_KG_CO2_PER_KWH
    s = out["annual_saving_rs"]
    out["payback_years"] = farmer_share / s if s and s > 0 else None
    return out
