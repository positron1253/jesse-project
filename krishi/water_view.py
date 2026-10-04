"""Water and energy tab: forecast and irrigation advice, 30-season climate risk, schedule vs usual practice,
pump sizing and solar payback, and the farmer's own energy log. Works on its own (no saved plan needed)."""

from datetime import date

import pandas as pd
import streamlit as st

from krishi import crop_model as cm
from krishi import crop_table, energylog, location_ui, water
from krishi import pump as pump_mod
from krishi.i18n import current_lang, inr, rupees, t
from krishi.plan_view import SEASON_LABEL, current_season


def _name(crop_id):
    try:
        return crop_table.crop_names(crop_id)[current_lang()]
    except Exception:
        return crop_id.replace("_", " ").title()


@st.cache_data(ttl=3600, show_spinner=False)
def _series(lat, lon, crop, season, duration, taw, level):
    return water.season_series(lat, lon, crop, season, duration, taw, level)


@st.cache_data(ttl=3600, show_spinner=False)
def _profile(lat, lon, crop, season, duration, taw, level):
    return water.climate_profile(lat, lon, crop, season, duration, taw, level)


@st.cache_data(ttl=3600, show_spinner=False)
def _compare(lat, lon, crop, season, duration, taw, level, acres, head, eff):
    return water.compare_practice(lat, lon, crop, season, duration, taw, level, acres=acres, head_m=head, pump_eff=eff)


@st.cache_data(ttl=900, show_spinner=False)
def _forecast(lat, lon):
    return water.fetch_forecast(lat, lon, 7)


def _inputs(user):
    """Shared selector block. Returns a dict, or None if the farm location is missing."""
    location_ui.render_location(user)
    farm = st.session_state.get("farm") or {}
    lat = farm.get("lat") or user.get("latitude")
    lon = farm.get("lon") or user.get("longitude")
    state = farm.get("state") or user.get("state") or "Maharashtra"
    if lat is None:
        st.info(t("loc.need"))
        return None
    with st.container(border=True):
        c1, c2 = st.columns(2)
        season = c1.pills(t("p2.season"), list(SEASON_LABEL), format_func=lambda s: t(f"s.{s}"),
                          default=current_season(), key="wat_season") or current_season()
        table = crop_table.crops_for(state, season)
        crop_ids = [c for c in table.crop_id if int(table[table.crop_id == c].duration_days.iloc[0]) <= 300]
        default_crop = "chana" if "chana" in crop_ids else crop_ids[0]
        crop = c2.selectbox(t("wat.crop"), crop_ids, index=crop_ids.index(default_crop), format_func=_name, key="wat_crop")
        duration = int(table[table.crop_id == crop].duration_days.iloc[0])
        d1, d2, d3 = st.columns(3)
        soils = [None] + list(cm.SOIL_TYPES)
        soil = d1.selectbox(t("p1.soil"), soils, format_func=lambda s: t("soil.unknown") if s is None else s,
                            index=soils.index(farm.get("soil")) if farm.get("soil") in soils else 0, key="wat_soil")
        keys = ["rain", "till_dec", "till_mar", "all_year"]
        level = d2.pills(t("p1.water"), keys, format_func=lambda k: t(f"w.{k}"),
                         default=farm.get("water") if farm.get("water") in keys else "till_mar", key="wat_level") or "till_mar"
        acres = d3.number_input(t("wat.acres"), min_value=0.5, max_value=100.0, value=2.0, step=0.5, key="wat_acres")
    return {"lat": round(lat, 2), "lon": round(lon, 2), "season": season, "crop": crop, "duration": duration,
            "level": level, "acres": float(acres), "taw": water.SOIL_TAW[water.SOIL_OF_TYPE.get(soil, "unknown")]}


def tab_next(s):
    try:
        fc = _forecast(s["lat"], s["lon"])
    except Exception:
        st.warning(t("p2.climate_fail"))
        return
    d_since = st.number_input(t("irrig.days"), min_value=0, max_value=400, value=0, key="wat_days")
    last = st.number_input(t("irrig.last"), min_value=0, max_value=60, value=0, key="wat_last")
    adv = water.next_irrigation_advice(s["lat"], s["lon"], s["crop"], int(d_since), s["duration"], s["taw"],
                                       last_irrigation_days_ago=int(last) or None)
    if s["level"] == "rain":
        st.info(t("wat.rain_only"))
    elif adv["action"] == "irrigate":
        st.success(t("irrig.irrigate", when=adv["when"].isoformat(), mm=adv["net_mm"]))
    else:
        st.info(t("irrig.wait"))
    st.bar_chart(pd.DataFrame({t("wat.rain_col"): [d["rain"] for d in fc], t("wat.use_col"): [p["etc_mm"] for p in adv["plan"]]},
                              index=[d["date"].strftime("%d %b") for d in fc]))
    st.caption(t("irrig.rain", p=max(d["p_rain"] for d in fc)))
    st.dataframe(pd.DataFrame([{t("wat.date"): d["date"].isoformat(), t("wat.rain_col"): d["rain"],
                                t("wat.chance"): f"{d['p_rain']}%", t("wat.et0"): round(d["et0"], 1)} for d in fc]),
                 hide_index=True, use_container_width=True)


