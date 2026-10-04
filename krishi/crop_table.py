"""Seed crop table: agronomy + economics per crop and state, with citations.

crops_v1.csv          - curated, cited rows (see data/SCHEMA.md); built from crops_field.csv + crops_horti.csv
price_snapshot.csv    - harvest-month price ranges computed from official DMI/Agmarknet data (CEDA API),
                        overrides the curated price columns when present
district_crops.csv    - crops traded in a district's mandis (CEDA arrivals) -> coverage = "district"
"""

import os
from functools import lru_cache

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
NUMERIC = [
    "duration_days", "yield_q_acre_lo", "yield_q_acre_hi", "cost_rs_acre", "cost_est",
    "price_q_lo", "price_q_mid", "price_q_hi", "price_est", "msp_rs_q", "procurement",
    "irrigations_needed", "tmin", "topt_lo", "topt_hi", "tmax", "ph_lo", "ph_hi",
    "perishable", "glut_prone", "loss_frac", "cluster_absorb_acres",
]


def _path(name):
    return os.path.join(DATA_DIR, name)


@lru_cache(maxsize=1)
def load_crops():
    if os.path.exists(_path("crops_v1.csv")):
        df = pd.read_csv(_path("crops_v1.csv"))
    else:
        parts = [pd.read_csv(_path(f)) for f in ("crops_field.csv", "crops_horti.csv") if os.path.exists(_path(f))]
        if not parts:
            raise FileNotFoundError("No crop seed table found in krishi/data/")
        df = pd.concat(parts, ignore_index=True)
    df["crop_id"] = df["crop_id"].str.strip().str.lower()
    df["state"] = df["state"].fillna("*").str.strip()
    for c in NUMERIC:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("seasons", "rainfed_ok_seasons", "harvest_months"):
        df[c] = df[c].fillna("") if c in df else ""

    snap = _path("price_snapshot.csv")
    if os.path.exists(snap):
        s = pd.read_csv(snap)
        for _, r in s.iterrows():
            m = (df.crop_id == r.crop_id) & (df.state == r.state)
            if m.any() and pd.notna(r.price_q_mid):
                df.loc[m, ["price_q_lo", "price_q_mid", "price_q_hi"]] = [r.price_q_lo, r.price_q_mid, r.price_q_hi]
                df.loc[m, "price_est"] = 0
                df.loc[m, "src_price"] = r.src
    return df


@lru_cache(maxsize=1)
def _district_crops():
    p = _path("district_crops.csv")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["state", "district", "crop_id"])
    return pd.read_csv(p)


def all_crop_ids():
    return sorted(load_crops().crop_id.unique())


def crop_names(crop_id):
    df = load_crops()
    row = df[df.crop_id == crop_id].iloc[0]
    return {"en": row["name_en"], "hi": row.get("name_hi", row["name_en"]), "mr": row.get("name_mr", row["name_en"])}


def crops_for(state, season, district=None):
    """One row per crop for this state & season: state row if present else national default.

    Adds `coverage`: "district" (traded in the district's mandis), "state" (state data), "none" (national default only).
    """
    df = load_crops()
    rows = []
    dc = _district_crops()
    local = set()
    if district and len(dc):
        local = set(dc[(dc.state.str.lower() == str(state).lower()) &
                       (dc.district.str.lower() == str(district).lower())].crop_id)
    for crop_id, g in df.groupby("crop_id"):
        st_rows = g[g.state.str.lower() == str(state or "").lower()]
        row = (st_rows if len(st_rows) else g[g.state == "*"]).iloc[0].copy()
        if season not in row["seasons"].split("|"):
            continue
        if crop_id in local:
            row["coverage"] = "district"
        elif len(st_rows):
            row["coverage"] = "state"
        else:
            row["coverage"] = "none"
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)
