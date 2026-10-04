"""Crop recommendation: model loading, soil inputs, safeguards and top-3 ranking."""

import pickle
import warnings

import numpy as np
import pandas as pd
import requests

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

# Min / max of each feature in the training data (Kaggle Crop Recommendation, 2200 rows).
# Inputs outside these ranges are extrapolation -> the model is guessing.
TRAIN_RANGES = {
    "N": (0, 140),
    "P": (5, 145),
    "K": (5, 205),
    "temperature": (8.8, 43.7),
    "humidity": (14.3, 100.0),
    "ph": (3.5, 9.9),
    "rainfall": (20.2, 298.6),
}

FEATURE_LABELS = {
    "N": "Nitrogen (N)",
    "P": "Phosphorus (P)",
    "K": "Potassium (K)",
    "temperature": "Avg temperature (°C)",
    "humidity": "Avg humidity (%)",
    "ph": "Soil pH",
    "rainfall": "Avg monthly rainfall (mm)",
}

# Typical values per Indian soil type, for farmers without a Soil Health Card.
# These are approximate averages - a soil test is always better.
SOIL_TYPES = {
    "Alluvial (Indo-Gangetic plains)": {"N": 80, "P": 45, "K": 40, "ph": 7.2},
    "Black / Regur (Deccan, cotton soil)": {"N": 40, "P": 30, "K": 80, "ph": 7.8},
    "Red (Tamil Nadu, Karnataka, Odisha)": {"N": 30, "P": 25, "K": 35, "ph": 6.2},
    "Laterite (Kerala, Konkan, NE hills)": {"N": 25, "P": 20, "K": 30, "ph": 5.5},
    "Sandy / Desert (Rajasthan)": {"N": 20, "P": 25, "K": 30, "ph": 8.0},
    "Mountain / Forest (Himalayan)": {"N": 70, "P": 50, "K": 45, "ph": 5.8},
}

# Crop display names (English + Hindi) and which Indian seasons they suit.
# "Perennial" = orchard / plantation crop, planted once and harvested for years.
CROP_INFO = {
    "rice":        {"name": "Rice (धान)",            "seasons": ["Kharif"]},
    "maize":       {"name": "Maize (मक्का)",          "seasons": ["Kharif", "Rabi", "Zaid"]},
    "chickpea":    {"name": "Chickpea (चना)",         "seasons": ["Rabi"]},
    "kidneybeans": {"name": "Kidney beans (राजमा)",    "seasons": ["Kharif", "Rabi"]},
    "pigeonpeas":  {"name": "Pigeon pea (अरहर/तूर)",    "seasons": ["Kharif"]},
    "mothbeans":   {"name": "Moth bean (मोठ)",         "seasons": ["Kharif"]},
    "mungbean":    {"name": "Mung bean (मूंग)",        "seasons": ["Kharif", "Zaid"]},
    "blackgram":   {"name": "Black gram (उड़द)",       "seasons": ["Kharif", "Zaid"]},
    "lentil":      {"name": "Lentil (मसूर)",          "seasons": ["Rabi"]},
    "cotton":      {"name": "Cotton (कपास)",          "seasons": ["Kharif"]},
    "jute":        {"name": "Jute (पटसन)",            "seasons": ["Kharif"]},
    "watermelon":  {"name": "Watermelon (तरबूज)",      "seasons": ["Zaid"]},
    "muskmelon":   {"name": "Muskmelon (खरबूजा)",      "seasons": ["Zaid"]},
    "pomegranate": {"name": "Pomegranate (अनार)",      "seasons": ["Perennial"]},
    "banana":      {"name": "Banana (केला)",          "seasons": ["Perennial"]},
    "mango":       {"name": "Mango (आम)",             "seasons": ["Perennial"]},
    "grapes":      {"name": "Grapes (अंगूर)",          "seasons": ["Perennial"]},
    "apple":       {"name": "Apple (सेब)",            "seasons": ["Perennial"]},
    "orange":      {"name": "Orange (संतरा)",          "seasons": ["Perennial"]},
    "papaya":      {"name": "Papaya (पपीता)",          "seasons": ["Perennial"]},
    "coconut":     {"name": "Coconut (नारियल)",        "seasons": ["Perennial"]},
    "coffee":      {"name": "Coffee (कॉफ़ी)",          "seasons": ["Perennial"]},
}


def crop_name(label):
    return CROP_INFO.get(label, {}).get("name", label.title())


def load_model(model_path="RandomForest.pkl", encoder_path="label_encoder.pkl"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # sklearn version warnings
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(encoder_path, "rb") as f:
            encoder = pickle.load(f)
    return model, encoder


def fetch_soil_ph(lat, lon, timeout=12):
    """Topsoil pH (0-5 cm) from ISRIC SoilGrids (250 m resolution, modelled estimate).

    Only pH is used - SoilGrids nitrogen is total N in g/kg, which is not the
    same scale as the N/P/K values the model was trained on.
    """
    resp = requests.get(
        "https://rest.isric.org/soilgrids/v2.0/properties/query",
        params={"lon": lon, "lat": lat, "property": "phh2o", "depth": "0-5cm", "value": "mean"},
        timeout=timeout,
    )
    resp.raise_for_status()
    layer = resp.json()["properties"]["layers"][0]
    value = layer["depths"][0]["values"]["mean"]
    if value is None:
        return None
    return round(value / layer["unit_measure"]["d_factor"], 1)


def out_of_range(inputs):
    """List of (feature, value, (lo, hi)) for inputs outside the training range."""
    issues = []
    for f in FEATURES:
        lo, hi = TRAIN_RANGES[f]
        if not lo <= inputs[f] <= hi:
            issues.append((f, inputs[f], (lo, hi)))
    return issues


def season_key(season_label):
    return season_label.split(" ")[0]  # "Kharif (Jun–Oct...)" -> "Kharif"


def recommend(model, encoder, inputs, season_label=None, include_perennial=True, top_n=3):
    """Rank crops for the given inputs.

    Returns (top, all_ranked) where each item is a dict with
    label, name, probability, seasons, in_season.
    `top` is restricted to crops that suit the season (if given).
    """
    X = pd.DataFrame([[inputs[f] for f in FEATURES]], columns=FEATURES)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        probs = model.predict_proba(X)[0]
    labels = encoder.inverse_transform(np.asarray(model.classes_))

    season = season_key(season_label) if season_label else None
    ranked = []
    for label, p in sorted(zip(labels, probs), key=lambda x: -x[1]):
        seasons = CROP_INFO.get(label, {}).get("seasons", [])
        in_season = (season is None or season in seasons
                     or (include_perennial and "Perennial" in seasons))
        ranked.append({
            "label": label,
            "name": crop_name(label),
            "probability": float(p),
            "seasons": seasons,
            "in_season": in_season,
        })
    top = [r for r in ranked if r["in_season"] and r["probability"] > 0][:top_n]
    return top, ranked


def confidence_level(p):
    if p >= 0.6:
        return "High", "🟢"
    if p >= 0.35:
        return "Medium", "🟡"
    return "Low", "🔴"
