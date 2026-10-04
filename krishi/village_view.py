"""Village water screen: everyone's saved crop plans added up into irrigation demand, power and CO2."""

import pandas as pd
import streamlit as st

from krishi import location_ui, village, water
from krishi.i18n import current_lang, inr, rupees, t
from krishi.crop_table import crop_names
from krishi.plan_view import SEASON_LABEL, current_season


def _name(crop_id):
    try:
        return crop_names(crop_id)[current_lang()]
    except Exception:
        return crop_id.replace("_", " ").title()


@st.cache_data(ttl=600, show_spinner=False)
def _roll_up(lat, lon, km, season, budget):
    return village.village_water(lat, lon, km, season, budget or None)


@st.cache_data(ttl=600, show_spinner=False)
def _swaps(lat, lon, season, rows_key, rows):
    return village.swap_suggestions(lat, lon, season, rows)


def render(user):
    st.subheader(t("village.title"))
    st.caption(t("village.sub"))

    location_ui.render_location(user)
    farm = st.session_state.get("farm") or {}
    lat = farm.get("lat") or user.get("latitude")
    lon = farm.get("lon") or user.get("longitude")
    if lat is None:
        st.info(t("loc.need"))
        return

    c1, c2 = st.columns(2)
    season = c1.pills(t("p2.season"), list(SEASON_LABEL), format_func=lambda s: t(f"s.{s}"),
                      default=current_season(), key="vil_season") or current_season()
    km = c2.select_slider(t("village.radius"), options=[2, 5, 10, 20], value=5, key="vil_km")
    budget = st.number_input(t("village.budget"), min_value=0.0, step=1000.0, value=0.0, key="vil_budget",
                             help=t("village.budget_help"))

    with st.spinner(t("village.wait")):
        res = _roll_up(round(lat, 3), round(lon, 3), km, season, budget)
    if not res:
        st.info(t("village.none"))
        return
    if res["demo"]:
        st.warning(t("village.demo"))

    m = st.columns(4)
    m[0].metric(t("village.farmers"), res["farmers"])
    m[1].metric(t("village.acres"), f"{res['acres']:.0f}", f"{res['irrigated_acres']:.0f} " + t("village.irrigated"))
    m[2].metric(t("village.demand"), f"{rupees(res['demand_m3_p50'])} m³", f"{t('village.bad')}: {rupees(res['demand_m3_p90'])} m³",
                delta_color="off")
    m[3].metric(t("village.power"), f"{rupees(res['kwh_p50'])} kWh", f"{rupees(res['co2_kg_p50'] / 1000)} t CO₂", delta_color="off")

    if "budget_m3" in res:
        if res["gap_p50_m3"] > 0:
            st.error(t("village.over", x=rupees(res["gap_p50_m3"]), y=rupees(res["gap_p90_m3"])))
        elif res["gap_p90_m3"] > 0:
            st.warning(t("village.tight", y=rupees(res["gap_p90_m3"])))
        else:
            st.success(t("village.ok"))

    df = pd.DataFrame([{
        t("tbl.crop"): _name(r["crop_id"]), t("village.water_col"): t(f"w.{r['water']}"), t("tbl.acres"): round(r["acres"], 1),
        t("tbl.farms"): r["farmers"], t("village.mm"): round(r["irrigation_mm_p50"]),
        t("village.demand"): round(r["demand_m3_p50"]), t("village.bad"): round(r["demand_m3_p90"]),
    } for r in res["rows"]])
    st.dataframe(df, use_container_width=True, hide_index=True)
    chart = df.set_index(t("tbl.crop"))[[t("village.demand")]]
    st.bar_chart(chart)

    sugg = _swaps(round(lat, 3), round(lon, 3), season, len(res["rows"]), res["rows"])
    if sugg:
        st.markdown(f"**{t('village.shift')}**")
        for s in sugg:
            st.write("• " + t("village.shift_line", a=_name(s["from"]), b=_name(s["to"]),
                              m3=rupees(s["saved_m3_per_acre"]), rs=inr(s["profit_change_per_acre"])))
    st.caption(t("village.note", head=int(water.PUMP_HEAD_M), eff=int(water.PUMP_EFFICIENCY * 100)))
