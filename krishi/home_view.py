"""Home screen: a few big icon tiles for the jobs a farmer actually has. Everything else is one tap from here."""

import streamlit as st

from krishi.i18n import UI_LANGUAGES, current_lang, set_lang, t

FARMER_TILES = [
    ("home.t_plan", "crop_prediction"), ("home.t_water", "water_energy"),
    ("home.t_ask", "assistant"), ("home.t_deals", "supply_commitments"),
    ("home.t_village", "village"), ("home.t_prices", "market_prices"),
    ("home.t_group", "communities"), ("home.t_tips", "farming_tips"),
]
VENDOR_TILES = [
    ("home.t_needs", "supply_commitments"), ("home.t_post", "vendor_post"),
    ("home.t_village", "village"), ("home.t_prices", "market_prices"),
    ("home.t_group", "communities"), ("home.t_tips", "farming_tips"),
]


def render(user, user_type):
    top = st.columns([4, 1])
    top[0].markdown(f"## 👋 {t('home.hello', name=user['name'])}")
    langs = list(UI_LANGUAGES)
    chosen = top[1].selectbox("🌐", langs, index=langs.index(current_lang()), format_func=UI_LANGUAGES.get,
                              key="home_lang", label_visibility="collapsed")
    if chosen != current_lang():
        set_lang(chosen)
        st.rerun()
    st.caption(t("home.title"))

    tiles = FARMER_TILES if user_type == "farmer" else VENDOR_TILES
    with st.container(key="home_tiles"):
        for i in range(0, len(tiles), 2):
            cols = st.columns(2)
            for col, (label_key, view) in zip(cols, tiles[i:i + 2]):
                if col.button(t(label_key), key=f"tile_{view}", use_container_width=True):
                    st.session_state.view = view
                    st.session_state.chat_community = None
                    st.rerun()
