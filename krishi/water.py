"""Climate risk, irrigation scheduling and pump energy from a daily soil-water balance (FAO-56).

Why this exists
  A crop recommendation based on this year's rain, or on one average, breaks in a dry or flooded year.
  Here every crop is "grown" in each of the last ~30 seasons at the farm's own coordinates (ERA5 daily
  ET0 and rainfall from Open-Meteo), on the farmer's own water supply, so we see how often it fails.

Method (FAO Irrigation & Drainage Paper 56, single crop coefficient)
  ETc  = Kc * ET0                         Kc follows the four growth stages
  Ks   = 1 if Dr <= RAW else (TAW-Dr)/(TAW-RAW)
  ETa  = Ks * ETc
  Dr   = Dr - effective_rain - irrigation + ETa          (Dr = root-zone depletion, clipped to 0..TAW)
  rel. yield = 1 - Ky * (1 - sum(ETa)/sum(ETc))           FAO-33 seasonal yield response

Assumptions that are NOT from a verified source and are exposed as parameters:
  - stage lengths: 20% initial, 25% development, 30% mid, 25% late of the crop duration
  - effective rain = 85% of rainfall (runoff, interception); profile full-ish at sowing (10% depleted)
  - soil total available water by soil class: mid-range of FAO-56 Table 19 texture ranges (I could not
    read the full table), so treat as editable
  - baseline farmer practice: flood irrigation, fixed calendar interval and depth, no rain adjustment
  - pump efficiency / head for energy: typical values, to be replaced by the farmer's own numbers
Seasonal-outlook data (ECMWF SEAS5 via Open-Meteo) is NOT used to rank crops: Indian monsoon seasonal skill
is limited at local scale, so the long-run climate record is the safer basis.
"""

import os
import statistics
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"

SEASON_START = {"Kharif": (7, 1), "Rabi": (11, 1), "Zaid": (3, 1)}   # typical sowing start; only a default, the farmer chooses


def season_of(day):
    """Season a sowing date belongs to: Kharif May-Sep, Rabi Oct-Jan, Zaid Feb-Apr."""
    m = day.month
    return "Kharif" if 5 <= m <= 9 else "Rabi" if (m >= 10 or m == 1) else "Zaid"


def default_sowing_date(today=None):
    """Next typical sowing start for the current season, or today if that start has already passed."""
    today = today or date.today()
    season = season_of(today)
    m, d = SEASON_START[season]
    start = date(today.year, m, d)
    if season == "Rabi" and today.month == 1:
        start = date(today.year - 1, m, d)
    return start if start >= today else today


def sow_md(season, sow=None):
    """(month, day) the simulations start from: the farmer's own date if given, else the season's typical start."""
    if sow:
        return (sow.month, sow.day) if hasattr(sow, "month") else tuple(sow)
    return SEASON_START[season]


def window_temp(hist, m, d, duration):
    """Median over past years of the mean temperature during the crop's own window (sowing to harvest)."""
    vals = []
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, d))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        w = hist["tmean"][i0:i0 + duration]
        vals.append(sum(w) / len(w))
    return _pct(vals, 0.5) if vals else None
STAGE_SPLIT = (0.20, 0.25, 0.30, 0.25)          # initial, development, mid, late
EFFECTIVE_RAIN = 0.85
INITIAL_DEPLETION = 0.10
DRY_DAY_MM = 2.5

# total available water (mm per metre of soil) by soil class - assumption, see module docstring
SOIL_TAW = {"sandy": 70, "red": 110, "laterite": 90, "alluvial": 150, "black": 170, "mountain": 140, "unknown": 130}
SOIL_OF_TYPE = {
    "Alluvial (Indo-Gangetic plains)": "alluvial", "Black / Regur (Deccan, cotton soil)": "black",
    "Red (Tamil Nadu, Karnataka, Odisha)": "red", "Laterite (Kerala, Konkan, NE hills)": "laterite",
    "Sandy / Desert (Rajasthan)": "sandy", "Mountain / Forest (Himalayan)": "mountain",
}

# Practice parameters (assumptions)
MAX_NET_IRRIGATION_MM = 60      # assumption: deepest single watering a farmer can really apply (net mm reaching the soil)
FLOOD_EFFICIENCY = 0.60
BASELINE_INTERVAL_DAYS = 12
BASELINE_DEPTH_MM = 70          # gross water per flood irrigation


