"""Mandi prices and arrivals.

Primary source: CEDA Ashoka's open Agmarknet API (no key needed). It serves the
official DMI / Agmarknet data as monthly modal / min / max prices (Rs/quintal)
and arrivals (tonnes) by state and district.
  GET  /api/states, /api/commodities, /api/districts?state_id=
  POST /api/prices, /api/quantities
       {"state_id", "commodity_id", "district_id", "calculation_type": "m",
        "start_date", "end_date"}   (state_id 0 = All India)

Optional: data.gov.in daily mandi prices if DATA_GOV_IN_API_KEY is set in
st.secrets or the environment. Every call fails soft (returns None) so the app
keeps working on the offline snapshot.
"""

import os
import statistics
from datetime import date

import requests

CEDA = "https://agmarknet.ceda.ashoka.edu.in/api/"
DATA_GOV_RESOURCE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# crop_id -> CEDA commodity display name
CEDA_COMMODITY = {
    "rice": "Paddy(Dhan)(Common)", "wheat": "Wheat", "maize": "Maize", "jowar": "Jowar (Sorghum)",
    "bajra": "Bajra (Pearl Millet/Cumbu)", "ragi": "Ragi (Finger Millet)",
    "tur": "Arhar (Tur/Red Gram)(Whole)", "chana": "Bengal Gram (Gram)(Whole)",
    "moong": "Green Gram (Moong)(Whole)", "urad": "Black Gram (Urad Beans)(Whole)",
    "masoor": "Lentil (Masur)(Whole)", "soybean": "Soyabean", "groundnut": "Groundnut",
    "mustard": "Mustard", "sesame": "Sesamum (Sesame, Gingelly, Til)", "cotton": "Cotton",
    "sugarcane": "Sugarcane", "potato": "Potato", "onion": "Onion", "tomato": "Tomato",
    "brinjal": "Brinjal", "okra": "Bhindi (Ladies Finger)", "cauliflower": "Cauliflower",
    "cabbage": "Cabbage", "green_chilli": "Green Chilli", "bottle_gourd": "Bottle gourd",
    "garlic": "Garlic", "turmeric": "Turmeric", "coriander": "Coriander (Leaves)", "banana": "Banana",
}

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def parse_months(spec):
    """'Oct-Dec' -> [10, 11, 12]; 'Nov-Feb' wraps; 'Mar|Oct' -> [3, 10]."""
    out = []
    for part in str(spec).replace(",", "|").split("|"):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (MONTHS[x.strip()[:3].title()] for x in part.split("-", 1))
            m = a
            while True:
                out.append(m)
                if m == b:
                    break
                m = m % 12 + 1
        else:
            out.append(MONTHS[part[:3].title()])
    return out


class Ceda:
    def __init__(self, timeout=25):
        self.timeout = timeout
        self._states = self._commodities = None

    def _get(self, path, **params):
        r = requests.get(CEDA + path, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["data"]

    def _post(self, path, body):
        r = requests.post(CEDA + path, json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["data"]

    def state_id(self, state):
        if not state or state in ("*", "All India"):
            return 0
        if self._states is None:
            self._states = {s["census_state_name"].lower(): s["census_state_id"] for s in self._get("states")}
        return self._states.get(state.lower())

    def commodity_id(self, crop_id):
        if self._commodities is None:
            self._commodities = {c["commodity_disp_name"]: c["commodity_id"] for c in self._get("commodities")}
        return self._commodities.get(CEDA_COMMODITY.get(crop_id, crop_id))

    def district_id(self, state, district):
        sid = self.state_id(state)
        if not sid or not district:
            return None
        for d in self._get("districts", state_id=sid):
            if d["census_district_name"].lower() == district.lower():
                return d["census_district_id"]
        return None

    def monthly(self, kind, crop_id, state="*", district=None, start="2020-01-01", end=None):
        """kind = 'prices' or 'quantities'. Returns list of rows sorted by month."""
        body = {
            "state_id": self.state_id(state),
            "commodity_id": self.commodity_id(crop_id),
            "district_id": self.district_id(state, district) if district else None,
            "calculation_type": "m",
            "start_date": start,
            "end_date": end or date.today().isoformat(),
        }
        if body["commodity_id"] is None or body["state_id"] is None:
            return []
        return sorted(self._post(kind, body), key=lambda r: r["t"])


def harvest_price_range(rows, harvest_months):
    """From monthly price rows -> (lo, mid, hi, years) of the yearly harvest-month mean modal price."""
    months = set(harvest_months)
    by_year = {}
    for r in rows:
        y, m = int(r["t"][:4]), int(r["t"][5:7])
        if m in months and r.get("p_modal"):
            # Harvest seasons crossing New Year are grouped by the season's start year
            season_year = y - 1 if (min(months) > 6 and m < 6) else y
            by_year.setdefault(season_year, []).append(r["p_modal"])
    yearly = {y: statistics.mean(v) for y, v in by_year.items() if v}
    if len(yearly) < 2:
        return None
    vals = sorted(yearly.values())
    return round(vals[0]), round(statistics.median(vals)), round(vals[-1]), sorted(yearly)


def arrivals_anomaly(rows, months_back=2):
    """Compare the latest months' arrivals with the same months in earlier years.

    Returns ratio (e.g. 1.3 = 30% above normal) or None.
    """
    if not rows:
        return None
    latest = rows[-months_back:]
    ratios = []
    for r in latest:
        m = r["t"][5:7]
        past = [x["qty"] for x in rows if x["t"][5:7] == m and x["t"] < r["t"] and x.get("qty")]
        if past and r.get("qty"):
            ratios.append(r["qty"] / statistics.mean(past))
    return round(statistics.mean(ratios), 2) if ratios else None


def recent_modal(crop_id, state, district=None, ceda=None):
    """Latest monthly modal price for display ('mandi price last month'). None on any failure."""
    try:
        ceda = ceda or Ceda(timeout=10)
        rows = ceda.monthly("prices", crop_id, state, district, start=f"{date.today().year - 1}-01-01")
        if rows:
            last = rows[-1]
            return {"month": last["t"], "modal": round(last["p_modal"]), "min": round(last["p_min"]),
                    "max": round(last["p_max"]), "district": district if district else None}
    except Exception:
        pass
    return None


def data_gov_key():
    try:
        import streamlit as st
        key = st.secrets.get("DATA_GOV_IN_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("DATA_GOV_IN_API_KEY")


def fetch_today_datagov(state, commodity_name, limit=50, timeout=8):
    """Today's mandi prices from data.gov.in (needs key). None on failure."""
    key = data_gov_key()
    if not key:
        return None
    try:
        r = requests.get(DATA_GOV_RESOURCE, params={
            "api-key": key, "format": "json", "limit": limit,
            "filters[state]": state, "filters[commodity]": commodity_name,
        }, timeout=timeout)
        r.raise_for_status()
        return r.json().get("records") or None
    except Exception:
        return None
