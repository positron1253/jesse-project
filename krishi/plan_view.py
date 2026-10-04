"""Farmer "Farm Plan" flow: Farm -> Crops -> Plan (frozen v1 spec from the expert panel).

Screen 1  place, water, land, soil
Screen 2  top crops per plot with Rs/acre for a usual year and a bad year, risk, buyers
Screen 3  how many acres of each crop, buyers near you, audio guide
"""

import hashlib
from datetime import date, timedelta
from io import BytesIO

import streamlit as st

from krishi import crop_model as cm
from krishi import live_prices, location_ui, soilcard, soilmap
from krishi import water as water_mod
from krishi import pump as pump_mod
from krishi import crop_table, geo, live_prices, plans
from krishi import recommender as rec
from krishi import weather as wx
from krishi import assistant as _assistant
from krishi.crop_view import LANGUAGES, _build_guide, tts_available
from krishi.i18n import GUIDE_LANGUAGE, current_lang, inr, rupees, t

ACRES_PER_UNIT = {"u.acre": 1.0, "u.guntha": 0.025, "u.bigha": 0.62, "u.hectare": 2.471}
WATER_KEYS = ["rain", "till_dec", "till_mar", "all_year"]
SEASON_LABEL = {k.split(" ")[0]: k for k in wx.SEASONS}


# ---------- cached lookups ----------
@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _locate(lat, lon):
    return geo.locate(lat, lon)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _climate(lat, lon, season):
    return wx.fetch_season_climate(lat, lon, SEASON_LABEL[season])


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _mandi_now(crop_id, state):
    return live_prices.recent_modal(crop_id, state)


@st.cache_data(show_spinner=False)
def _tts(text, lang_code):
    from gtts import gTTS
    buf = BytesIO()
    gTTS(text=text, lang=lang_code).write_to_fp(buf)
    return buf.getvalue()


def _known_ids():
    return set(crop_table.all_crop_ids())


def _crop_name(crop_id):
    lang = current_lang()
    try:
        return crop_table.crop_names(crop_id)[lang]
    except Exception:
        return crop_id.replace("_", " ").title()


def current_season():
    return wx.current_season().split(" ")[0]


# ---------- state helpers ----------
def _farm():
    return st.session_state.setdefault("farm", {})


def farm_taw(farm):
    """Soil water-holding capacity (mm per metre) for this farm: chosen soil type, else map/test estimate, else default."""
    if farm.get("taw"):
        return farm["taw"]
    return water_mod.SOIL_TAW[water_mod.SOIL_OF_TYPE.get(farm.get("soil"), "unknown")]


def sow_tuple(farm):
    d = farm.get("sow_date")
    return (d.month, d.day) if d else None


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def _soil_map(lat, lon):
    return soilmap.soil_from_coordinates(lat, lon)


def _price_items(state):
    """(crop_id, harvest_months, stored mid price) for every crop, for the live price refresh."""
    df = crop_table.load_crops()
    items = []
    for crop_id, g in df.groupby("crop_id"):
        row = (g[g.state.str.lower() == str(state).lower()] if (g.state.str.lower() == str(state).lower()).any() else g[g.state == "*"]).iloc[0]
        items.append((crop_id, row["harvest_months"], row["price_q_mid"]))
    return items


def _go(step):
    st.session_state.plan_step = step
    st.rerun()


def _dots(n):
    return "●" * n + "○" * (4 - n)


# ---------- screen 1 ----------
def _place_picker(user):
    """GPS auto-fill + editable coordinates (shared component). Everything downstream reads st.session_state['farm']."""
    return location_ui.render_location(user)


