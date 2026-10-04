"""One place for the farm location: GPS auto-fill, a village search, and editable coordinates.

Everything else in the app (crop ranking, water, village roll-up, assistant) reads the location from
st.session_state["farm"] (lat, lon, state, district, place, loc_source), so whatever is set here drives all of it.

GPS notes: the browser asks permission once. The library's GPS call never reports a refusal (it just never answers),
so we stop waiting after GPS_WAIT_SECONDS and leave the manual controls open.
"""

import time

import streamlit as st
from streamlit_js_eval import get_geolocation

from krishi import accounts, geo
from krishi import weather as wx
from krishi.i18n import t

GPS_WAIT_SECONDS = 20
DERIVED_KEYS = ("options", "nearby", "chosen", "climate")   # computed from the location; cleared when it changes


def _farm():
    return st.session_state.setdefault("farm", {})


def set_location(lat, lon, source, place=None, state=None, district=None):
    """Make (lat, lon) the farm location. Looks up state and district unless they are given."""
    farm = _farm()
    moved = (round(farm.get("lat") or 0.0, 4), round(farm.get("lon") or 0.0, 4)) != (round(lat, 4), round(lon, 4))
    if state is None and district is None:
        info = geo.locate(round(lat, 3), round(lon, 3)) or {}
        state, district = info.get("state"), info.get("district")
        place = place or info.get("place")
    farm.update(lat=lat, lon=lon, state=state, district=district, place=place, loc_source=source,
                loc_rev=farm.get("loc_rev", 0) + 1)
    if moved:
        for k in DERIVED_KEYS:
            farm.pop(k, None)


def _start_from_account(user):
    farm = _farm()
    lat, lon = user.get("latitude"), user.get("longitude")
    if lat is not None and lon is not None:
        farm.update(lat=lat, lon=lon, state=user.get("state"), district=user.get("district"), loc_source="saved")
        if not farm.get("state"):
            set_location(lat, lon, "saved")
    farm["want_gps"] = True          # try the phone's GPS once per session
    farm["gps_started"] = time.time()


def _poll_gps():
    """Ask the browser for the position. Returns 'ok', 'waiting' or 'gave_up'."""
    farm = _farm()
    loc = get_geolocation(component_key=f"gps_{farm.get('gps_run', 0)}")
    coords = (loc or {}).get("coords") if isinstance(loc, dict) else None
    if coords and coords.get("latitude") is not None:
        set_location(coords["latitude"], coords["longitude"], "gps")
        farm.update(want_gps=False, gps_accuracy=coords.get("accuracy"))
        return "ok"
    if time.time() - farm.get("gps_started", time.time()) > GPS_WAIT_SECONDS:
        farm["want_gps"] = False
        return "gave_up"
    return "waiting"


def render_location(user, compact=False):
    """Show the current location and let the farmer re-detect by GPS or edit it. Returns True if usable."""
    farm = _farm()
    if "lat" not in farm and "loc_source" not in farm:
        _start_from_account(user)

    status = None
    if farm.get("want_gps"):
        status = _poll_gps()
        if status == "ok":
            st.rerun()

    ok = farm.get("lat") is not None and not wx.check_coordinates(farm.get("lat"), farm.get("lon"))
    src = {"gps": "loc.src_gps", "saved": "loc.src_saved", "manual": "loc.src_manual", "search": "loc.src_manual"}.get(
        farm.get("loc_source"), "loc.src_saved")
    place = ", ".join(x for x in [farm.get("place") or "", farm.get("district") or "", farm.get("state") or ""] if x)
    if farm.get("lat") is not None:
        st.markdown(f"**{t(src)}**  \n📍 {place or t('loc.saved')} · `{farm['lat']:.4f}, {farm['lon']:.4f}`")
        if farm.get("loc_source") == "gps" and farm.get("gps_accuracy"):
            st.caption(t("loc.accuracy", m=round(farm["gps_accuracy"])))
    if status == "waiting":
        st.caption(t("loc.detecting"))
    elif status == "gave_up":
        st.caption(t("loc.denied"))
    for problem in ([] if ok else wx.check_coordinates(farm.get("lat"), farm.get("lon"))):
        st.error(f"📍 {problem}")

    rev = farm.get("loc_rev", 0)
    with st.expander("✏️ " + t("loc.edit"), expanded=not ok):
        if st.button(t("loc.use_gps"), key=f"loc_gps_btn_{rev}", use_container_width=True):
            farm.update(want_gps=True, gps_started=time.time(), gps_run=farm.get("gps_run", 0) + 1)
            st.rerun()

        q = st.text_input(t("loc.search"), placeholder=t("loc.search_ph"), key=f"loc_q_{rev}")
        results = geo.search_places(q) if q else []
        if results:
            i = st.selectbox(t("loc.pick"), range(len(results)), format_func=lambda i: results[i]["label"],
                             key=f"loc_pick_{rev}")
            if st.button("✔ " + t("loc.apply"), key=f"loc_pick_ok_{rev}"):
                r = results[i]
                set_location(r["lat"], r["lon"], "search", place=r["label"].split(",")[0], state=r["state"],
                             district=r["district"])
                st.rerun()

        st.caption(t("loc.coords_help"))
        c1, c2 = st.columns(2)
        lat = c1.number_input(t("loc.lat"), value=float(farm.get("lat") or 0.0), format="%.4f", step=0.0001, key=f"loc_lat_{rev}")
        lon = c2.number_input(t("loc.lon"), value=float(farm.get("lon") or 0.0), format="%.4f", step=0.0001, key=f"loc_lon_{rev}")
        if st.button("✔ " + t("loc.apply_coords"), key=f"loc_coords_ok_{rev}", type="primary", use_container_width=True):
            problems = wx.check_coordinates(lat, lon)
            if problems:
                for p in problems:
                    st.error(f"📍 {p}")
            else:
                set_location(lat, lon, "manual")
                st.rerun()

        differs = farm.get("lat") is not None and (
            round(farm["lat"], 4) != round(user.get("latitude") or 0.0, 4) or round(farm["lon"], 4) != round(user.get("longitude") or 0.0, 4))
        if ok and differs and st.button(t("loc.save_profile"), key=f"loc_save_{rev}", use_container_width=True):
            utype = st.session_state.get("current_user_type", "farmer")
            if accounts.update_location(user["id"], utype, farm["lat"], farm["lon"], farm.get("state"), farm.get("district")):
                user["latitude"], user["longitude"] = farm["lat"], farm["lon"]
                st.success(t("loc.saved_profile"))
    return ok
