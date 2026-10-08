"""My farm tab: the farmer's chosen crops (with sowing dates), irrigation system, and the watering schedule."""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from krishi import crop_table, farmprofile, plans, water
from krishi.i18n import current_lang, inr, rupees, t


def _name(crop_id):
    try:
        return crop_table.crop_names(crop_id)[current_lang()]
    except Exception:
        return crop_id.replace("_", " ").title()


def _duration(crop_id):
    df = crop_table.load_crops()
    return int(df[df.crop_id == crop_id].duration_days.iloc[0])


def _sow(row):
    s = row.get("sow_date")
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


def _level(row):
    return row.get("water") if row.get("plot") == "water" and row.get("water") else "rain"


def _stage(row, today):
    sow = _sow(row)
    if not sow:
        return None
    dur = _duration(row["crop_id"])
    day = (today - sow).days
    if day < 0:
        return t("farm.not_sown", n=-day)
    if day > dur:
        return t("farm.harvest_done")
    frac = day / dur
    key = "farm.stage_ini" if frac < 0.2 else "farm.stage_dev" if frac < 0.45 else "farm.stage_mid" if frac < 0.75 else "farm.stage_late"
    return t("farm.day_of", day=day, total=dur, stage=t(key))


def _ask_about(row):
    st.session_state["ask_focus"] = {"row_id": row["id"], "crop_id": row["crop_id"], "sow_date": row.get("sow_date"),
                                     "acres": row["acres"], "water": _level(row)}
    st.session_state.view = "assistant"
    st.rerun()


def tab_crops(user, rows):
    today = date.today()
    for row in rows:
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            sow = _sow(row)
            c1.markdown(f"### 🌾 {_name(row['crop_id'])}")
            c1.write(t("farm.row_line", acres=f"{row['acres']:g}", season=t(f"s.{row['season']}"),
                       water=t(f"w.{_level(row)}")))
            stage = _stage(row, today)
            if stage:
                c1.info(stage)
            if sow:
                c1.caption(t("farm.harvest_expected", date=(sow + timedelta(days=_duration(row['crop_id']))).strftime("%d %b %Y")))
            c1.caption(t("farm.yield_line", lo=row.get("yield_q_lo", 0), hi=row.get("yield_q_hi", 0)))
            new_sow = c2.date_input(t("farm.sow_date"), value=sow or today, min_value=today - timedelta(days=400),
                                    max_value=today + timedelta(days=400), key=f"farm_sow_{row['id']}")
            b1, b2, b3 = c2.columns(3)
            if new_sow != sow and b1.button("💾", key=f"farm_save_{row['id']}", help=t("farm.save_date")):
                plans.update_row(row["id"], sow_date=new_sow.isoformat())
                farmprofile.clear_events(row["id"])
                st.rerun()
            if b2.button("💬", key=f"farm_ask_{row['id']}", help=t("farm.ask_about")):
                _ask_about(row)
            if b3.button("🗑", key=f"farm_del_{row['id']}", help=t("farm.remove")):
                plans.delete_row(row["id"], user["id"])
                st.rerun()


def tab_system(user):
    prof, saved = farmprofile.get_profile(user["id"])
    if not saved:
        st.info(t("farm.system_none"))
    with st.form("irrigation_system"):
        c1, c2 = st.columns(2)
        method = c1.radio(t("farm.method"), list(farmprofile.METHOD_EFFICIENCY), format_func=lambda m: t(f"farm.m_{m}"),
                          index=list(farmprofile.METHOD_EFFICIENCY).index(prof["method"]))
        source = c2.selectbox(t("farm.source"), farmprofile.SOURCES, format_func=lambda s: t(f"farm.s_{s}"),
                              index=farmprofile.SOURCES.index(prof["source"]))
        d1, d2, d3, d4 = st.columns(4)
        hp = d1.number_input(t("farm.pump_hp"), min_value=0.0, max_value=50.0, value=float(prof["pump_hp"]), step=0.5)
        power = d2.selectbox(t("farm.power"), farmprofile.POWER, format_func=lambda p: t(f"pump.src_{p}") if p != "solar" else t("farm.p_solar"),
                             index=farmprofile.POWER.index(prof["power"]))
        hours = d3.number_input(t("pump.hours"), min_value=1.0, max_value=24.0, value=float(prof["hours_per_day"]), step=1.0)
        lift = d4.number_input(t("pump.head"), min_value=3.0, max_value=250.0, value=float(prof["lift_m"]), step=5.0)
        if st.form_submit_button(t("farm.save_system"), type="primary"):
            farmprofile.save_profile(user["id"], {"method": method, "source": source, "pump_hp": hp, "power": power,
                                                  "hours_per_day": hours, "lift_m": lift})
            st.success(t("log.saved"))
            st.rerun()
    flow = farmprofile.pump_flow_m3h(prof["pump_hp"], prof["lift_m"])
    m = st.columns(3)
    m[0].metric(t("farm.eff"), f"{farmprofile.efficiency(prof) * 100:.0f}%")
    m[1].metric(t("farm.flow"), f"{flow:.1f} m³/h")
    m[2].metric(t("farm.per_day"), f"{flow * prof['hours_per_day']:.0f} m³")
    st.caption(t("farm.system_note"))