def _soil_section(farm):
    """Soil: from the map by default, or the farmer's own soil-test numbers. Sets farm['ph'], ['taw'], ['soil_card']."""
    st.caption("🧪 " + t("p1.card_where"))
    mode = st.radio(t("soil.mode"), ["map", "test"], format_func=lambda m: t(f"soil.mode_{m}"), key="soil_mode",
                    horizontal=False)
    smap = None
    if farm.get("lat") is not None:
        try:
            with st.spinner(t("soil.reading")):
                smap = _soil_map(round(farm["lat"], 3), round(farm["lon"], 3))
        except Exception:
            smap = None
    farm["soil_map"] = smap

    if smap:
        with st.container(border=True):
            st.markdown(f"**🛰️ {t('soil.map_title')}**")
            m = st.columns(4)
            if smap.get("ph") is not None:
                m[0].metric("pH", f"{smap['ph']}")
            if smap.get("oc_pct") is not None:
                r = soilcard.rate("OC", smap["oc_pct"])
                m[1].metric(t("soil.oc"), f"{smap['oc_pct']}%", t(f"p1.rating_{r}") if r else None, delta_color="off")
            if smap.get("texture"):
                m[2].metric(t("soil.texture"), smap["texture"].title(), f"{t('soil.clay')} {smap['clay']}%", delta_color="off")
            if smap.get("taw_mm_per_m"):
                m[3].metric(t("soil.water"), t("soil.taw_value", v=smap["taw_mm_per_m"]))
            st.caption(t("soil.map_note"))
    else:
        st.info(t("soil.map_fail"))

    ph_default = smap["ph"] if smap and smap.get("ph") is not None else 6.8
    card = farm.setdefault("soil_card", {})
    ph = ph_default
    source = "map" if smap and smap.get("ph") is not None else "default"
    if mode == "test":
        st.caption(t("p1.card_help"))
        ph = st.number_input("pH", min_value=3.0, max_value=10.5, step=0.1, value=float(ph_default), format="%.1f", key="plan_ph")
        n1, n2, n3 = st.columns(3)
        for col, nutrient, label_key in ((n1, "N", "p1.n"), (n2, "P", "p1.p"), (n3, "K", "p1.k")):
            prev = card.get(nutrient)
            prev = 0.0 if prev is None or isinstance(prev, str) else float(prev)
            v = col.number_input(t(label_key), min_value=0.0, max_value=2000.0, value=prev, step=1.0, key=f"plan_card_{nutrient}")
            card[nutrient] = v
            r = soilcard.rate(nutrient, v)
            col.caption(t(f"p1.rating_{r}") if r else t("p1.not_entered"))
        prev = card.get("OC")
        prev = (smap or {}).get("oc_pct") or 0.0 if prev is None or isinstance(prev, str) else float(prev)
        oc = st.number_input(t("p1.oc"), min_value=0.0, max_value=6.0, value=float(prev), step=0.01, format="%.2f", key="plan_card_OC")
        card["OC"] = oc
        r = soilcard.rate("OC", oc)
        st.caption(t(f"p1.rating_{r}") if r else t("p1.not_entered"))
        st.caption(t("p1.card_note"))
        st.caption(t("p1.card_get"))
        source = "test"
    else:
        # no test: only what the map can tell (organic carbon); N, P, K stay unknown
        card.clear()
        if smap and smap.get("oc_pct"):
            card["OC"] = smap["oc_pct"]

    # optional soil-type override (for farmers who know their soil better than a 250 m map does)
    soils = list(cm.SOIL_TYPES)
    with st.expander(t("soil.override")):
        soil = st.selectbox(t("p1.soil"), [None] + soils, format_func=lambda s_: t("soil.unknown") if s_ is None else s_,
                            key="plan_soil")
    farm["soil"] = soil
    taw = None
    if soil:
        taw = water_mod.SOIL_TAW[water_mod.SOIL_OF_TYPE.get(soil, "unknown")]
        if source != "test":
            ph = cm.SOIL_TYPES[soil]["ph"]
            source = "type"
    elif smap and smap.get("taw_mm_per_m"):
        taw = smap["taw_mm_per_m"]
    farm["taw"] = taw
    farm["ph"] = ph
    farm["soil_source"] = source
    st.caption(t(f"soil.using_{source}", ph=f"{ph:.1f}", taw=taw or water_mod.SOIL_TAW["unknown"]))