@lru_cache(maxsize=1)
def crop_water_table():
    df = pd.read_csv(os.path.join(DATA_DIR, "crop_water.csv"))
    return df.set_index("crop_id")


# ---------------------------------------------------------------- weather history
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
HISTORY_GRID_DEG = 0.1      # ERA5 is a ~0.25 degree grid, so nearby farms can share one downloaded history


def _history_from_arrays(dates, et0, rain, tmax, tmean):
    return {"dates": dates, "et0": et0, "rain": rain, "tmax": tmax, "tmean": tmean,
            "index": {x: i for i, x in enumerate(dates)}}


@lru_cache(maxsize=32)
def _history_cached(lat, lon, first_year, last_year, timeout):
    """Daily ET0, rain, Tmax, Tmean from ERA5 (Open-Meteo archive). Kept on disk, so each ~10 km cell is downloaded once."""
    import gzip
    import json
    path = os.path.join(CACHE_DIR, f"hist_{lat:.1f}_{lon:.1f}_{first_year}_{last_year}.json.gz")
    if os.path.exists(path):
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                d = json.load(f)
            return _history_from_arrays([date.fromisoformat(x) for x in d["t"]], d["et0"], d["rain"], d["tmax"], d["tmean"])
        except Exception:
            pass                                    # unreadable cache file: fetch again
    r = requests.get(ARCHIVE, params={
        "latitude": lat, "longitude": lon, "start_date": f"{first_year}-01-01", "end_date": f"{last_year}-12-31",
        "daily": "et0_fao_evapotranspiration,precipitation_sum,temperature_2m_max,temperature_2m_mean", "timezone": "auto"},
        timeout=timeout)
    r.raise_for_status()
    d = r.json()["daily"]
    et0 = [v if v is not None else 0.0 for v in d["et0_fao_evapotranspiration"]]
    rain = [v if v is not None else 0.0 for v in d["precipitation_sum"]]
    tmax = [v if v is not None else 30.0 for v in d["temperature_2m_max"]]
    tmean = [v if v is not None else 25.0 for v in d["temperature_2m_mean"]]
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump({"t": d["time"], "et0": et0, "rain": rain, "tmax": tmax, "tmean": tmean}, f)
    except Exception:
        pass
    return _history_from_arrays([date.fromisoformat(x) for x in d["time"]], et0, rain, tmax, tmean)


def fetch_history(lat, lon, first_year=1995, last_year=None, timeout=45):
    """30 years of daily weather for the grid cell around (lat, lon). Memory- and disk-cached; raises if the service refuses
    and there is no saved copy."""
    last_year = last_year or date.today().year - 1
    g = HISTORY_GRID_DEG
    return _history_cached(round(round(lat / g) * g, 1), round(round(lon / g) * g, 1), first_year, last_year, timeout)


fetch_history.cache_clear = _history_cached.cache_clear    # used by the Home "refresh" button


def fetch_forecast(lat, lon, days=7, timeout=20):
    r = requests.get(FORECAST, params={
        "latitude": lat, "longitude": lon, "forecast_days": days, "timezone": "auto",
        "daily": "et0_fao_evapotranspiration,precipitation_sum,precipitation_probability_max"}, timeout=timeout)
    r.raise_for_status()
    d = r.json()["daily"]
    return [{"date": date.fromisoformat(t), "et0": e or 0.0, "rain": p or 0.0, "p_rain": pp or 0}
            for t, e, p, pp in zip(d["time"], d["et0_fao_evapotranspiration"], d["precipitation_sum"],
                                   d["precipitation_probability_max"])]


# ---------------------------------------------------------------- crop model
def _kc(day, D, c):
    L = [x * D for x in STAGE_SPLIT]
    if day < L[0]:
        return c["kc_ini"]
    if day < L[0] + L[1]:
        return c["kc_ini"] + (c["kc_mid"] - c["kc_ini"]) * (day - L[0]) / L[1]
    if day < L[0] + L[1] + L[2]:
        return c["kc_mid"]
    return c["kc_mid"] + (c["kc_end"] - c["kc_mid"]) * min(1.0, (day - L[0] - L[1] - L[2]) / L[3])


