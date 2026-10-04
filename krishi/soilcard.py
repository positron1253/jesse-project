"""Soil Health Card values the farmer types in (from a soil test), with an APPROXIMATE Low / Medium / High reading.

The rating limits differ between sources and labs (for example available potassium "Low" is quoted as below 108,
120 or 135 kg/ha; available phosphorus "Low" as below 10 or 12.5 kg/ha), and depend on the test method. The limits
below are a common middle choice. Always trust the rating printed on the farmer's own card over this reading.

Nitrogen is available N by alkaline permanganate, phosphorus Olsen P, potassium ammonium-acetate K, all in kg/ha;
organic carbon in percent.
"""

# nutrient: (low_below, high_above, unit, label)
LIMITS = {
    "N": (280.0, 560.0, "kg/ha", "nitrogen"),
    "P": (10.0, 25.0, "kg/ha", "phosphorus"),
    "K": (120.0, 280.0, "kg/ha", "potassium"),
    "OC": (0.50, 0.75, "%", "organic carbon"),
}


def rate(nutrient, value):
    """'low' | 'medium' | 'high', or None if no value was entered (0 or empty means not entered)."""
    if value in (None, "", 0, 0.0):
        return None
    if isinstance(value, str):          # older sessions stored the level itself
        return value if value in ("low", "medium", "high") else None
    low, high, _, _ = LIMITS[nutrient]
    return "low" if value < low else "high" if value > high else "medium"


def describe(card):
    """Short English phrase for prompts: 'nitrogen 250 kg/ha (approximately low), ...' or '' if nothing entered."""
    parts = []
    for k, (_, _, unit, label) in LIMITS.items():
        v = (card or {}).get(k)
        r = rate(k, v)
        if r is None:
            continue
        parts.append(f"{label} {v} {unit} (approximately {r})" if not isinstance(v, str) else f"{label} {v}")
    return ", ".join(parts)