def tab_schedule(user, rows):
    prof, _ = farmprofile.get_profile(user["id"])
    eff = farmprofile.efficiency(prof)
    flow = farmprofile.pump_flow_m3h(prof["pump_hp"], prof["lift_m"]) or None
    watered = [r for r in rows if _level(r) != "rain" and _sow(r)]
    if not watered:
        st.info(t("farm.sched_none"))
        return
    row = st.selectbox(t("p2.choose"), watered, format_func=lambda r: f"{_name(r['crop_id'])} · {r['acres']:g} " + t("tbl.acres") + f" · {_sow(r).strftime('%d %b')}",
                       key="farm_sched_row")
    sow = _sow(row)
    duration = _duration(row["crop_id"])
    taw = row.get("taw") or water.SOIL_TAW[water.SOIL_OF_TYPE.get(row.get("soil"), "unknown")]
    actual = farmprofile.events_for(row["id"])
    try:
        with st.spinner(t("farm.sched_wait")):
            sch = water.live_schedule(row["lat"], row["lon"], row["crop_id"], sow, duration, taw, _level(row), eff,
                                      actual_events=actual if actual else None)
    except Exception:
        sch = None
    if not sch:
        st.warning(t("p2.climate_fail"))
        return

    ev = sch["events"]
    upcoming = [e for e in ev if e["status"] in ("today", "upcoming")]
    if upcoming:
        n = upcoming[0]
        if n["status"] == "today":
            st.success(t("farm.water_today", mm=round(n["gross_mm"])))
        else:
            st.success(t("farm.next_water", date=n["date"].strftime("%d %b"), days=(n["date"] - date.today()).days, mm=round(n["gross_mm"])))
    else:
        st.info(t("farm.no_more_water"))
    if not sch["weather_ok"]:
        st.warning(t("farm.sched_typical_only"))
    if sch["days_of_forecast"]:
        st.caption(t("farm.sched_basis", n=sch["days_of_forecast"], y=sch["typical_year"]))

    acres = row["acres"]
    total_m3 = sch["gross_mm"] * 4.047 * acres
    kwh = water.pump_energy_kwh(total_m3, prof["lift_m"])
    m = st.columns(4)
    m[0].metric(t("farm.waterings"), sch["n"])
    m[1].metric(t("wat.water"), f"{rupees(total_m3)} m³")
    m[2].metric(t("wat.energy"), f"{rupees(kwh)} kWh" if prof["power"] == "grid" else f"{rupees(kwh)} kWh eq.")
    m[3].metric(t("farm.pump_hours"), f"{total_m3 / flow:.0f} h" if flow else "—")

    if ev:
        df = pd.DataFrame([{
            t("wat.date"): e["date"].strftime("%d %b %Y"), t("farm.status"): t(f"farm.st_{e['status']}"),
            t("farm.depth"): round(e["gross_mm"]), t("farm.volume"): round(e["gross_mm"] * 4.047 * acres),
            t("farm.pump_hours"): round(e["gross_mm"] * 4.047 * acres / flow, 1) if flow else None,
            t("farm.based_on"): t(f"farm.basis_{e['basis']}")} for e in ev])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.bar_chart(pd.DataFrame({t("farm.depth"): [e["gross_mm"] for e in ev]}, index=[e["date"].strftime("%d %b") for e in ev]))
    st.caption(t("farm.sched_note", eff=int(eff * 100), cap=water.MAX_NET_IRRIGATION_MM))

    # what the farmer really did (only possible once the crop is sown)
    st.markdown(f"**{t('farm.log_title')}**")
    if sow > date.today():
        st.caption(t("farm.log_not_yet", date=sow.strftime("%d %b %Y")))
        return
    st.caption(t("farm.log_help"))
    c1, c2, c3 = st.columns([2, 2, 1])
    wday = c1.date_input(t("wat.date"), value=date.today(), min_value=sow, max_value=date.today(), key="farm_wdate")
    wmm = c2.number_input(t("farm.log_mm"), min_value=5.0, max_value=150.0, value=float(water.MAX_NET_IRRIGATION_MM), step=5.0, key="farm_wmm")
    if c3.button(t("farm.log_add"), key="farm_wadd", type="primary", use_container_width=True):
        farmprofile.add_event(row["id"], wday, wmm)
        st.rerun()
    if actual:
        st.caption(t("farm.log_done", n=len(actual)) + " " + ", ".join(d.strftime("%d %b") for d in sorted(actual)))
        if st.button(t("farm.log_reset"), key="farm_wreset"):
            farmprofile.clear_events(row["id"])
            st.rerun()


def render(user):
    rows = plans.farmer_rows(user["id"])
    if not rows:
        st.info(t("farm.none"))
        if st.button(t("home.t_plan"), type="primary", use_container_width=True):
            st.session_state.view = "crop_prediction"
            st.rerun()
        return
    tabs = st.tabs([t("farm.tab_crops"), t("farm.tab_system"), t("farm.tab_schedule")])
    with tabs[0]:
        tab_crops(user, rows)
    with tabs[1]:
        tab_system(user)
    with tabs[2]:
        tab_schedule(user, rows)