def water_limit_date(water, sow):
    """Last day irrigation is available for a plot: rain-only none, till Dec / Mar, or all season."""
    if water == "rain":
        return sow - timedelta(days=1)
    if water == "till_dec":
        end = date(sow.year, 12, 31)
        return end if end >= sow else date(sow.year + 1, 12, 31)
    if water == "till_mar":
        end = date(sow.year, 3, 31)
        return end if end >= sow else date(sow.year + 1, 3, 31)
    return date(9999, 1, 1)


def simulate(hist, crop_id, sow, duration, taw_per_m=130, policy="scheduled", water="all_year",
             eff=0.9, interval=BASELINE_INTERVAL_DAYS, depth=BASELINE_DEPTH_MM, n_irr=0,
             override_until=None, override_events=None):
    """One season. policy: 'rainfed' | 'scheduled' (refill at RAW) | 'baseline' (fixed interval flood) |
    'calendar' (n_irr flood irrigations spread evenly over 15-85% of the cycle = package-of-practice baseline).

    Returns dict(etc, eta, rel_yield, irrigation_mm (gross), n_irrig, rain_mm, events=[(date, gross_mm)]).
    """
    c = crop_water_table().loc[crop_id]
    i0 = hist["index"].get(sow)
    if i0 is None or i0 + duration >= len(hist["dates"]):
        return None
    allowed_until = water_limit_date(water, sow)
    if policy == "rainfed":
        allowed_until = sow - timedelta(days=1)
    zr_full = float(c["zr_m"])
    Dr = None
    etc_sum = eta_sum = gross = rain_sum = 0.0
    events = []
    last_irrig = -10**6
    cal_days = {int(duration * (0.15 + 0.70 * (j + 0.5) / n_irr)) for j in range(n_irr)} if policy == "calendar" else set()
    for k in range(duration):
        i = i0 + k
        d = hist["dates"][i]
        zr = 0.3 + (zr_full - 0.3) * min(1.0, k / (STAGE_SPLIT[0] + STAGE_SPLIT[1]) / duration)
        taw = taw_per_m * zr
        raw = float(c["p"]) * taw
        if Dr is None:
            Dr = INITIAL_DEPLETION * taw
        Dr = min(Dr, taw)
        etc = _kc(k, duration, c) * hist["et0"][i]
        ks = 1.0 if Dr <= raw else max(0.0, (taw - Dr) / max(1e-6, taw - raw))
        eta = ks * etc
        peff = EFFECTIVE_RAIN * hist["rain"][i]
        net_irrig = 0.0
        if override_until is not None and d <= override_until:
            # days already lived: use what the farmer actually watered (net mm), not what the model would have done
            net_irrig = (override_events or {}).get(d, 0.0)
            if net_irrig:
                events.append((d, net_irrig / eff))
                gross += net_irrig / eff
        elif d <= allowed_until:
            if policy == "scheduled" and Dr >= min(raw, MAX_NET_IRRIGATION_MM) and k < duration * 0.92:
                net_irrig = min(Dr, MAX_NET_IRRIGATION_MM)
                events.append((d, net_irrig / eff))
                gross += net_irrig / eff
            elif policy == "calendar" and k in cal_days:
                net_irrig = depth * FLOOD_EFFICIENCY
                events.append((d, float(depth)))
                gross += depth
            elif policy == "baseline" and (k - last_irrig) >= interval and k < duration * 0.92:
                net_irrig = depth * FLOOD_EFFICIENCY
                last_irrig = k
                events.append((d, float(depth)))
                gross += depth
        Dr = max(0.0, Dr - peff - net_irrig + eta)
        etc_sum += etc
        eta_sum += eta
        rain_sum += hist["rain"][i]
    ratio = eta_sum / etc_sum if etc_sum else 1.0
    rel = max(0.0, min(1.0, 1.0 - float(c["ky"]) * (1.0 - ratio)))
    return {"etc": etc_sum, "eta": eta_sum, "rel_yield": rel, "irrigation_mm": gross, "n_irrig": len(events),
            "rain_mm": rain_sum, "events": events}


