"""Place lookup so farmers never have to type coordinates.

- search_places(): village / town name -> candidates with state & district (Open-Meteo geocoding, free).
- locate(): coordinates -> state & district (OpenStreetMap Nominatim reverse geocoding).
Both fail soft and return [] / None.
"""

import requests

HEADERS = {"User-Agent": "KrishiSahay/1.0 (farmer advisory app; contact via project owner)"}


def _clean_district(name):
    if not name:
        return None
    for suffix in (" District", " district", " Division"):
        name = name.replace(suffix, "")
    return name.strip()


def search_places(query, limit=8, timeout=10):
    if not query or len(query.strip()) < 2:
        return []
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query.strip(), "count": 20, "language": "en", "format": "json"},
            timeout=timeout,
        )
        r.raise_for_status()
        results = []
        for x in r.json().get("results", []):
            if x.get("country_code") != "IN":
                continue
            results.append({
                "label": ", ".join(p for p in [x["name"], _clean_district(x.get("admin2")), x.get("admin1")] if p),
                "lat": x["latitude"], "lon": x["longitude"],
                "state": x.get("admin1"), "district": _clean_district(x.get("admin2")),
            })
        return results[:limit]
    except Exception:
        return []


def locate(lat, lon, timeout=10):
    """Return {'state', 'district', 'place'} for coordinates, or None."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10, "accept-language": "en"},
            headers=HEADERS, timeout=timeout,
        )
        r.raise_for_status()
        a = r.json().get("address", {})
        if a.get("country_code") != "in":
            return None
        district = _clean_district(a.get("state_district") or a.get("county"))
        place = a.get("village") or a.get("town") or a.get("city") or a.get("county")
        return {"state": a.get("state"), "district": district, "place": place}
    except Exception:
        return None
