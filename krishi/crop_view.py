"""Crop recommendation page: location -> soil -> climate -> top-3 crops -> guide + audio."""

from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from krishi import crop_model as cm
from krishi import weather as wx
from krishi.ui import crop_card, step_header

from krishi.languages import LANGUAGES  # name -> code, 20 Indian languages + English
from krishi import assistant as _assistant


def tts_available(code):
    return _assistant.has_tts(code)


GUIDE_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",  # original model, no longer serverless on Together
]


@st.cache_resource
def _model():
    return cm.load_model()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _climate(lat, lon, season):
    return wx.fetch_season_climate(lat, lon, season)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _soil_ph(lat, lon):
    return cm.fetch_soil_ph(lat, lon)


def _set_default(key, value):
    """Prefill a widget once per new data signature without fighting user edits."""
    st.session_state[key] = value


def render(user, together_api_key):
    lat, lon = user.get("latitude"), user.get("longitude")

    # ---------------- Step 1: location, season, language ----------------
    with st.container(border=True):
        step_header(1, "Your farm & season",
                    "We use your registered farm location to look up local climate.")
        coord_problems = wx.check_coordinates(lat, lon)
        c1, c2 = st.columns([3, 2])
        with c1:
            if coord_problems:
                for p in coord_problems:
                    st.error(f"📍 {p}")
                st.caption("Enter your farm's correct location below (open Google Maps → long-press your field → copy the numbers).")
                cc1, cc2 = st.columns(2)
                lat = cc1.number_input("Farm latitude", value=float(lat or 0.0), format="%.4f", key="cp_lat")
                lon = cc2.number_input("Farm longitude", value=float(lon or 0.0), format="%.4f", key="cp_lon")
                coord_problems = wx.check_coordinates(lat, lon)
            else:
                st.markdown(f"📍 **Farm location:** {lat:.4f}, {lon:.4f}")
                with st.expander("Use a different location for this farm"):
                    cc1, cc2 = st.columns(2)
                    lat = cc1.number_input("Farm latitude", value=float(lat), format="%.4f", key="cp_lat")
                    lon = cc2.number_input("Farm longitude", value=float(lon), format="%.4f", key="cp_lon")
                    coord_problems = wx.check_coordinates(lat, lon)
            seasons = list(wx.SEASONS.keys())
            season = st.radio("Which season are you planning for?", seasons,
                              index=seasons.index(wx.current_season()), horizontal=False, key="cp_season")
            include_perennial = st.checkbox("Also suggest orchard / plantation crops (mango, banana, coconut…)",
                                            value=True, key="cp_perennial")
        with c2:
            if not coord_problems:
                st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=8, height=230)
            language = st.selectbox("Guidance language", list(LANGUAGES.keys()), key="cp_lang")

    if coord_problems:
        st.warning("Fix the farm location above to continue.")
        return

    # ---------------- Step 2: soil ----------------
    with st.container(border=True):
        step_header(2, "Your soil",
                    "Soil nutrients matter most for the recommendation. Soil Health Card values are the most accurate.")
        mode = st.radio("How do you want to enter soil details?",
                        ["I know my soil type", "I have a Soil Health Card (soil test)"],
                        horizontal=True, key="cp_soil_mode")
        if mode == "I know my soil type":
            soil_type = st.selectbox("Soil type", list(cm.SOIL_TYPES.keys()), key="cp_soil_type")
            preset = cm.SOIL_TYPES[soil_type]
            sig = ("soil", soil_type)
            if st.session_state.get("cp_soil_sig") != sig:
                for k in ("N", "P", "K", "ph"):
                    _set_default(f"cp_{k}", float(preset[k]))
                st.session_state.cp_soil_sig = sig
            st.caption("ℹ️ Typical values for this soil type are filled in. Edit them if you know better.")
        else:
            st.caption("Copy N, P, K (kg/ha) and pH from your Soil Health Card.")
            if st.session_state.get("cp_soil_sig") is None:
                for k, v in {"N": 50.0, "P": 40.0, "K": 40.0, "ph": 6.8}.items():
                    _set_default(f"cp_{k}", v)
                st.session_state.cp_soil_sig = ("card",)

        s1, s2, s3, s4 = st.columns(4)
        s1.number_input("Nitrogen (N)", min_value=0.0, max_value=300.0, step=1.0, key="cp_N")
        s2.number_input("Phosphorus (P)", min_value=0.0, max_value=300.0, step=1.0, key="cp_P")
        s3.number_input("Potassium (K)", min_value=0.0, max_value=400.0, step=1.0, key="cp_K")
        s4.number_input("Soil pH", min_value=3.0, max_value=10.5, step=0.1, format="%.1f", key="cp_ph")

        if st.button("🛰️ Estimate pH from soil map (SoilGrids)", key="cp_fetch_ph"):
            with st.spinner("Looking up soil map…"):
                try:
                    ph = _soil_ph(round(lat, 3), round(lon, 3))
                except Exception:
                    ph = None
            if ph:
                st.session_state.cp_ph = ph
                st.success(f"Soil map estimate for your location: pH {ph}. (Modelled estimate, 250 m resolution.)")
                st.rerun()
            else:
                st.info("No soil-map value for this exact spot (common in towns/water bodies). Keep your own value.")

    # ---------------- Step 3: climate ----------------
    with st.container(border=True):
        step_header(3, "Local climate (automatic)",
                    "Average of the last 3 years for your season, from ERA5 satellite/weather data for your ~10 km area.")
        climate, climate_error = None, None
        with st.spinner("Fetching climate for your farm…"):
            try:
                climate = _climate(round(lat, 2), round(lon, 2), season)
            except Exception as e:
                climate_error = str(e)

        sig = ("climate", round(lat, 2), round(lon, 2), season, climate is not None)
        if st.session_state.get("cp_climate_sig") != sig:
            src = climate or {"temperature": 25.0, "humidity": 65.0, "rainfall": 100.0}
            for k in ("temperature", "humidity", "rainfall"):
                _set_default(f"cp_{k}", float(src[k]))
            st.session_state.cp_climate_sig = sig

        if climate:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Avg temperature", f"{climate['temperature']} °C")
            m2.metric("Avg humidity", f"{climate['humidity']} %")
            m3.metric("Rain per month", f"{climate['rainfall']} mm")
            m4.metric("Rain per season", f"{climate['season_total_rain']} mm")
            recent = climate["recent"]
            st.caption(
                f"Seasons averaged: {', '.join(map(str, climate['years_used']))} · grid point "
                f"{climate['grid_lat']:.2f}, {climate['grid_lon']:.2f} · elevation {climate['elevation']:.0f} m · "
                f"last 30 days: {recent['temperature']} °C, {recent['rain_30d']} mm rain (up to {recent['until']})"
            )
        else:
            st.warning(f"Couldn't fetch climate automatically ({climate_error}). Please enter values below.")

        with st.expander("Adjust climate values", expanded=climate is None):
            k1, k2, k3 = st.columns(3)
            k1.number_input("Avg temperature (°C)", min_value=-10.0, max_value=55.0, step=0.5, key="cp_temperature")
            k2.number_input("Avg humidity (%)", min_value=0.0, max_value=100.0, step=1.0, key="cp_humidity")
            k3.number_input("Avg monthly rainfall (mm)", min_value=0.0, max_value=1500.0, step=5.0, key="cp_rainfall")

    inputs = {f: float(st.session_state[f"cp_{f}"]) for f in cm.FEATURES}

    # Safeguard: inputs outside what the model has learned
    oor = cm.out_of_range(inputs)
    if oor:
        lines = "\n".join(
            f"- **{cm.FEATURE_LABELS[f]}** = {v:g} (model trained on {lo:g}–{hi:g})" for f, v, (lo, hi) in oor)
        st.warning("⚠️ Some values are outside what the model has learned, so results are less reliable:\n" + lines)

    if st.button("🌱 Recommend crops", type="primary", use_container_width=True, key="cp_go"):
        model, encoder = _model()
        top, ranked = cm.recommend(model, encoder, inputs, season, include_perennial)
        st.session_state.cp_result = {
            "top": top, "ranked": ranked, "inputs": inputs, "season": season,
            "lat": lat, "lon": lon, "oor": bool(oor),
        }
        st.session_state.pop("cp_guide", None)

    result = st.session_state.get("cp_result")
    if not result:
        return

    # ---------------- Results ----------------
    st.markdown("### Recommended crops")
    top = result["top"]
    if not top:
        st.error("No crop in the model suits this season with these conditions. Try another season or check your inputs.")
        return

    best = top[0]["probability"]
    if best < 0.35 or result["oor"]:
        st.warning(
            "🔴 **Low confidence.** The model isn't sure about your conditions. Treat these as ideas to discuss "
            "with your local Krishi Vigyan Kendra (KVK) or agriculture officer, not as a final decision.")
    elif best < 0.6:
        st.info("🟡 **Medium confidence.** These crops fit reasonably well. Compare them with what grows well around you.")

    cols = st.columns(len(top))
    for i, (col, crop) in enumerate(zip(cols, top), start=1):
        level, icon = cm.confidence_level(crop["probability"])
        with col:
            crop_card(i, crop["name"], crop["probability"], level, icon, crop["seasons"])

    out_of_season = [r for r in result["ranked"][:5] if not r["in_season"] and r["probability"] >= 0.1]
    if out_of_season:
        st.caption("Not shown because they don't suit this season: " +
                   ", ".join(f"{r['name']} ({r['probability']:.0%})" for r in out_of_season))

    with st.expander("See how every crop scored"):
        shown = [r for r in result["ranked"] if r["probability"] > 0][:10]
        fig = go.Figure(go.Bar(
            x=[r["probability"] for r in shown][::-1],
            y=[r["name"] for r in shown][::-1],
            orientation="h",
            marker_color=["#2e7d32" if r["in_season"] else "#b0bec5" for r in shown][::-1],
            text=[f"{r['probability']:.0%}" for r in shown][::-1], textposition="auto",
        ))
        fig.update_layout(height=40 * len(shown) + 60, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(tickformat=".0%", range=[0, 1]))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Grey = doesn't suit the selected season.")

    # ---------------- Guide + audio ----------------
    with st.container(border=True):
        step_header(4, "Cultivation & irrigation guide", f"Spoken and written in {language}.")
        crop_choice = st.radio("Choose a crop", [c["name"] for c in top], horizontal=True, key="cp_guide_crop")
        chosen = next(c for c in top if c["name"] == crop_choice)
        if st.button(f"📖 Get guide for {crop_choice}", key="cp_guide_btn"):
            with st.spinner("Preparing your guide… (about 20–40 seconds)"):
                try:
                    st.session_state.cp_guide = _build_guide(
                        chosen["label"], result, language, together_api_key)
                except Exception as e:
                    st.error(f"Couldn't prepare the guide: {e}")

        guide = st.session_state.get("cp_guide")
        if guide:
            if guide.get("audio"):
                st.audio(guide["audio"], format=_assistant.audio_mime(guide["audio"]))
            elif not tts_available(LANGUAGES[guide["language"]]):
                st.info(f"Audio isn't available in {guide['language']} yet, the written guide is below.")
            st.markdown(f"#### {cm.crop_name(guide['crop'])} — {guide['language']}")
            st.write(guide["text"])
            if guide["language"] != "English":
                with st.expander("Show in English"):
                    st.write(guide["english"])