def _pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * q
    f, c = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def longest_dry_spell(hist, sow, duration):
    i0 = hist["index"][sow]
    best = run = 0
    for r in hist["rain"][i0:i0 + duration]:
        run = run + 1 if r < DRY_DAY_MM else 0
        best = max(best, run)
    return best


def climate_profile(lat, lon, crop_id, season, duration, taw_per_m=130, water="rain", years=None, hist=None, sow=None):
    """How this crop fares across past seasons at this farm, for this plot's water supply.

    Returns dict with relative-yield percentiles (1.0 = no water stress), probability of crop failure,
    irrigation need and the longest dry spell inside the crop cycle.
    """
    hist = hist or fetch_history(round(lat, 2), round(lon, 2))
    m, dd = sow_md(season, sow)
    first, last = hist["dates"][0].year, hist["dates"][-1].year
    policy = "rainfed" if water == "rain" else "scheduled"
    rows = []
    for y in (years or range(first, last)):
        res = simulate(hist, crop_id, date(y, m, dd), duration, taw_per_m, policy, water)
        if res:
            res["dry_spell"] = longest_dry_spell(hist, date(y, m, dd), duration)
            rows.append(res)
    if not rows:
        return None
    rel = [r["rel_yield"] for r in rows]
    irr = [r["irrigation_mm"] for r in rows]
    return {
        "n_years": len(rows), "water": water,
        "rel_p10": _pct(rel, 0.10), "rel_p50": _pct(rel, 0.50), "rel_p90": _pct(rel, 0.90),
        "p_failure": sum(1 for v in rel if v < 0.5) / len(rel),
        "p_poor": sum(1 for v in rel if v < 0.75) / len(rel),
        "irrigation_mm_p50": _pct(irr, 0.50), "irrigation_mm_p90": _pct(irr, 0.90),
        "irrigations_p50": _pct([r["n_irrig"] for r in rows], 0.50),
        "rain_mm_p10": _pct([r["rain_mm"] for r in rows], 0.10), "rain_mm_p50": _pct([r["rain_mm"] for r in rows], 0.50),
        "rain_mm_p90": _pct([r["rain_mm"] for r in rows], 0.90),
        "dry_spell_p50": _pct([r["dry_spell"] for r in rows], 0.50), "dry_spell_p90": _pct([r["dry_spell"] for r in rows], 0.90),
    }


# ---------------------------------------------------------------- scheduling and energy
def pump_energy_kwh(volume_m3, head_m=40.0, efficiency=0.35):
    """Electrical energy to lift `volume_m3` of water `head_m` metres: rho*g*H*V / (3.6e6 * eta)."""
    return 9810.0 * head_m * volume_m3 / 3.6e6 / efficiency


def mm_to_m3_per_ha(mm):
    return mm * 10.0


def next_irrigation_advice(lat, lon, crop_id, days_since_sowing, duration, soil_taw=130, last_irrigation_days_ago=None,
                           recent_rain_mm=0.0, water_available=True):
    """Short-horizon advice: simulate the coming days with the forecast and say when the next watering is due.

    Starts from a conservative assumption (profile depleted to RAW if the farmer has not irrigated for a long time).
    Deliberately simple: the farmer can correct it with a soil-moisture reading.
    """
    c = crop_water_table().loc[crop_id]
    fc = fetch_forecast(lat, lon, 7)
    taw = soil_taw * float(c["zr_m"])
    raw = float(c["p"]) * taw
    Dr = 0.5 * raw if last_irrigation_days_ago is None else min(raw, 0.15 * raw * last_irrigation_days_ago)
    Dr = max(0.0, Dr - EFFECTIVE_RAIN * recent_rain_mm)
    plan = []
    for k, day in enumerate(fc):
        kc = _kc(days_since_sowing + k, duration, c)
        etc = kc * day["et0"]
        Dr = max(0.0, Dr + etc - EFFECTIVE_RAIN * day["rain"])
        plan.append({"date": day["date"], "etc_mm": round(etc, 1), "rain_mm": day["rain"], "p_rain": day["p_rain"],
                     "depletion_pct": round(100 * Dr / raw) if raw else 0})
        if Dr >= raw:
            return {"action": "irrigate", "when": day["date"], "net_mm": round(Dr), "plan": plan}
    return {"action": "wait", "when": None, "net_mm": 0, "plan": plan}