def screen_farm(user):
    st.subheader(t("p1.title"))
    farm = _farm()

    st.markdown("#### 1️⃣ " + t("step.where"))
    ok = _place_picker(user)
    if ok and farm.get("state"):
        live_prices.prefetch_price_ranges(farm["state"], _price_items(farm["state"]))   # background, never blocks

    st.markdown("#### 2️⃣ " + t("step.water"))
    labels = {k: t(f"w.{k}") for k in WATER_KEYS}
    farm["water"] = st.pills(t("p1.water"), WATER_KEYS, format_func=labels.get,
                             default=farm.get("water", "rain"), key="plan_water") or farm.get("water", "rain")
    unit = st.radio(t("p1.unit"), list(ACRES_PER_UNIT), format_func=t, horizontal=True, key="plan_unit")
    c1, c2 = st.columns(2)
    if farm["water"] != "rain":
        land_w = c1.number_input(t("p1.land_water"), min_value=0.0, step=0.5, value=float(farm.get("land_w") or 1.0),
                                 key="plan_land_w")
    else:
        land_w = 0.0
    land_r = c2.number_input(t("p1.land_rain"), min_value=0.0, step=0.5, value=float(farm.get("land_r", 2.0)),
                             key="plan_land_r")
    farm["land_w"], farm["land_r"] = land_w, land_r
    farm["acres_w"], farm["acres_r"] = land_w * ACRES_PER_UNIT[unit], land_r * ACRES_PER_UNIT[unit]

    st.markdown("#### 3️⃣ " + t("step.soil"))
    _soil_section(farm)

    st.markdown("#### 4️⃣ " + t("step.sowing"))
    default_sow = farm.get("sow_date") or water_mod.default_sowing_date()
    sow = st.date_input(t("p1.sow"), value=default_sow, min_value=date.today() - timedelta(days=120),
                        max_value=date.today() + timedelta(days=400), key="plan_sow", help=t("p1.sow_help"))
    farm["sow_date"] = sow
    farm["season"] = water_mod.season_of(sow)
    days = (sow - date.today()).days
    st.caption(t("p1.sow_season", season=t(f"s.{farm['season']}"),
                 when=(t("p1.sow_in", n=days) if days > 0 else t("p1.sow_today") if days == 0 else t("p1.sow_ago", n=-days))))

    st.markdown("#### 5️⃣ " + t("p1.risk"))
    risk_labels = {k: t(f"risk.appetite_{k}") for k in ("low", "medium", "high")}
    farm["appetite"] = st.pills(t("p1.risk"), list(risk_labels), format_func=risk_labels.get,
                                default=farm.get("appetite", "medium"), key="plan_appetite",
                                label_visibility="collapsed") or "medium"

    if st.button(t("btn.next"), type="primary", use_container_width=True):
        if not ok:
            st.error(t("loc.need"))
        elif farm["acres_w"] + farm["acres_r"] <= 0:
            st.error(t("p1.no_land"))
        else:
            _go(2)


# ---------- screen 2 ----------
def _plots():
    farm = _farm()
    out = []
    if farm["acres_w"] > 0 and farm["water"] != "rain":
        out.append(rec.Plot("water", farm["acres_w"], farm["water"]))
    if farm["acres_r"] > 0:
        out.append(rec.Plot("rain", farm["acres_r"], "rain"))
    return out


def _risk_text(opt):
    return f"{t('risk.' + opt.risk)} — {t('reason.' + opt.reasons[0])}"


def _speak(opt, name):
    lo, hi = opt.profit_normal
    bad = opt.profit_worst
    text = f"{name}. " + t("card.usual", lo=inr(lo), hi=inr(hi)) + ". " + \
        (t("card.bad_loss", x=inr(-bad)) if bad < 0 else t("card.bad_profit", x=inr(bad))) + ". " + \
        _risk_text(opt)
    lang = current_lang()
    return _tts(text, lang)


def _card(opt, rank, nearby, state):
    name = _crop_name(opt.crop_id)
    lo, hi = opt.profit_normal
    with st.container(border=True):
        h1, h2 = st.columns([4, 1])
        h1.markdown(f"### 🌾 {name}")
        if rank == 1:
            h2.markdown(f"**{t('card.best')}**")
        st.markdown(f"**{t('card.usual', lo=inr(lo), hi=inr(hi))}**")
        bad = opt.profit_worst
        msg = t("card.bad_loss", x=inr(-bad)) if bad < 0 else t("card.bad_profit", x=inr(bad))
        (st.error if bad < 0 else st.info)(msg)
        st.write(t("card.yield", lo=opt.yield_q_acre[0], hi=opt.yield_q_acre[1]))
        price_line = t("card.price", p=rupees(opt.price_q))
        if opt.msp:
            price_line += " · " + t("card.msp", msp=rupees(opt.msp))
        st.caption(price_line)
        lv = (_farm().get("live_prices") or {}).get(opt.crop_id)
        if lv:
            usual = opt.row["price_q_mid"]
            diff = round(100 * (lv["latest"] / usual - 1)) if usual else 0
            st.caption(t("card.mandi_now", p=rupees(lv["latest"]), month=lv["latest_month"]) + f" ({diff:+d}% " + t("card.vs_usual") + ")")
        st.write(_risk_text(opt))
        st.caption(f"{t('card.fit')}: {_dots(opt.fit_dots)}")
        if opt.climate:
            c = opt.climate
            if c["p_poor"] > 0:
                st.write(t("card.dry_years", n=round(c["p_poor"] * c["n_years"]), total=c["n_years"]))
            try:
                hist = water_mod.fetch_history(round(_farm()["lat"], 2), round(_farm()["lon"], 2))
                share, hits, total = water_mod.heavy_rain_share(hist, opt.row["_season"], int(opt.row["duration_days"]), sow=sow_tuple(_farm()))
                if share >= 0.15:
                    st.write(t("card.heavy_rain", n=hits, total=total))
            except Exception:
                pass
        if opt.glut_note:
            st.write("🚜 " + opt.glut_note)
        buyers = nearby.buyers.get(opt.crop_id, [])
        if buyers:
            st.write(t("card.buyers", n=len(buyers), q=round(sum(b["open_q"] for b in buyers))))
        if opt.coverage == "none":
            st.caption(t("card.new"))
        if opt.est:
            st.caption("ℹ️ " + t("card.estimate"))
        c1, c2 = st.columns([1, 1])
        c1.checkbox(t("p2.choose"), value=(rank == 1), key=f"pick_{opt.plot}_{opt.crop_id}")
        if c2.button(t("card.listen"), key=f"listen_{opt.plot}_{opt.crop_id}"):
            try:
                st.audio(_speak(opt, name), format="audio/mp3", autoplay=True)
            except Exception:
                st.caption("🔇")


