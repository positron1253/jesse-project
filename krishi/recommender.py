"""Profit-and-risk crop recommender + "how much to grow" allocation (panel's frozen v1 spec).

Ranking replaces the old Kaggle RandomForest:
  feasible (season, water) -> fit (season temperature, soil pH) -> yield range (water-adjusted)
  -> price (harvest-month mandi range, MSP x procurement floor, glut haircut)
  -> profit normal range & worst case -> score S = pi_mid - lambda * (pi_mid - pi_bad)
"""

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from krishi.crop_table import crops_for

# Irrigations a plot can supply, by season. The panel's v1 spec used one number per water level, but a well that
# lasts "till March" covers the whole Rabi season (Nov-Mar), so the allowance depends on the season:
#   Rabi:   till_dec = 3 (dies before wheat/vegetables finish; chana at 2 still fits), till_mar = whole season
#   Kharif: monsoon does most of the work, so even short-lived water is plentiful
#   Zaid:   (Mar-Jun) a well that dies in March/December gives little or nothing
WATER_CAPACITY = {
    "Rabi":   {"rain": 0, "till_dec": 3, "till_mar": 15, "all_year": 99},
    "Kharif": {"rain": 0, "till_dec": 6, "till_mar": 15, "all_year": 99},
    "Zaid":   {"rain": 0, "till_dec": 0, "till_mar": 2, "all_year": 99},
}
LAMBDA = {"low": 0.75, "medium": 0.5, "high": 0.25}  # risk appetite -> downside weight
GLUT_MIN_PLANS = 10
FARMGATE = 0.92          # mandi modal price -> what the farmer receives after commission, transport, handling
EST_SCORE_DISCOUNT = 0.5  # ranking discount for crops whose cost/price are estimates
COST_EST_MARKUP = 1.15   # cost figures marked `est` tend to understate picking / hired labour


@dataclass
class Plot:
    name: str
    acres: float
    water: Literal["rain", "till_dec", "till_mar", "all_year"]


@dataclass
class NearbySignals:
    """What's happening within ~50 km: planned acreage from other farmers and open vendor demand."""
    n_plans: dict = field(default_factory=dict)        # crop_id -> number of saved plans
    planned_acres: dict = field(default_factory=dict)  # crop_id -> acres
    vendor_q: dict = field(default_factory=dict)       # crop_id -> open demand, quintal
    buyers: dict = field(default_factory=dict)         # crop_id -> list of poll dicts (+distance)


@dataclass
class CropOption:
    crop_id: str
    plot: str
    fit_dots: int
    coverage: str
    yield_q_acre: tuple
    price_q: float
    msp: float | None
    profit_normal: tuple
    profit_worst: float
    profit_mid: float
    score: float
    risk: str
    reasons: list
    row: dict
    glut_note: str | None = None
    est: bool = False


def _trap(x, a, b, c, d):
    """Trapezoid membership: 0 outside [a, d], 1 inside [b, c]."""
    if any(pd.isna(v) for v in (a, b, c, d)):
        return 1.0
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    return (x - a) / (b - a) if x < b else (d - x) / (d - c)


def _num(v, default=0.0):
    return default if v is None or pd.isna(v) else float(v)