# ---------------------------------------------------------------- heavy rain, trend, practice comparison
VERY_HEAVY_RAIN_MM = 115.6       # IMD class "very heavy rain" lower bound, mm in 24 h (IMD national bulletins)
GRID_KG_CO2_PER_KWH = 0.727      # CEA CO2 Baseline Database v19, weighted average EF 2023-24 (secondary summary)
DIESEL_KG_CO2_PER_LITRE = 2.68   # 86% carbon, density 0.85 kg/L, complete combustion
PUMP_HEAD_M = 40.0               # assumption: typical total dynamic head, replace with the farmer's own
PUMP_EFFICIENCY = 0.35           # assumption: typical wire-to-water efficiency of an older farm pumpset


def heavy_rain_share(hist, season, duration, sow=None):
    """Share of past seasons with at least one 'very heavy rain' day (>= 115.6 mm) inside the crop cycle."""
    m, dd = sow_md(season, sow)
    hits = total = 0
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, dd))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        total += 1
        hits += any(r >= VERY_HEAVY_RAIN_MM for r in hist["rain"][i0:i0 + duration])
    return (hits / total if total else 0.0), hits, total


def climate_trend(hist, season, duration, recent_years=10, sow=None):
    """Last `recent_years` seasons vs the earlier ones: change in season rain, water demand (ET0) and dry spells."""
    m, dd = sow_md(season, sow)
    rows = []
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, dd))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        rows.append((y, sum(hist["rain"][i0:i0 + duration]), sum(hist["et0"][i0:i0 + duration]),
                     longest_dry_spell(hist, date(y, m, dd), duration)))
    if len(rows) < recent_years + 8:
        return None
    old, new = rows[:-recent_years], rows[-recent_years:]
    mean = lambda xs: sum(xs) / len(xs)
    rain_old, rain_new = mean([r[1] for r in old]), mean([r[1] for r in new])
    et_old, et_new = mean([r[2] for r in old]), mean([r[2] for r in new])
    return {"rain_change_pct": round(100 * (rain_new - rain_old) / rain_old) if rain_old else 0,
            "et0_change_pct": round(100 * (et_new - et_old) / et_old),
            "dry_spell_old": round(mean([r[3] for r in old])), "dry_spell_new": round(mean([r[3] for r in new])),
            "recent_years": recent_years, "years": f"{rows[-recent_years][0]}-{rows[-1][0]}"}


