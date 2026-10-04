"""Soil properties predicted from coordinates (for farmers who have no soil test).

Source: ISRIC SoilGrids 2.0 (250 m, machine-learning predictions) read from ISRIC's raster service (WCS). Their
point-query REST service returned empty values / timed out when tested, so we read a small window of pixels and take
the median of the valid ones (the service returns 0 where a pixel is missing).

What it gives:  pH, organic carbon %, clay / sand / silt %, USDA texture class, and the soil's water-holding capacity.
What it can NOT give: available nitrogen, phosphorus, potassium. Those need a soil test (or the Soil Health Card).
These are modelled estimates for a 250 m cell, not a measurement of the farmer's own field.
"""

import io
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests

WCS = "https://maps.isric.org/mapserv"
DEPTHS = [("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)]   # label, thickness cm (for depth weighting)
PROPS = ("phh2o", "soc", "clay", "sand", "silt")
HALF_DEG = 0.03       # about 3 km half-width; the service leaves gaps, so a wider window finds enough valid pixels
MIN_VALID = 3

# Water-holding capacity (mm of plant-available water per metre of soil) by USDA texture class.
# ASSUMPTION: middle of the FAO-56 Table 19 ranges for each texture (I could not read the full table).
TEXTURE_TAW = {
    "sand": 80, "loamy sand": 90, "sandy loam": 120, "loam": 155, "silt loam": 165, "silt": 180,
    "sandy clay loam": 135, "clay loam": 150, "silty clay loam": 155, "sandy clay": 130, "silty clay": 160, "clay": 160,
}


def usda_texture(sand, silt, clay):
    """USDA texture class from sand, silt, clay percentages."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 1.5 * clay < 30 and silt + 2 * clay >= 15:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    if clay >= 40:
        return "clay"
    return "loam"


def _window(prop, depth, lat, lon, timeout=40):
    from PIL import Image
    params = [("map", f"/map/{prop}.map"), ("SERVICE", "WCS"), ("VERSION", "2.0.1"), ("REQUEST", "GetCoverage"),
              ("COVERAGEID", f"{prop}_{depth}_mean"), ("FORMAT", "image/tiff"),
              ("SUBSET", f"long({lon - HALF_DEG},{lon + HALF_DEG})"), ("SUBSET", f"lat({lat - HALF_DEG},{lat + HALF_DEG})"),
              ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/4326")]
    r = requests.get(WCS, params=params, timeout=timeout)
    if r.status_code != 200 or "tiff" not in r.headers.get("content-type", ""):
        return None
    a = np.array(Image.open(io.BytesIO(r.content))).astype("float64")
    valid = a[a > 0]                      # 0 = missing in this service's output
    return (float(np.median(valid)), int(valid.size)) if valid.size >= MIN_VALID else None


def soil_from_coordinates(lat, lon):
    """Estimated topsoil (0-30 cm) properties, or None if the map has no usable data for this spot."""
    jobs = [(p, d, th) for p in PROPS for d, th in DEPTHS]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda j: _window(j[0], j[1], lat, lon), jobs))
    by_prop = {p: [] for p in PROPS}
    for (p, d, th), res in zip(jobs, results):
        if res:
            by_prop[p].append((res[0], th))

    def avg(prop, scale):
        vals = by_prop[prop]
        if not vals:
            return None
        return sum(v * w for v, w in vals) / sum(w for _, w in vals) / scale

    ph, soc = avg("phh2o", 10.0), avg("soc", 100.0)       # pH*10 -> pH; dg/kg -> %
    clay, sand, silt = avg("clay", 10.0), avg("sand", 10.0), avg("silt", 10.0)   # g/kg -> %
    if ph is None and clay is None:
        return None
    out = {"ph": round(ph, 1) if ph is not None else None, "oc_pct": round(soc, 2) if soc is not None else None,
           "clay": round(clay) if clay is not None else None, "sand": round(sand) if sand is not None else None,
           "silt": round(silt) if silt is not None else None, "texture": None, "taw_mm_per_m": None,
           "source": "SoilGrids 250 m (ISRIC)", "layers_found": sum(1 for p in PROPS if by_prop[p])}
    if None not in (clay, sand, silt):
        total = clay + sand + silt
        if total > 0:
            c, s, si = 100 * clay / total, 100 * sand / total, 100 * silt / total   # normalise: layers are medians of separate pixels
            out["texture"] = usda_texture(s, si, c)
            out["taw_mm_per_m"] = TEXTURE_TAW[out["texture"]]
    return out