def tab_past(s):
    with st.spinner(t("village.wait")):
        prof = _profile(s["lat"], s["lon"], s["crop"], s["season"], s["duration"], s["taw"], s["level"])
        series = _series(s["lat"], s["lon"], s["crop"], s["season"], s["duration"], s["taw"], s["level"])
        hist = water.fetch_history(s["lat"], s["lon"])
    if not prof:
        st.warning(t("p2.climate_fail"))
        return
    m = st.columns(4)
    m[0].metric(t("wat.bad_year"), f"{prof['rel_p10'] * 100:.0f}%")
    m[1].metric(t("wat.usual_year"), f"{prof['rel_p50'] * 100:.0f}%")
    m[2].metric(t("wat.poor_share"), f"{prof['p_poor'] * 100:.0f}%")
    m[3].metric(t("wat.dry_spell"), f"{prof['dry_spell_p90']:.0f} " + t("wat.days"))
    st.caption(t("wat.rel_note", n=prof["n_years"]))
    df = pd.DataFrame(series).set_index("year")
    st.markdown(f"**{t('wat.chart_yield')}**")
    st.bar_chart(df[["rel_yield"]].rename(columns={"rel_yield": t("wat.rel_col")}))
    st.markdown(f"**{t('wat.chart_rain')}**")
    st.line_chart(df[["rain_mm"]].rename(columns={"rain_mm": t("wat.season_rain")}))
    share, hits, total = water.heavy_rain_share(hist, s["season"], s["duration"])
    if hits:
        st.warning(t("card.heavy_rain", n=hits, total=total))
    trend = water.climate_trend(hist, s["season"], s["duration"])
    if trend:
        st.info("📈 " + t("p2.trend", recent=trend["recent_years"], years=trend["years"],
                          rain=trend["rain_change_pct"], et0=trend["et0_change_pct"]))
    if s["level"] != "rain":
        st.caption(t("wat.irrig_need", mm=round(prof["irrigation_mm_p50"]), p90=round(prof["irrigation_mm_p90"]),
                     n=round(prof["irrigations_p50"])))


def tab_compare(s):
    e1, e2 = st.columns(2)
    head = e1.number_input(t("pump.head"), min_value=5.0, max_value=200.0, value=float(water.PUMP_HEAD_M), step=5.0, key="wat_head")
    eff = e2.slider(t("wat.pump_eff"), 15, 70, int(water.PUMP_EFFICIENCY * 100), key="wat_eff") / 100
    if s["level"] == "rain":
        st.info(t("wat.rain_only"))
        return
    with st.spinner(t("village.wait")):
        cmp = _compare(s["lat"], s["lon"], s["crop"], s["season"], s["duration"], s["taw"], s["level"],
                       s["acres"], float(head), float(eff))
    if not cmp:
        st.warning(t("p2.climate_fail"))
        return
    b, f, e = cmp["baseline"], cmp["sched_flood"], cmp["sched_efficient"]
    st.caption(t("wat.cmp_note", n=cmp["n_years"], k=cmp["n_irrigations_practice"]))
    cols = st.columns(3)
    for col, title, a, is_base in ((cols[0], t("wat.arm_base"), b, True), (cols[1], t("wat.arm_flood"), f, False),
                                   (cols[2], t("wat.arm_eff"), e, False)):
        with col:
            st.markdown(f"**{title}**")
            st.metric(t("wat.water"), f"{rupees(a['m3'])} m³", None if is_base else f"{-a['saved_pct']:+.0f}%",
                      delta_color="inverse")
            st.metric(t("wat.energy"), f"{rupees(a['kwh'])} kWh")
            st.metric("CO₂", f"{rupees(a['co2_kg'])} kg")
            st.metric(t("wat.yield"), f"{a['rel_yield'] * 100:.0f}%")
    if e["saved_pct"] < 0 or f["saved_pct"] < 0:
        st.info(t("wat.more_water_note"))
    st.caption(t("plan.water_note", n=cmp["n_years"], head=int(head), eff=int(eff * 100)))