def compare_practice(lat, lon, crop_id, season, duration, taw_per_m=130, water="all_year", acres=1.0,
                     head_m=PUMP_HEAD_M, pump_eff=PUMP_EFFICIENCY, efficient_eff=0.90, calendar_depth=60, hist=None, sow=None):
    """Median over past seasons, per season for `acres`, against a stated baseline.

    baseline        package-of-practice calendar: the crop's usual number of flood irrigations (crop table
                    `irrigations_needed`), evenly spaced, `calendar_depth` mm gross each, no rain adjustment
    sched_flood     lever 1: irrigate when the soil needs it, using flood irrigation at the same 60% efficiency
    sched_efficient lever 2: lever 1 plus an efficient method (drip / micro-sprinkler, `efficient_eff`)
    The saving only means something if yield holds, so relative yields are returned for every arm.
    """
    from krishi.crop_table import load_crops

    hist = hist or fetch_history(round(lat, 2), round(lon, 2))
    rows_c = load_crops()
    n_irr = int(round(float(rows_c[rows_c.crop_id == crop_id].irrigations_needed.iloc[0])))
    n_irr = min(n_irr, 30)
    m, dd = sow_md(season, sow)
    arms = {"baseline": [], "sched_flood": [], "sched_efficient": []}
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        sow = date(y, m, dd)
        a = simulate(hist, crop_id, sow, duration, taw_per_m, "calendar", water, depth=calendar_depth, n_irr=n_irr)
        b = simulate(hist, crop_id, sow, duration, taw_per_m, "scheduled", water, eff=FLOOD_EFFICIENCY)
        c = simulate(hist, crop_id, sow, duration, taw_per_m, "scheduled", water, eff=efficient_eff)
        if a and b and c:
            arms["baseline"].append(a); arms["sched_flood"].append(b); arms["sched_efficient"].append(c)
    if not arms["baseline"]:
        return None
    med = lambda rows, k: _pct([r[k] for r in rows], 0.5)
    m3_per_mm = 4.047 * acres          # 1 mm over 1 acre = 4.047 m3
    out = {"n_irrigations_practice": n_irr}
    for name, rows in arms.items():
        mm = med(rows, "irrigation_mm")
        vol = mm * m3_per_mm
        kwh = pump_energy_kwh(vol, head_m, pump_eff)
        out[name] = {"mm": mm, "m3": vol, "kwh": kwh, "co2_kg": kwh * GRID_KG_CO2_PER_KWH,
                     "rel_yield": med(rows, "rel_yield"), "irrigations": med(rows, "n_irrig")}
    base = out["baseline"]
    for name in ("sched_flood", "sched_efficient"):
        arm = out[name]
        arm["saved_m3"] = base["m3"] - arm["m3"]
        arm["saved_pct"] = 100 * arm["saved_m3"] / base["m3"] if base["m3"] else 0.0
        arm["saved_kwh"] = base["kwh"] - arm["kwh"]
        arm["saved_co2_kg"] = base["co2_kg"] - arm["co2_kg"]
        arm["yield_change_pct"] = 100 * (arm["rel_yield"] - base["rel_yield"]) / base["rel_yield"] if base["rel_yield"] else 0.0
        arm["m3_per_rel_yield"] = arm["m3"] / arm["rel_yield"] if arm["rel_yield"] else None
    base["m3_per_rel_yield"] = base["m3"] / base["rel_yield"] if base["rel_yield"] else None
    # spread across seasons: per-season percentage saving against that season's baseline
    for name in ("sched_flood", "sched_efficient"):
        per_year = []
        for a, b in zip(arms["baseline"], arms[name]):
            if a["irrigation_mm"] > 0:
                per_year.append(100 * (a["irrigation_mm"] - b["irrigation_mm"]) / a["irrigation_mm"])
        out[name]["saved_pct_p10"] = _pct(per_year, 0.10) if per_year else None
        out[name]["saved_pct_p90"] = _pct(per_year, 0.90) if per_year else None
    out["n_years"] = len(arms["baseline"])
    return out


# ---------------------------------------------------------------- series for charts
def season_series(lat, lon, crop_id, season, duration, taw_per_m=130, water_level="rain", hist=None, sow=None):
    """Per past season: relative yield, irrigation (gross mm) and rain, for charts. Oldest first."""
    hist = hist or fetch_history(round(lat, 2), round(lon, 2))
    m, dd = sow_md(season, sow)
    policy = "rainfed" if water_level == "rain" else "scheduled"
    out = []
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        res = simulate(hist, crop_id, date(y, m, dd), duration, taw_per_m, policy, water_level)
        if res:
            out.append({"year": y, "rel_yield": res["rel_yield"], "irrigation_mm": res["irrigation_mm"],
                        "rain_mm": res["rain_mm"], "n_irrig": res["n_irrig"]})
    return out


def season_rain_stats(hist, season, duration=120, sow=None):
    """Dry-year / usual / wet-year rainfall (10th, 50th, 90th percentile) over a `duration`-day season window."""
    m, dd = sow_md(season, sow)
    tot = []
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, dd))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        tot.append(sum(hist["rain"][i0:i0 + duration]))
    if not tot:
        return None
    return {"p10": _pct(tot, 0.10), "p50": _pct(tot, 0.50), "p90": _pct(tot, 0.90), "n": len(tot)}


