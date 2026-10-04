"""Location-specific climate data for crop prediction.

The crop model was trained on the Kaggle "Crop Recommendation" dataset, where
  - temperature = average temperature during the growing season (deg C)
  - humidity    = average relative humidity during the growing season (%)
  - rainfall    = average MONTHLY rainfall during the growing season (mm)

So we must NOT feed today's temperature or a 3-month rainfall total. Instead we
pull ERA5 reanalysis data from Open-Meteo (free, no API key) for the farmer's
exact coordinates (~9-11 km grid cell) and average the chosen season over the
last few complete years. That matches what the model learned from.
"""

from datetime import date, timedelta

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Indian cropping seasons -> calendar months
SEASONS = {
    "Kharif (Jun–Oct, monsoon)": [6, 7, 8, 9, 10],
    "Rabi (Nov–Mar, winter)": [11, 12, 1, 2, 3],
    "Zaid (Mar–Jun, summer)": [3, 4, 5, 6],
}

# Rough India bounding box, used to catch bad / default coordinates
INDIA_BOUNDS = {"lat": (6.0, 37.6), "lon": (68.0, 97.5)}


def current_season(today=None):
    """Return the season a farmer would be planning for right now."""
    m = (today or date.today()).month
    if m in (5, 6, 7, 8, 9):
        return "Kharif (Jun–Oct, monsoon)"
    if m in (10, 11, 12, 1):
        return "Rabi (Nov–Mar, winter)"
    return "Zaid (Mar–Jun, summer)"


def check_coordinates(lat, lon):
    """Return a list of human-readable problems with the coordinates (empty if fine)."""
    problems = []
    if lat is None or lon is None:
        return ["Your farm location is missing."]
    if abs(lat) < 0.01 and abs(lon) < 0.01:
        problems.append("Location is 0, 0 (GPS was probably blocked during registration).")
    elif not (INDIA_BOUNDS["lat"][0] <= lat <= INDIA_BOUNDS["lat"][1]
              and INDIA_BOUNDS["lon"][0] <= lon <= INDIA_BOUNDS["lon"][1]):
        problems.append(f"Location ({lat:.4f}, {lon:.4f}) is outside India.")
    return problems


def fetch_season_climate(lat, lon, season, years=3, timeout=15):
    """Average climate for `season` at (lat, lon) over the last `years` years.

    Returns a dict:
        temperature  - mean daily temperature in season (deg C)
        humidity     - mean daily relative humidity in season (%)
        rainfall     - mean MONTHLY rainfall in season (mm)   <- model's unit
        season_total_rain - mean total rain per season (mm), for display
        recent       - last ~30 days summary (for context only, not the model)
        years_used, grid_lat, grid_lon, elevation
    Raises requests.RequestException / ValueError on failure.
    """
    months = SEASONS[season]
    end = date.today() - timedelta(days=7)  # ERA5 has a ~5 day delay
    start = date(end.year - years - 1, 1, 1)

    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
            "timezone": "auto",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    daily = data.get("daily")
    if not daily or not daily.get("time"):
        raise ValueError("Weather service returned no data for this location.")

    # Group daily values by (year, month)
    by_month = {}
    for d, t, h, p in zip(daily["time"], daily["temperature_2m_mean"],
                          daily["relative_humidity_2m_mean"], daily["precipitation_sum"]):
        y, m = int(d[:4]), int(d[5:7])
        if m not in months:
            continue
        bucket = by_month.setdefault((y, m), {"t": [], "h": [], "p": [], "days": 0})
        bucket["days"] += 1
        if t is not None:
            bucket["t"].append(t)
        if h is not None:
            bucket["h"].append(h)
        if p is not None:
            bucket["p"].append(p)

    # Keep only (nearly) complete months, and only the most recent `years` of each month
    complete = {k: v for k, v in by_month.items() if v["days"] >= 26 and v["p"]}
    selected = []
    for m in months:
        keys = sorted((k for k in complete if k[1] == m), reverse=True)[:years]
        selected.extend(keys)
    if not selected:
        raise ValueError("Not enough historical weather data for this location.")

    temps = [x for k in selected for x in complete[k]["t"]]
    hums = [x for k in selected for x in complete[k]["h"]]
    monthly_rain = [sum(complete[k]["p"]) for k in selected]
    avg_monthly_rain = sum(monthly_rain) / len(monthly_rain)

    # Last 30 days, purely informational
    recent_t = [t for t in daily["temperature_2m_mean"][-30:] if t is not None]
    recent_p = [p for p in daily["precipitation_sum"][-30:] if p is not None]

    return {
        "temperature": round(sum(temps) / len(temps), 1),
        "humidity": round(sum(hums) / len(hums), 1),
        "rainfall": round(avg_monthly_rain, 1),
        "season_total_rain": round(avg_monthly_rain * len(months)),
        "recent": {
            "temperature": round(sum(recent_t) / len(recent_t), 1) if recent_t else None,
            "rain_30d": round(sum(recent_p)) if recent_p else None,
            "until": daily["time"][-1],
        },
        "years_used": sorted({k[0] for k in selected}),
        "grid_lat": data.get("latitude"),
        "grid_lon": data.get("longitude"),
        "elevation": data.get("elevation"),
    }
