"""Tiny translation helper: t("key", **fmt). Strings live in krishi/locales/<lang>.json.

hi.json / mr.json are machine-translated from en.json by scripts/translate_locales.py
and should be reviewed by a native speaker before a field launch.
"""

import json
import os
from functools import lru_cache

import streamlit as st

LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locales")
UI_LANGUAGES = {"en": "English", "hi": "हिन्दी", "mr": "मराठी"}
# Guide language name used by the audio guide for each UI language
GUIDE_LANGUAGE = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


@lru_cache(maxsize=None)
def _strings(lang):
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def current_lang():
    if "lang" not in st.session_state:
        qp = st.query_params.get("lang")
        st.session_state.lang = qp if qp in UI_LANGUAGES else "en"
    return st.session_state.lang


def set_lang(lang):
    st.session_state.lang = lang
    st.query_params["lang"] = lang


def t(key, **fmt):
    text = _strings(current_lang()).get(key) or _strings("en").get(key) or key
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            text = (_strings("en").get(key) or key).format(**fmt)
    return text


def rupees(x):
    """Indian digit grouping: 120000 -> '1,20,000'."""
    neg = x < 0
    s = str(int(round(abs(x))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + s


def inr(x):
    """Signed rupee amount: 5000 -> '₹5,000', -5000 -> '-₹5,000'."""
    return ("-" if x < 0 else "") + "₹" + rupees(abs(x))