# ---------------------------------------------------------------- live schedule from the farmer's own sowing date
def weather_window(lat, lon, start, end, timeout=30):
    """Daily ET0 and rain for start..end: ERA5 archive up to 6 days ago, the forecast service for the recent days and the
    next ~15 days. Returns {date: (et0, rain, kind)} with kind 'observed' or 'forecast'. Days beyond the forecast are absent."""
    today = date.today()
    out = {}
    arch_end = min(end, today - timedelta(days=6))
    if start <= arch_end:
        r = requests.get(ARCHIVE, params={"latitude": lat, "longitude": lon, "start_date": start.isoformat(),
                                          "end_date": arch_end.isoformat(),
                                          "daily": "et0_fao_evapotranspiration,precipitation_sum", "timezone": "auto"},
                         timeout=timeout)
        r.raise_for_status()
        d = r.json()["daily"]
        for t, e, p in zip(d["time"], d["et0_fao_evapotranspiration"], d["precipitation_sum"]):
            out[date.fromisoformat(t)] = (e or 0.0, p or 0.0, "observed")
    if end > arch_end:
        r = requests.get(FORECAST, params={"latitude": lat, "longitude": lon, "past_days": 92, "forecast_days": 16,
                                           "daily": "et0_fao_evapotranspiration,precipitation_sum", "timezone": "auto"},
                         timeout=timeout)
        r.raise_for_status()
        d = r.json()["daily"]
        for t, e, p in zip(d["time"], d["et0_fao_evapotranspiration"], d["precipitation_sum"]):
            day = date.fromisoformat(t)
            if day > arch_end and start <= day <= end and day not in out:
                out[day] = (e or 0.0, p or 0.0, "observed" if day <= today else "forecast")
    return out


def _typical_year(hist, m, d, duration):
    """The past year whose rain over this crop window is closest to the median: a realistic day-by-day 'normal' season."""
    totals = []
    for y in range(hist["dates"][0].year, hist["dates"][-1].year):
        i0 = hist["index"].get(date(y, m, d))
        if i0 is None or i0 + duration >= len(hist["dates"]):
            continue
        totals.append((sum(hist["rain"][i0:i0 + duration]), y))
    if not totals:
        return None
    totals.sort()
    return totals[len(totals) // 2][1]


def live_schedule(lat, lon, crop_id, sow_date, duration, taw_per_m=130, water_level="till_mar", eff=0.9,
                  actual_events=None, today=None):
    """Watering schedule for one crop from the farmer's sowing date.

    Weather used: observed (ERA5) up to a few days ago, the 15-day forecast, then a 'typical' past year for the rest.
    actual_events = {date: net_mm} the farmer really watered (days up to today use these instead of the model's).
    Returns dict with events [{date, gross_mm, net_mm, status, basis}], totals, and the soil-water state.
    """
    today = today or date.today()
    hist = fetch_history(round(lat, 2), round(lon, 2))
    start = sow_date
    n = duration + 2
    days = [start + timedelta(days=i) for i in range(n)]
    try:
        wx = weather_window(lat, lon, start, days[-1])
    except Exception:
        wx = {}
    ty = _typical_year(hist, start.month, start.day, duration)
    et0, rain, basis = [], [], []
    for day in days:
        if day in wx:
            e, p, kind = wx[day]
            et0.append(e); rain.append(p); basis.append(kind)
            continue
        got = None
        if ty is not None:
            try:
                yy = ty + (day.year - start.year)       # keep the year offset when the season crosses New Year
                i = hist["index"].get(date(yy, day.month, day.day))
                if i is None and day.month == 2 and day.day == 29:
                    i = hist["index"].get(date(yy, 2, 28))
                if i is not None:
                    got = (hist["et0"][i], hist["rain"][i])
            except ValueError:
                got = None
        e, p = got if got else (4.0, 0.0)
        et0.append(e); rain.append(p); basis.append("typical")
    custom = {"dates": days, "et0": et0, "rain": rain, "tmax": [30.0] * n, "tmean": [25.0] * n,
              "index": {d: i for i, d in enumerate(days)}}
    res = simulate(custom, crop_id, start, duration, taw_per_m, "scheduled", water_level, eff,
                   override_until=today if actual_events is not None else None, override_events=actual_events)
    if not res:
        return None
    events = []
    for d, gross in res["events"]:
        events.append({"date": d, "gross_mm": gross, "net_mm": gross * eff,
                       "status": "done" if d < today else "today" if d == today else "upcoming",
                       "basis": basis[custom["index"][d]]})
    return {"events": events, "n": len(events), "gross_mm": res["irrigation_mm"], "rel_yield": res["rel_yield"],
            "start": start, "end": start + timedelta(days=duration), "typical_year": ty,
            "days_of_forecast": sum(1 for b in basis if b == "forecast"), "weather_ok": bool(wx)}
