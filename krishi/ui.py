"""Shared styling and small render helpers for the Streamlit app."""

import streamlit as st

THEME_CSS = """
<style>
:root {
    --ks-green: #2e7d32;
    --ks-green-dark: #1b5e20;
    --ks-green-soft: #e8f5e9;
    --ks-amber: #f9a825;
    --ks-text: #1f2a1f;
    --ks-muted: #5f6b5f;
    --ks-border: #d7e3d7;
}
.stApp { font-family: 'Inter', 'Segoe UI', 'Noto Sans', sans-serif; }
.block-container { padding-top: 4.5rem; max-width: 1150px; }  /* clear Streamlit's fixed top bar */
header[data-testid="stHeader"] { background: rgba(247,250,247,0.92); backdrop-filter: blur(4px); }
.stDeployButton, [data-testid="stDeployButton"] { display: none; }

/* Hero banner */
.ks-hero {
    background: linear-gradient(120deg, var(--ks-green-dark), var(--ks-green) 60%, #558b2f);
    color: #fff; border-radius: 16px; padding: 22px 26px; margin-bottom: 18px;
}
.ks-hero h1 { color: #fff; font-size: 1.8rem; margin: 0 0 4px 0; padding: 0; }
.ks-hero p { color: #e8f5e9; margin: 0; font-size: 1rem; }

/* Cards */
.ks-card {
    background: #fff; border: 1px solid var(--ks-border); border-radius: 14px;
    padding: 16px 18px; margin-bottom: 12px; color: var(--ks-text);
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.ks-step {
    display: inline-block; background: var(--ks-green); color: #fff; border-radius: 999px;
    width: 28px; height: 28px; line-height: 28px; text-align: center; font-weight: 700;
    margin-right: 8px;
}
.ks-step-title { font-size: 1.15rem; font-weight: 700; color: var(--ks-text); }

/* Crop result cards */
.ks-crop {
    border-radius: 14px; padding: 16px; border: 2px solid var(--ks-border);
    background: #fff; color: var(--ks-text); height: 100%;
}
.ks-crop.rank-1 { border-color: var(--ks-green); background: var(--ks-green-soft); }
.ks-crop .rank { font-size: .8rem; font-weight: 700; color: var(--ks-muted); letter-spacing: .05em; }
.ks-crop .name { font-size: 1.35rem; font-weight: 800; margin: 4px 0; }
.ks-crop .meta { font-size: .9rem; color: var(--ks-muted); }
.ks-bar { background: #eceff1; border-radius: 999px; height: 10px; margin: 8px 0 4px 0; }
.ks-bar > div { background: var(--ks-green); height: 10px; border-radius: 999px; }

.ks-chip {
    display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem;
    font-weight: 600; margin-right: 4px; background: #eef3ee; color: var(--ks-green-dark);
}

/* Sidebar user box */
.user-info-box {
    background: var(--ks-green-soft); border-radius: 12px; padding: 14px;
    margin-bottom: 16px; border: 1px solid var(--ks-border); color: var(--ks-text);
}
.user-info-name { font-weight: 700; font-size: 1.05rem; }

/* Bigger, friendlier buttons (many farmers use phones) */
.stButton > button, .stFormSubmitButton > button { border-radius: 10px; min-height: 44px; font-weight: 600; }
div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(f"<div class='ks-hero'><h1>{title}</h1><p>{subtitle}</p></div>",
                unsafe_allow_html=True)


def step_header(number, title, help_text=None):
    st.markdown(f"<span class='ks-step'>{number}</span><span class='ks-step-title'>{title}</span>",
                unsafe_allow_html=True)
    if help_text:
        st.caption(help_text)


def crop_card(rank, name, probability, level, icon, seasons):
    chips = "".join(f"<span class='ks-chip'>{s}</span>" for s in seasons)
    pct = round(probability * 100)
    st.markdown(
        f"""
        <div class='ks-crop rank-{rank}'>
            <div class='rank'>#{rank} RECOMMENDATION</div>
            <div class='name'>{name}</div>
            <div class='ks-bar'><div style='width:{pct}%'></div></div>
            <div class='meta'>{icon} {level} match · {pct}% of model votes</div>
            <div style='margin-top:8px'>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