def screen_crops(user):
    farm = _farm()
    st.subheader(t("p2.title"))
    season = farm["season"] = water_mod.season_of(farm["sow_date"])
    st.caption("🌱 " + t("p2.sowing_line", date=farm["sow_date"].strftime("%d %b %Y"), season=t(f"s.{season}")))
    if st.button("✏️ " + t("p2.change_sowing"), key="p2_change"):
        _go(1)

    try:
        climate = _climate(round(farm["lat"], 2), round(farm["lon"], 2), season)
        st.caption(t("p2.climate", temp=climate["temperature"], rain=climate["rainfall"]))
    except Exception:
        climate = {"temperature": 26.0, "humidity": 65.0, "rainfall": 90.0}
        st.warning(t("p2.climate_fail"))
    farm["climate"] = climate

    taw = farm_taw(farm)
    sow_md_ = sow_tuple(farm)
    ctx = {"lat": round(farm["lat"], 2), "lon": round(farm["lon"], 2), "taw": taw, "sow": sow_md_}

    # live harvest-month prices from Agmarknet (fetched in the background; stored prices are used until they arrive)
    pstate = farm.get("state") or "*"
    live, live_ok = live_prices.peek_price_ranges(pstate)
    if live_ok is None:
        live_prices.prefetch_price_ranges(pstate, _price_items(pstate))
        st.caption("💰 " + t("p2.prices_loading"))
    elif live_ok:
        crop_table.set_price_overrides(pstate, live)
        st.caption("💰 " + t("p2.prices_live", n=len(live)))
    else:
        st.caption("💰 " + t("p2.prices_stored"))
    farm["live_prices"] = live if live_ok else {}
    try:
        trend = water_mod.climate_trend(water_mod.fetch_history(ctx["lat"], ctx["lon"]), season, 120, sow=sow_md_)
        if trend:
            st.caption("📈 " + t("p2.trend", recent=trend["recent_years"], years=trend["years"],
                                 rain=trend["rain_change_pct"], et0=trend["et0_change_pct"]))
    except Exception:
        pass
    try:
        hist_ = water_mod.fetch_history(ctx["lat"], ctx["lon"])
        rs = water_mod.season_rain_stats(hist_, season, 120, sow=sow_md_)
        if rs:
            st.info("🌧️ " + t("p2.rain_range", dry=round(rs["p10"]), usual=round(rs["p50"]), wet=round(rs["p90"]), n=rs["n"]))
        fc_ = water_mod.fetch_forecast(ctx["lat"], ctx["lon"], 7)
        st.info("📅 " + t("p2.forecast", days=len(fc_), rain=round(sum(d["rain"] for d in fc_)), p=max(d["p_rain"] for d in fc_)))
    except Exception:
        pass
    include_perennial = st.checkbox(t("p2.orchard"), value=False, key="plan_perennial")
    nearby = plans.nearby_signals(farm["lat"], farm["lon"], season, _known_ids(), exclude_farmer=user["id"])
    farm["nearby"] = nearby

    options = {}
    try:
        for plot in _plots():
            options[plot.name] = rec.rank_crops(
                farm.get("state") or "*", season, plot, climate, farm["ph"], nearby,
                risk_appetite=farm["appetite"], district=farm.get("district"), include_perennial=include_perennial,
                climate_ctx=ctx)
    except Exception as e:
        st.error(f"Crop data is not ready: {e}")
        if st.button(t("btn.back")):
            _go(1)
        return
    farm["options"] = options

    any_option = False
    for plot in _plots():
        opts = options.get(plot.name, [])
        if len(_plots()) > 1:
            st.markdown(f"#### {t('p2.plot_water') if plot.name == 'water' else t('p2.plot_rain')} · {plot.acres:g} acre")
        if not opts:
            st.info(t("p2.none"))
            continue
        any_option = True
        for i, o in enumerate(opts, start=1):
            _card(o, i, nearby, farm.get("state"))
    st.caption("ℹ️ " + t("card.fl_note"))
    st.caption(t("p2.ask_kvk"))

    b1, b2 = st.columns(2)
    if b1.button(t("btn.back")):
        _go(1)
    if b2.button(t("btn.make_plan"), type="primary", disabled=not any_option, use_container_width=True):
        chosen = {o.crop_id for plot, opts in options.items() for o in opts
                  if st.session_state.get(f"pick_{plot}_{o.crop_id}")}
        if not chosen:
            st.error(t("p2.pick_one"))
        else:
            farm["chosen"] = chosen
            for k in [k for k in st.session_state if k.startswith("alloc_")]:
                del st.session_state[k]
            _go(3)


