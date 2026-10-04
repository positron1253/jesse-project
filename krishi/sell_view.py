"""Sell tab: every open vendor need within 50 km (all crops, not just the farmer's chosen ones), future demand first.
The farmer filters, compares and commits quantity to a vendor with the same two-step confirmation as the plan screen."""

from datetime import date

import pandas as pd
import streamlit as st

from krishi import crop_table, location_ui, plans
from krishi.i18n import current_lang, inr, rupees, t
from krishi.plan_view import _agree_dialog

RADIUS_KM = 50


def _name(crop_id, fallback=""):
    if not crop_id:
        return (fallback or "?").title()
    try:
        return crop_table.crop_names(crop_id)[current_lang()]
    except Exception:
        return crop_id.replace("_", " ").title()


def _offers(lat, lon, known):
    """All open needs within 50 km with distance, crop and remaining quantity (quintals)."""
    vendors = {v["id"]: v for v in plans._load(plans.VENDORS_FILE)}
    out = []
    for poll in plans._load(plans.POLLS_FILE):
        if poll.get("status") != "open":
            continue
        v = vendors.get(poll["vendor_id"])
        if not v:
            continue
        d = plans.haversine_km(lat, lon, v["latitude"], v["longitude"])
        if d > RADIUS_KM:
            continue
        crop_id = poll.get("crop_id") or plans.to_crop_id(poll.get("product"), known)
        committed = sum(r.get("quantity", 0) for r in poll.get("responses", [])) * plans.TO_QUINTAL.get(str(poll.get("unit", "quintal")).lower(), 0)
        open_q = max(0.0, plans.poll_quantity_q(poll) - committed)
        if open_q <= 0:
            continue
        end = poll.get("delivery_to") or poll.get("deadline")
        out.append({**poll, "crop_id": crop_id, "distance_km": round(d, 1), "open_q": open_q, "end": end,
                    "start": poll.get("delivery_from") or poll.get("created_at", "")[:10]})
    return out


def render(user, respond_fn):
    st.caption(t("sell.sub"))
    location_ui.render_location(user)
    farm = st.session_state.get("farm") or {}
    lat, lon = farm.get("lat") or user.get("latitude"), farm.get("lon") or user.get("longitude")
    if lat is None:
        st.info(t("loc.need"))
        return
    known = set(crop_table.all_crop_ids())
    offers = _offers(lat, lon, known)
    today = date.today().isoformat()
    future = [o for o in offers if not o["end"] or o["end"] >= today]
    if not future:
        st.info(t("sell.none"))
        return

    # what the farmer already plans to grow
    mine = {}
    for r in plans.farmer_rows(user["id"]):
        mine.setdefault(r["crop_id"], 0.0)
        mine[r["crop_id"]] += (r.get("yield_q_lo", 0) + r.get("yield_q_hi", 0)) / 2

    # demand summary per crop
    by_crop = {}
    for o in future:
        c = by_crop.setdefault(o["crop_id"] or o.get("product"), {"crop": o["crop_id"], "label": _name(o["crop_id"], o.get("product")),
                                                                "buyers": 0, "qty": 0.0, "prices": [], "first": o["start"], "last": o["end"] or ""})
        c["buyers"] += 1
        c["qty"] += o["open_q"]
        if o.get("price_per_quintal"):
            c["prices"].append(o["price_per_quintal"])
        c["first"] = min(c["first"] or "9999", o["start"] or "9999")
        c["last"] = max(c["last"], o["end"] or "")
    st.markdown(f"**{t('sell.demand_title', km=RADIUS_KM)}**")
    st.dataframe(pd.DataFrame([{
        t("tbl.crop"): v["label"], t("sell.buyers"): v["buyers"], t("sell.qty"): round(v["qty"]),
        t("sell.price"): ((inr(min(v['prices'])) if min(v['prices']) == max(v['prices']) else f"{inr(min(v['prices']))}–{inr(max(v['prices']))}") if v["prices"] else t("buyer.no_price")),
        t("sell.window"): f"{v['first']} → {v['last']}" if v["last"] else v["first"],
        t("sell.my_plan"): (f"≈ {round(mine[v['crop']])} q" if v["crop"] in mine else "—")}
        for v in sorted(by_crop.values(), key=lambda x: -x["qty"])]), hide_index=True, use_container_width=True)

    # filters
    c1, c2 = st.columns([3, 2])
    labels = {k: v["label"] for k, v in by_crop.items()}
    pick = c1.multiselect(t("sell.filter_crop"), list(labels), format_func=labels.get, key="sell_crops")
    order = c2.selectbox(t("sell.sort"), ["price", "near", "soon"], format_func=lambda k: t(f"sell.sort_{k}"), key="sell_sort")
    shown = [o for o in future if not pick or (o["crop_id"] or o.get("product")) in pick]
    key = {"price": lambda o: -(o.get("price_per_quintal") or 0), "near": lambda o: o["distance_km"],
           "soon": lambda o: o["start"] or "9999"}[order]
    for o in sorted(shown, key=key):
        with st.container(border=True):
            h1, h2 = st.columns([3, 2])
            h1.markdown(f"### 🛒 {_name(o['crop_id'], o.get('product'))}")
            h1.write(t("buyer.line", vendor=o["vendor_name"], km=o["distance_km"], qty=round(o["open_q"]),
                       crop=_name(o["crop_id"], o.get("product"))))
            price = o.get("price_per_quintal")
            if price:
                h1.caption(t("buyer.terms", price=rupees(price), grade=o.get("grade", "FAQ"),
                             **{"from": o.get("delivery_from", o["start"]), "to": o.get("delivery_to", o["end"]),
                                "pickup": t("pk." + o.get("pickup", "vendor"))}))
            else:
                h1.caption(t("buyer.no_price"))
            if o["crop_id"] in mine:
                h2.info(t("sell.you_plan", q=round(mine[o["crop_id"]])))
            if h2.button(t("sell.commit"), key=f"sell_commit_{o['id']}", type="primary", use_container_width=True):
                _agree_dialog(o, o["crop_id"] or o.get("product", "?"), user, respond_fn)
            if st.session_state.get("dlg_done") == o["id"]:
                poll_now = next((p for p in plans._load(plans.POLLS_FILE) if p["id"] == o["id"]), {})
                code = next((r.get("reference_code") for r in poll_now.get("responses", []) if r["farmer_id"] == user["id"]), "")
                st.success(t("dlg.done", code=code))