def tab_pump(s):
    if s["level"] == "rain":
        st.info(t("wat.rain_only"))
        return
    q1, q2, q3 = st.columns(3)
    hours = q1.number_input(t("pump.hours"), min_value=2.0, max_value=24.0, value=8.0, step=1.0, key="wat_hours",
                            help=t("pump.hours_help"))
    head = q2.number_input(t("pump.head"), min_value=5.0, max_value=200.0, value=float(water.PUMP_HEAD_M), step=5.0, key="wat_head2")
    drip = q3.checkbox(t("pump.drip"), value=False, key="wat_drip")
    peak = pump_mod.peak_demand_mm_day(s["lat"], s["lon"], s["crop"], s["season"], s["duration"])
    sz = pump_mod.size_pump(s["acres"], peak, hours, head, water.PUMP_EFFICIENCY, 0.9 if drip else 0.6)
    st.success(t("pump.result", acres=f"{s['acres']:g}", peak=f"{peak:.1f}", m3=rupees(sz["daily_m3"]), hp=sz["hp"], kwp=sz["array_kwp"]))
    st.caption(t("pump.assume"))
    cur = st.number_input(t("pump.current_hp"), min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="wat_cur")
    if cur and cur > sz["hp"]:
        st.warning(t("pump.oversized", cur=f"{cur:g}", hp=sz["hp"]))
    st.markdown(f"**{t('pump.payback_title')}**")
    st.caption(t("pump.payback_help"))
    src = st.radio(t("pump.source"), ["grid", "diesel"], format_func=lambda k: t(f"pump.src_{k}"), horizontal=True, key="wat_src")
    price = st.number_input(t("pump.tariff") if src == "grid" else t("pump.diesel_price"), min_value=0.0, value=0.0, step=1.0, key="wat_price")
    cost = st.number_input(t("pump.cost"), min_value=0.0, value=0.0, step=10000.0, key="wat_cost")
    if cost > 0 and price > 0:
        cmp = _compare(s["lat"], s["lon"], s["crop"], s["season"], s["duration"], s["taw"], s["level"], s["acres"],
                       float(head), water.PUMP_EFFICIENCY)
        kwh = cmp["sched_efficient" if drip else "sched_flood"]["kwh"]
        pb = pump_mod.solar_payback(cost, kwh, src, price if src == "grid" else None, price if src == "diesel" else None)
        if pb["payback_years"]:
            st.success(t("pump.payback_result", own=inr(pb["farmer_share_rs"]), sub=inr(pb["subsidy_rs"]),
                         save=inr(pb["annual_saving_rs"]), yrs=f"{pb['payback_years']:.1f}", co2=rupees(pb["annual_co2_kg"])))
    else:
        st.caption(t("wat.enter_prices"))


def tab_log(s, user):
    st.caption(t("log.sub"))
    with st.form("energy_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        day = f1.date_input(t("wat.date"), value=date.today())
        source = f2.radio(t("pump.source"), ["grid", "diesel"], format_func=lambda k: t(f"pump.src_{k}"), horizontal=True)
        hrs = f3.number_input(t("log.hours"), min_value=0.0, max_value=24.0, value=2.0, step=0.5)
        g1, g2, g3 = st.columns(3)
        hp = g1.number_input(t("log.hp"), min_value=0.0, max_value=50.0, value=5.0, step=0.5)
        litres = g2.number_input(t("log.litres"), min_value=0.0, max_value=500.0, value=0.0, step=1.0)
        note = g3.text_input(t("log.note"))
        if st.form_submit_button(t("log.add"), type="primary"):
            energylog.add(user["id"], day, s["crop"], source, hrs, pump_kw=hp * 0.746, litres=litres, acres=s["acres"], note=note)
            st.success(t("log.saved"))
    rows = energylog.entries(user["id"])
    if not rows:
        st.info(t("log.none"))
        return
    tot = energylog.totals(rows)
    m = st.columns(4)
    m[0].metric(t("log.total_hours"), f"{tot['hours']:.1f}")
    m[1].metric(t("wat.energy"), f"{rupees(tot['kwh'])} kWh")
    m[2].metric(t("log.total_litres"), f"{tot['litres']:.0f} L")
    m[3].metric("CO₂", f"{rupees(tot['co2_kg'])} kg")
    st.bar_chart(pd.DataFrame([{"month": k, t("wat.energy"): v["kwh"]} for k, v in sorted(tot["by_month"].items())]).set_index("month"))
    if s["level"] != "rain":
        cmp = _compare(s["lat"], s["lon"], s["crop"], s["season"], s["duration"], s["taw"], s["level"], s["acres"],
                       float(water.PUMP_HEAD_M), water.PUMP_EFFICIENCY)
        if cmp:
            st.info(t("log.vs_plan", acres=f"{s['acres']:g}", crop=_name(s["crop"]), base=rupees(cmp["baseline"]["kwh"]),
                      sched=rupees(cmp["sched_flood"]["kwh"]), mine=rupees(tot["kwh"])))
    st.dataframe(pd.DataFrame([{t("wat.date"): e["date"], t("tbl.crop"): _name(e["crop_id"]) if e.get("crop_id") else "",
                                t("log.hours"): e["hours"], "kWh": round(e["kwh"], 1), "L": round(e["litres"], 1),
                                "CO₂ kg": round(e["co2_kg"], 1), t("log.note"): e.get("note", "")} for e in reversed(rows)]),
                 hide_index=True, use_container_width=True)
    if st.button(t("log.delete_last"), key="log_del"):
        energylog.delete(user["id"], rows[-1]["id"])
        st.rerun()


def render(user):
    st.caption(t("wat.sub"))
    s = _inputs(user)
    if not s:
        return
    tabs = st.tabs([t("wat.tab_next"), t("wat.tab_past"), t("wat.tab_compare"), t("wat.tab_pump"), t("wat.tab_log")])
    with tabs[0]:
        tab_next(s)
    with tabs[1]:
        tab_past(s)
    with tabs[2]:
        tab_compare(s)
    with tabs[3]:
        tab_pump(s)
    with tabs[4]:
        tab_log(s, user)