# ---------- screen 3 ----------
@st.dialog("🤝")
def _agree_dialog(poll, crop_id, user, respond_fn):
    price = poll.get("price_per_quintal")
    d_from, d_to = poll.get("delivery_from", poll.get("deadline", "")), poll.get("delivery_to", poll.get("deadline", ""))
    pickup = t("pk." + poll.get("pickup", "vendor"))
    st.subheader(t("dlg.title"))
    st.write(t("dlg.terms", crop=_crop_name(crop_id), vendor=poll["vendor_name"],
               price=rupees(price) if price else "—", grade=poll.get("grade", "FAQ"),
               **{"from": d_from, "to": d_to, "pickup": pickup}))
    qty = st.number_input(t("dlg.qty"), min_value=0.0, step=1.0, key=f"dlg_qty_{poll['id']}")
    c1, c2 = st.columns(2)
    if c1.button(t("btn.agree"), type="primary", disabled=qty <= 0, use_container_width=True):
        unit_factor = {"kg": 100.0, "quintal": 1.0, "ton": 0.1, "tonne": 0.1}.get(poll.get("unit", "quintal"), 1.0)
        respond_fn(poll_id=poll["id"], farmer_id=user["id"], farmer_name=user["name"], quantity=qty * unit_factor)
        st.session_state.dlg_done = poll["id"]
        st.rerun()
    if c2.button(t("btn.not_now"), use_container_width=True):
        st.rerun()