def score_crop(row, plot, temp, ph, nearby, risk_appetite="medium"):
    """Return CropOption or None if not feasible on this plot."""
    season_ok_rainfed = row["_season"] in str(row["rainfed_ok_seasons"]).split("|")
    need = _num(row["irrigations_needed"], 0)
    cap = WATER_CAPACITY[row["_season"]][plot.water]
    if not (need <= cap or season_ok_rainfed):
        return None

    fit = min(_trap(temp, row["tmin"], row["topt_lo"], row["topt_hi"], row["tmax"]),
              _trap(ph, _num(row["ph_lo"], 5.5) - 1.5, row["ph_lo"], row["ph_hi"], _num(row["ph_hi"], 8) + 1.5))
    if fit < 0.3:
        return None
    est = bool(_num(row.get("cost_est")) or _num(row.get("price_est")))
    dots = 4 if fit >= .85 else 3 if fit >= .65 else 2 if fit >= .45 else 1
    dots = max(1, dots - (1 if est else 0))
    if row["coverage"] == "none":
        dots = min(dots, 2)

    # Normally-irrigated crop on a plot with limited water: still feasible (rain-fed season) but lower yield
    k_w = 0.75 if (need > cap and season_ok_rainfed and need > 0) else 1.0
    y_lo, y_hi = _num(row["yield_q_acre_lo"]) * k_w, _num(row["yield_q_acre_hi"]) * k_w
    y_mid = (y_lo + y_hi) / 2

    crop = row["crop_id"]
    n_plans = nearby.n_plans.get(crop, 0)
    planned = nearby.planned_acres.get(crop, 0.0)
    vendor_q = nearby.vendor_q.get(crop, 0.0)
    perishable = bool(_num(row["perishable"]))
    g, glut_note = 0.0, None
    if n_plans >= GLUT_MIN_PLANS:
        absorb = _num(row["cluster_absorb_acres"], 500) + (vendor_q / y_mid if y_mid else 0)
        beta = 0.3 if perishable else 0.1
        g = min(0.5, max(0.0, beta * max(0.0, planned / absorb - 1)))
    if n_plans:
        glut_note = f"{n_plans} farmers near you plan {planned:g} acres"

    msp = _num(row["msp_rs_q"], 0) or None
    floor = (msp or 0) * _num(row["procurement"], 0)
    p_lo, p_mid, p_hi = (_num(row[c]) * FARMGATE for c in ("price_q_lo", "price_q_mid", "price_q_hi"))
    P_mid = max(p_mid * (1 - g), floor)
    P_bad = max(p_lo * (1 - g), floor)
    loss = _num(row["loss_frac"], 0.05)
    cost = _num(row["cost_rs_acre"]) * (COST_EST_MARKUP if _num(row.get("cost_est")) else 1.0)

    pi_mid = y_mid * P_mid * (1 - loss) - cost
    pi_bad = y_lo * P_bad * (1 - loss) - cost
    normal = (y_lo * P_mid * (1 - loss) - cost, y_hi * P_mid * (1 - loss) - cost)
    lam = LAMBDA.get(risk_appetite, 0.5)
    S = pi_mid - lam * (pi_mid - pi_bad)

    reasons = []
    spread = (p_hi - p_lo) / p_mid if p_mid else 0
    if pi_bad < -0.25 * cost or (_num(row["glut_prone"]) and pi_bad < 0):
        risk = "high"
        reasons.append("price_crash" if _num(row["glut_prone"]) else "bad_year_loss")
    elif pi_bad < 0 or spread > 0.6:
        risk = "medium"
        reasons.append("bad_year_loss" if pi_bad < 0 else "price_swings")
    else:
        risk = "low"
        reasons.append("steady")
    if floor >= 0.8 * p_mid and risk == "high":
        risk = "medium"
    if est:
        # Costs/prices are rough estimates for this crop: never call it low risk, and rank it below
        # crops backed by measured (CACP/Agmarknet) numbers.
        if risk == "low":
            risk = "medium"
        reasons.append("rough_numbers")
        if S > 0:
            S *= EST_SCORE_DISCOUNT
    if floor > 0:
        reasons.append("msp_support")
    if g > 0:
        reasons.insert(0, "too_many_planting")
    if k_w < 1:
        reasons.append("less_water_lower_yield")
    if row["coverage"] == "none":
        reasons.append("new_here")

    return CropOption(
        crop_id=crop, plot=plot.name, fit_dots=dots, coverage=row["coverage"],
        yield_q_acre=(round(y_lo, 1), round(y_hi, 1)), price_q=round(P_mid), msp=msp,
        profit_normal=(round(normal[0], -3), round(normal[1], -3)), profit_worst=round(pi_bad, -3),
        profit_mid=round(pi_mid, -3), score=S, risk=risk, reasons=reasons, row=dict(row),
        glut_note=glut_note, est=est,
    )


def rank_crops(state, season, plot, climate, ph, nearby=None, risk_appetite="medium",
               district=None, top_n=3, include_perennial=False):
    """Ranked CropOptions for one plot. `season` is 'Kharif' | 'Rabi' | 'Zaid'."""
    nearby = nearby or NearbySignals()
    table = crops_for(state, season, district)
    options = []
    for _, row in table.iterrows():
        if not include_perennial and _num(row.get("duration_days"), 0) > 300:
            continue
        row = row.copy()
        row["_season"] = season
        opt = score_crop(row, plot, climate["temperature"], ph, nearby, risk_appetite)
        if opt:
            options.append(opt)
    options.sort(key=lambda o: o.score, reverse=True)
    # A crop with no local/state data can never be #1
    if options and options[0].coverage == "none":
        local = next((o for o in options if o.coverage != "none"), None)
        if local:
            options.remove(local)
            options.insert(0, local)
    return options[:top_n] if top_n else options


@dataclass
class PlanRow:
    plot: str
    crop_id: str
    acres: float
    yield_q: tuple
    profit_normal: tuple
    profit_worst: float
    contracted: bool = False
    note: str | None = None