def _card_text(inp):
    """Soil test values the farmer entered, as a short phrase for the guide prompt ('' if none)."""
    from krishi import soilcard
    d = soilcard.describe(inp.get("card"))
    if not d:
        return ""
    return (", soil test values: " + d + ". Tailor the fertilizer advice to these values, but give no exact doses of "
            "chemicals; tell the farmer to get a soil-test based dose from the local KVK")


def _build_guide(crop_label, result, language, api_key):
    from together import Together

    inp = result["inputs"]
    prompt = (
        "You are an experienced Indian agronomist speaking to a small farmer in simple words. "
        f"Give a practical guide to grow {crop_label} in the {result['season']} season at latitude "
        f"{result['lat']:.2f}, longitude {result['lon']:.2f} in India. Local conditions: average temperature "
        f"{inp['temperature']} C, humidity {inp['humidity']}%, about {inp['rainfall']} mm rain per month, "
        f"soil pH {inp['ph']}{_card_text(inp)}. "
        "Cover, with short numbered points: 1) land preparation, 2) best sowing time, seed rate and spacing, "
        "3) fertilizer schedule for this soil, 4) irrigation: when and how much water at each crop stage, "
        "critical stages not to miss, and water-saving methods like drip or mulching, 5) main pests and diseases "
        "and low-cost control, 6) harvest time and signs. Use plain sentences. Do not use markdown, asterisks or tables. "
        "Keep it under 450 words."
    )
    client = Together(api_key=api_key)
    response, last_error = None, None
    for model_id in GUIDE_MODELS:  # Together retires serverless models; try in order
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=900,
                temperature=0.4,
            )
            if response.choices and response.choices[0].message.content:
                break
        except Exception as e:
            last_error = e
            response = None
    if response is None:
        raise RuntimeError(f"No guide model available ({last_error})")
    english = "".join(c.message.content for c in response.choices).replace("*", "").replace("#", "").strip()

    lang_code = LANGUAGES[language]
    translated = True
    if lang_code == "en":
        text = english
    else:
        try:
            text = _translate(english, lang_code)
        except Exception:
            text, lang_code, translated = english, "en", False   # translation busy: English text and voice instead

    try:
        audio = _assistant.speak(text, lang_code)
    except Exception:
        audio = None

    return {"crop": crop_label, "language": language, "text": text, "english": english, "audio": audio,
            "translated": translated}


def _translate(text, lang_code, chunk_size=1500):
    """Translate paragraph-by-paragraph to stay under the free translator's size limits.

    Calls Google Translate's public endpoint directly; the `googletrans` package
    is broken with current httpx/httpcore versions.
    """
    import requests

    def translate_chunk(chunk):
        import time
        for attempt in range(3):  # free endpoint rate-limits (HTTP 429)
            r = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "en", "tl": lang_code, "dt": "t", "q": chunk},
                timeout=20,
            )
            if r.status_code != 429:
                break
            time.sleep(1.5 * (attempt + 1))
        r.raise_for_status()
        return "".join(part[0] for part in r.json()[0] if part[0])

    chunks, current = [], ""
    for para in text.split("\n"):
        if len(current) + len(para) + 1 > chunk_size and current:
            chunks.append(current)
            current = ""
        current += para + "\n"
    if current.strip():
        chunks.append(current)
    out = []
    for chunk in chunks:
        if chunk.strip():
            out.append(translate_chunk(chunk))
    return "\n".join(out)