def screen_plan(user, respond_fn):
    farm = _farm()
    st.subheader(t("plan.title"))
    options, nearby, chosen = farm["options"], farm["nearby"], farm["chosen"]
    plots = _plots()
    farm_acres = sum(p.acres for p in plots)

    sig = hashlib.md5(repr((sorted(chosen), [(p.name, p.acres, p.water) for p in plots], farm["season"])).encode()).hexdigest()[:8]
    auto = rec.allocate(plots, options, contracts=[], nearby=nearby, chosen=chosen)
    auto_acres = {(r.plot, r.crop_id): r.acres for r in auto.rows}

    rows = []
    by_key = {(o.plot, o.crop_id): o for opts in options.values() for o in opts}
    for plot in plots:
        st.markdown(f"**{t('p2.plot_water') if plot.name == 'water' else t('p2.plot_rain')} · {plot.acres:g} acre**"
                    if len(plots) > 1 else f"**{plot.acres:g} acre**")
        used = 0.0
        step = 0.25 if plot.acres < 1 else 0.5
        for o in [o for o in options.get(plot.name, []) if o.crop_id in chosen]:
            cap = rec.crop_cap_acres(o, farm_acres, nearby)
            max_v = max(0.0, min(plot.acres, cap))
            default = min(auto_acres.get((plot.name, o.crop_id), 0.0), max_v)
            label = f"{_crop_name(o.crop_id)}"
            if max_v < plot.acres:
                label += " — " + t("warn.cap", crop=_crop_name(o.crop_id), n=f"{max_v:g}")
            if max_v <= 0:
                st.caption(f"{_crop_name(o.crop_id)}: 0")
                continue
            a = st.slider(label, 0.0, float(max_v), float(default), step=step, key=f"alloc_{sig}_{plot.name}_{o.crop_id}")
            used += a
            if a > 0:
                rows.append(rec._row_for(o, a))
        left = plot.acres - used
        if left > 1e-9:
            st.caption(t("plan.left", x=f"{left:g}"))
        elif left < -1e-9:
            st.error(f"{-left:g} acre too many on this land")
    plan = rec.FarmPlan(rows=rows, unused={}, warnings=[])

    if rows:
        lo, hi = plan.total_normal
        c1, c2 = st.columns(2)
        c1.metric(t("plan.usual_label"), f"{inr(lo)} – {inr(hi)}")
        c2.metric(t("plan.bad_label"), inr(plan.total_worst))
        if any(by_key[(r.plot, r.crop_id)].est for r in rows):
            st.warning(t("plan.est_note"))
        for r in rows:
            st.write("• " + t("plan.row", crop=_crop_name(r.crop_id), acres=f"{r.acres:g}", qlo=r.yield_q[0], qhi=r.yield_q[1]))
            o = by_key[(r.plot, r.crop_id)]
            if o.glut_note:
                st.caption("🚜 " + o.glut_note)
        crop_acres = {}
        for r in rows:
            crop_acres[r.crop_id] = crop_acres.get(r.crop_id, 0) + r.acres
        for cid, acres in crop_acres.items():
            if farm_acres > 1 and acres / farm_acres > 0.7:
                st.warning(t("warn.one_crop", crop=_crop_name(cid)))
            demand = nearby.vendor_q.get(cid, 0)
            produce = sum(r.yield_q[1] for r in rows if r.crop_id == cid)
            if demand and produce > demand * 1.5:
                st.warning(t("warn.over_demand", crop=_crop_name(cid), q=round(demand)))

        if st.button(t("btn.save_plan"), type="primary", use_container_width=True):
            plans.save_plan(user["id"], farm["lat"], farm["lon"], farm["season"], plan,
                            meta={"water": farm["water"], "soil": farm.get("soil"), "state": farm.get("state"),
                                  "taw": farm_taw(farm), "sow_date": farm["sow_date"].isoformat(),
                                  "lat_label": farm.get("place") or farm.get("district")})
            st.success(t("msg.saved"))
            st.session_state["plan_saved_now"] = True


    if st.session_state.get("plan_saved_now"):
        n1, n2 = st.columns(2)
        if n1.button("➡️ " + t("home.t_myfarm"), key="after_save_farm", type="primary", use_container_width=True):
            st.session_state["plan_saved_now"] = False
            st.session_state.view = "my_farm"
            st.rerun()
        if n2.button("➡️ " + t("home.t_sell"), key="after_save_sell", use_container_width=True):
            st.session_state["plan_saved_now"] = False
            st.session_state.view = "sell"
            st.rerun()

    # Water, power and CO2 against the usual practice, for crops on watered land
    watered = [r for r in rows if r.plot == "water"]
    if watered:
        with st.expander(t("plan.water_title")):
            try:
                taw = farm_taw(farm)
                lat2, lon2 = round(farm["lat"], 2), round(farm["lon"], 2)
                shown_note = False
                for r in watered:
                    o = by_key[(r.plot, r.crop_id)]
                    cmp = water_mod.compare_practice(lat2, lon2, r.crop_id, farm["season"], int(o.row["duration_days"]),
                                                     taw, farm["water"], acres=r.acres, sow=sow_tuple(farm))
                    if not cmp:
                        continue
                    if not shown_note:
                        st.caption(t("plan.water_note", n=cmp["n_years"], head=int(water_mod.PUMP_HEAD_M),
                                     eff=int(water_mod.PUMP_EFFICIENCY * 100)))
                        shown_note = True
                    b, f, e = cmp["baseline"], cmp["sched_flood"], cmp["sched_efficient"]
                    sv = lambda a: (t("plan.water_less", x=round(a["saved_pct"])) if a["saved_pct"] >= 0
                                    else t("plan.water_more", x=round(-a["saved_pct"])))
                    st.markdown("**" + t("plan.water_row", crop=_crop_name(r.crop_id), acres=f"{r.acres:g}") + "**")
                    st.write("• " + t("plan.water_base", m3=rupees(b["m3"]), kwh=rupees(b["kwh"]), y=round(100 * b["rel_yield"])))
                    st.write("• " + t("plan.water_l1", m3=rupees(f["m3"]), saved=sv(f), y=round(100 * f["rel_yield"])))
                    st.write("• " + t("plan.water_l2", m3=rupees(e["m3"]), saved=sv(e), kwh=rupees(e["kwh"]),
                                      co2=rupees(e["co2_kg"]), saved_kwh=rupees(max(0, e["saved_kwh"])),
                                      y=round(100 * e["rel_yield"])))
            except Exception:
                st.caption("—")


        with st.expander(t("pump.title")):
            wc = sorted({r.crop_id for r in watered}, key=_crop_name)
            pc = st.selectbox(t("p2.choose"), wc, format_func=_crop_name, key="pump_crop")
            pr = next(r for r in watered if r.crop_id == pc)
            po = by_key[(pr.plot, pr.crop_id)]
            q1, q2, q3 = st.columns(3)
            hours = q1.number_input(t("pump.hours"), min_value=2.0, max_value=24.0, value=8.0, step=1.0, key="pump_hours",
                                    help=t("pump.hours_help"))
            head = q2.number_input(t("pump.head"), min_value=5.0, max_value=200.0, value=float(water_mod.PUMP_HEAD_M), step=5.0, key="pump_head")
            drip = q3.checkbox(t("pump.drip"), value=False, key="pump_drip")
            try:
                peak = pump_mod.peak_demand_mm_day(farm["lat"], farm["lon"], pc, farm["season"], int(po.row["duration_days"]), sow=sow_tuple(farm))
                sz = pump_mod.size_pump(pr.acres, peak, hours, head, water_mod.PUMP_EFFICIENCY, 0.9 if drip else 0.6)
                st.write(t("pump.result", acres=f"{pr.acres:g}", peak=f"{peak:.1f}", m3=rupees(sz["daily_m3"]),
                           hp=sz["hp"], kwp=sz["array_kwp"]))
                st.caption(t("pump.assume"))
                cur = st.number_input(t("pump.current_hp"), min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="pump_cur")
                if cur and cur > sz["hp"]:
                    st.warning(t("pump.oversized", cur=f"{cur:g}", hp=sz["hp"]))
                st.markdown(f"**{t('pump.payback_title')}**")
                st.caption(t("pump.payback_help"))
                src = st.radio(t("pump.source"), ["grid", "diesel"], format_func=lambda k: t(f"pump.src_{k}"), horizontal=True, key="pump_src")
                price_label = t("pump.tariff") if src == "grid" else t("pump.diesel_price")
                unit_price = st.number_input(price_label, min_value=0.0, value=0.0, step=1.0, key="pump_price")
                cost = st.number_input(t("pump.cost"), min_value=0.0, value=0.0, step=10000.0, key="pump_cost")
                if cost > 0 and unit_price > 0:
                    taw = farm_taw(farm)
                    cmp = water_mod.compare_practice(round(farm["lat"], 2), round(farm["lon"], 2), pc, farm["season"],
                                                     int(po.row["duration_days"]), taw, farm["water"], acres=pr.acres,
                                                     head_m=head, sow=sow_tuple(farm))
                    kwh = cmp["sched_efficient" if drip else "sched_flood"]["kwh"]
                    pb = pump_mod.solar_payback(cost, kwh, src, unit_price if src == "grid" else None,
                                                unit_price if src == "diesel" else None)
                    if pb["payback_years"]:
                        st.success(t("pump.payback_result", own=inr(pb["farmer_share_rs"]), sub=inr(pb["subsidy_rs"]),
                                     save=inr(pb["annual_saving_rs"]), yrs=f"{pb['payback_years']:.1f}",
                                     co2=rupees(pb["annual_co2_kg"])))
            except Exception:
                st.caption("—")

        with st.expander(t("irrig.title")):
            crop_opts = sorted({r.crop_id for r in watered}, key=_crop_name)
            ic = st.selectbox(t("p2.choose"), crop_opts, format_func=_crop_name, key="irrig_crop")
            d_since = st.number_input(t("irrig.days"), min_value=0, max_value=400, value=0, key="irrig_days")
            last = st.number_input(t("irrig.last"), min_value=0, max_value=60, value=0, key="irrig_last")
            if st.button(t("irrig.go"), key="irrig_go"):
                try:
                    o = next(o for o in options["water"] if o.crop_id == ic)
                    taw = farm_taw(farm)
                    adv = water_mod.next_irrigation_advice(
                        farm["lat"], farm["lon"], ic, int(d_since), int(o.row["duration_days"]), taw,
                        last_irrigation_days_ago=int(last) or None)
                    if adv["action"] == "irrigate":
                        st.success(t("irrig.irrigate", when=adv["when"].isoformat(), mm=adv["net_mm"]))
                    else:
                        st.info(t("irrig.wait"))
                    st.caption(t("irrig.rain", p=max(d["p_rain"] for d in adv["plan"])))
                except Exception:
                    st.error(t("ask.error"))

    # Buyers
    st.markdown(f"### {t('buyer.title')}")
    shown = False
    for cid in chosen:
        for b in nearby.buyers.get(cid, []):
            shown = True
            with st.container(border=True):
                st.write(t("buyer.line", vendor=b["vendor_name"], km=b["distance_km"],
                           qty=round(b["open_q"]), crop=_crop_name(cid)))
                price = b.get("price_per_quintal")
                if price:
                    st.caption(t("buyer.terms", price=rupees(price), grade=b.get("grade", "FAQ"),
                                 **{"from": b.get("delivery_from", b.get("deadline")), "to": b.get("delivery_to", b.get("deadline")),
                                    "pickup": t("pk." + b.get("pickup", "vendor"))}))
                else:
                    st.caption(t("buyer.no_price"))
                if st.button(t("btn.can_give"), key=f"give_{b['id']}"):
                    _agree_dialog(b, cid, user, respond_fn)
                if st.session_state.get("dlg_done") == b["id"]:
                    poll_now = next((p for p in plans._load(plans.POLLS_FILE) if p["id"] == b["id"]), {})
                    code = next((r.get("reference_code") for r in poll_now.get("responses", [])
                                 if r["farmer_id"] == user["id"]), "")
                    st.success(t("dlg.done", code=code))
    if not shown:
        st.info(t("buyer.none"))

    # Audio guide
    st.markdown(f"### {t('guide.title')}")
    crops = sorted(chosen, key=lambda c: _crop_name(c))
    crop_pick = st.radio(t("p2.choose"), crops, format_func=_crop_name, horizontal=True, key="plan_guide_crop")
    guide_langs = list(LANGUAGES)
    default_lang = GUIDE_LANGUAGE[current_lang()]
    glang = st.selectbox(t("guide.lang"), guide_langs, index=guide_langs.index(default_lang), key="plan_guide_lang")
    cache = st.session_state.setdefault("guide_cache", {})
    key = (crop_pick, glang, farm["season"])
    if st.button(t("btn.guide"), key="plan_guide_btn"):
        with st.spinner(t("guide.wait")):
            try:
                result = {"inputs": {"temperature": farm["climate"]["temperature"], "humidity": farm["climate"]["humidity"],
                                     "rainfall": farm["climate"]["rainfall"], "ph": farm["ph"], "card": farm.get("soil_card") or {}},
                          "season": SEASON_LABEL[farm["season"]], "lat": farm["lat"], "lon": farm["lon"]}
                label = crop_table.crop_names(crop_pick)["en"]
                cache[key] = _build_guide(label, result, glang, _together_key())
            except Exception as e:
                st.error(str(e))
    g = cache.get(key)
    if g and g.get("translated") is False:
        st.warning(t("guide.untranslated"))
    if g:
        if g.get("audio"):
            st.audio(g["audio"], format=_assistant.audio_mime(g["audio"]))
        elif not tts_available(LANGUAGES[glang]):
            st.info(t("guide.no_audio"))
        st.write(g["text"])
        if glang != "English":
            with st.expander(t("guide.english")):
                st.write(g["english"])

    if st.button(t("btn.back")):
        _go(2)


_KEY = {"v": None}


def set_together_key(key):
    _KEY["v"] = key


def _together_key():
    return _KEY["v"]


def render(user, respond_fn, together_key):
    set_together_key(together_key)
    step = st.session_state.setdefault("plan_step", 1)
    farm_ = st.session_state.setdefault("farm", {})
    if not farm_.get("sow_date"):          # e.g. a page opened mid-flow: fall back to the season's typical start
        farm_["sow_date"] = water_mod.default_sowing_date()
        farm_["season"] = water_mod.season_of(farm_["sow_date"])
    # progress indicator
    st.progress(step / 3)
    if step == 1 or "farm" not in st.session_state or "acres_w" not in _farm():
        st.session_state.plan_step = 1
        screen_farm(user)
    elif step == 2:
        screen_crops(user)
    else:
        if "chosen" not in _farm():
            _go(2)
        screen_plan(user, respond_fn)