@dataclass
class FarmPlan:
    rows: list
    unused: dict
    warnings: list

    @property
    def total_normal(self):
        return (sum(r.profit_normal[0] for r in self.rows), sum(r.profit_normal[1] for r in self.rows))

    @property
    def total_worst(self):
        return sum(r.profit_worst for r in self.rows)


def cap_share(opt):
    if _num(opt.row.get("glut_prone")) or _num(opt.row.get("perishable")):
        return 0.25  # thin market for fresh produce, labour heavy: start small
    if _num(opt.row.get("procurement")) >= 0.8:
        return 1.0
    return 0.6


def crop_cap_acres(opt, farm_acres, nearby):
    cap = cap_share(opt) * farm_acres
    if opt.coverage == "none":
        cap = min(cap, 0.5)
    if _num(opt.row.get("glut_prone")) and nearby.n_plans.get(opt.crop_id, 0) >= GLUT_MIN_PLANS:
        quota = max(0.0, _num(opt.row.get("cluster_absorb_acres"), 0) - nearby.planned_acres.get(opt.crop_id, 0))
        cap = min(cap, quota)
    return cap


def _row_for(opt, acres, contracted=False, note=None):
    return PlanRow(
        plot=opt.plot, crop_id=opt.crop_id, acres=acres,
        yield_q=(round(opt.yield_q_acre[0] * acres, 1), round(opt.yield_q_acre[1] * acres, 1)),
        profit_normal=(opt.profit_normal[0] * acres, opt.profit_normal[1] * acres),
        profit_worst=opt.profit_worst * acres, contracted=contracted, note=note,
    )


def allocate(plots, options, contracts=None, nearby=None, chosen=None):
    """Split each plot's acres between crops.

    options:   {plot_name: [CropOption, ...]} ranked
    contracts: [{"crop_id", "quantity_q"}] accepted vendor commitments (allocated first)
    chosen:    optional set of crop_ids the farmer ticked; others are ignored
    """
    nearby = nearby or NearbySignals()
    farm_acres = sum(p.acres for p in plots)
    remaining = {p.name: p.acres for p in plots}
    used = {}  # crop_id -> acres across farm
    rows, warnings = [], []

    def step_for(plot_acres):
        return 0.25 if plot_acres < 1 else 0.5

    # A1: contracts first, on the plot where that crop scores best
    for c in contracts or []:
        best = None
        for p in plots:
            for o in options.get(p.name, []):
                if o.crop_id == c["crop_id"] and (best is None or o.score > best.score):
                    best = o
        if not best:
            continue
        acres = min(remaining[best.plot], c["quantity_q"] / max(best.yield_q_acre[0], 0.1))
        acres = round(acres * 4) / 4
        if acres > 0:
            rows.append(_row_for(best, acres, contracted=True, note="contract"))
            remaining[best.plot] -= acres
            used[best.crop_id] = used.get(best.crop_id, 0) + acres

    # A2/A3: greedy fill by score with caps, max 3 crops per plot
    for p in plots:
        opts = [o for o in options.get(p.name, []) if o.score > 0 and (not chosen or o.crop_id in chosen)]
        step = step_for(p.acres)
        crops_here = {r.crop_id for r in rows if r.plot == p.name}
        alloc = {}
        progress = True
        while remaining[p.name] >= step - 1e-9 and progress:
            progress = False
            for o in opts:
                if o.crop_id not in alloc and o.crop_id not in crops_here and len(crops_here | set(alloc)) >= 3:
                    continue
                cap = crop_cap_acres(o, farm_acres, nearby)
                if used.get(o.crop_id, 0) + step <= cap + 1e-9:
                    alloc[o.crop_id] = alloc.get(o.crop_id, 0) + step
                    used[o.crop_id] = used.get(o.crop_id, 0) + step
                    remaining[p.name] -= step
                    progress = True
                    break
        for o in opts:
            if o.crop_id in alloc:
                rows.append(_row_for(o, alloc[o.crop_id]))

    for crop_id, acres in used.items():
        if farm_acres and acres / farm_acres > 0.7 and farm_acres > 1:
            warnings.append(("one_crop", crop_id, acres))
        demand = nearby.vendor_q.get(crop_id, 0)
        produce = sum(r.yield_q[1] for r in rows if r.crop_id == crop_id)
        if demand and produce > demand * 1.5 and any(not r.contracted for r in rows if r.crop_id == crop_id):
            warnings.append(("over_demand", crop_id, demand))
    unused = {k: round(v, 2) for k, v in remaining.items() if v > 1e-9}
    return FarmPlan(rows=rows, unused=unused, warnings=warnings)
