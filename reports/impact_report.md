# Quantified benefit: reference-site simulation

*Generated 2026-10-04 by `scripts/run_impact.py`. Site: Yavatmal, Maharashtra (20.39, 78.13), black (vertisol) soil, 1995-2024 seasons of ERA5 weather. Every figure is a **simulation against a stated baseline, not field evidence**. Section 8 says how to validate it in a pilot.*

## 1. Baselines and what is being measured

| Item | Baseline (what the farmer does today) | Our approach |
|---|---|---|
| Irrigation timing | The crop's usual number of **flood irrigations on fixed dates** (package-of-practice count from the crop table), 60 mm gross each, no rain adjustment | Water when the soil needs it, using the 7-day forecast (lever 1) |
| Application method | Flood, 60% field efficiency | Drip / micro-sprinkler, 90% (lever 2, where suitable) |
| Crop choice | Not claimed as a saving. Section 4 shows how much the choice moves water and profit | Crops ranked on the farmer's own water supply |
| Pump | 40 m lift, 35% wire-to-water efficiency (assumptions, Section 3 tests others) | Same pump, fewer hours |
| Emissions | Grid 0.727 kg CO2/kWh (CEA v19, 2023-24) | Energy saved x grid factor |

## 2. Irrigation scheduling and method: water, energy, CO2 and yield (per acre, per season, 30 past seasons)

Yield is relative to the unstressed potential (1.00 = no water stress). A water saving only counts if yield holds.

| Crop | Season | Usual irrigations | Baseline water m³ | Baseline yield | Lever 1 water m³ (vs baseline, P10–P90) | Lever 1 yield | Levers 1+2 water m³ (vs baseline, P10–P90) | Levers 1+2 yield | kWh saved | CO2 saved kg |
|---|---|---|---|---|---|---|---|---|---|---|
| wheat | Rabi | 5 | 1,214 | 0.93 | 2,023 (-67%, -100 to -33) | 1.00 | 1,349 (-11%, -33 to +11) | 1.00 | -42 | -31 |
| chana | Rabi | 2 | 486 | 0.63 | 1,925 (-296%, -302 to -216) | 1.00 | 1,283 (-164%, -168 to -111) | 1.00 | -248 | -181 |
| mustard | Rabi | 2 | 486 | 0.66 | 2,428 (-400%, -408 to -317) | 1.00 | 1,619 (-233%, -239 to -178) | 1.00 | -353 | -257 |
| onion | Rabi | 12 | 2,914 | 0.75 | 3,486 (-20%, -30 to -1) | 0.96 | 2,324 (+20%, +13 to +33) | 0.96 | 184 | 134 |
| tomato | Rabi | 12 | 2,914 | 1.00 | 1,882 (+35%, +22 to +46) | 1.00 | 1,255 (+57%, +48 to +64) | 1.00 | 517 | 376 |
| cotton | Kharif | 6 | 1,457 | 1.00 | 1,214 (+17%, -14 to +44) | 1.00 | 809 (+44%, +24 to +63) | 1.00 | 202 | 147 |
| tur | Kharif | 2 | 486 | 0.86 | 1,214 (-150%, -325 to -67) | 1.00 | 809 (-67%, -183 to -11) | 1.00 | -101 | -73 |

**Reading it honestly** (generated from the table above)
- Water saved at equal or better yield (scheduling plus an efficient method): **onion** 20% less water (-20% with scheduling alone), yield +28% relative; **tomato** 57% less water (+35% with scheduling alone), yield +0% relative; **cotton** 44% less water (+17% with scheduling alone), yield +0% relative.
- Crops where the usual practice leaves the crop short of water, so the schedule uses MORE water to protect yield: **wheat** (water 11% more, yield +7% relative); **chana** (water 164% more, yield +59% relative); **mustard** (water 233% more, yield +51% relative); **tur** (water 67% more, yield +17% relative). That is a yield gain, not a water saving; a negative saved figure above means extra water.
- Each single watering is capped at 60 mm net (what a farmer can realistically apply), so deep-soil crops get more, smaller waterings.

## 3. Sensitivity of the energy result to pump assumptions (cotton, Kharif, levers 1+2, per acre)

| Pump efficiency | Lift 30 m | Lift 40 m | Lift 60 m |
|---|---|---|---|
| 25% | 212 kWh (154 kg CO2) | 282 kWh (205 kg CO2) | 423 kWh (308 kg CO2) |
| 35% | 151 kWh (110 kg CO2) | 202 kWh (147 kg CO2) | 302 kWh (220 kg CO2) |
| 50% | 106 kWh (77 kg CO2) | 141 kWh (103 kg CO2) | 212 kWh (154 kg CO2) |

Energy scales with lift and inversely with efficiency, so the farmer's own pump details should replace these assumptions.

## 4. Crop choice on the same well: how much it moves water and money (Rabi, well lasts till March, per acre)

This is the size of the crop-choice lever, not a claimed saving: the farmer's alternative crop is not known.

| Crop | Irrigation m³ | Usual profit ₹ | Bad year ₹ | ₹ per m³ | Poor-yield seasons | Risk | Numbers estimated |
|---|---|---|---|---|---|---|---|
| coriander | 496 | -3,000 | -15,000 | -6 | 0% | high | yes |
| maize | 1,079 | -9,000 | -22,000 | -8 | 0% | high | yes |
| green_chilli | 1,227 | 35,000 | -19,000 | 29 | 0% | medium | yes |
| brinjal | 1,243 | 155,000 | 101,000 | 125 | 0% | medium | yes |
| tomato | 1,255 | 73,000 | -27,000 | 58 | 0% | high | yes |
| chana | 1,283 | 9,000 | 3,000 | 7 | 0% | low | no |
| cabbage | 1,284 | 7,000 | -13,000 | 5 | 0% | high | yes |
| jowar | 1,349 | -7,000 | -11,000 | -5 | 0% | high | no |
| wheat | 1,349 | -5,000 | -14,000 | -4 | 0% | high | yes |
| cauliflower | 1,393 | 28,000 | 3,000 | 20 | 0% | medium | yes |
| masoor | 1,490 | 22,000 | 16,000 | 15 | 0% | low | no |
| mustard | 1,619 | 10,000 | 6,000 | 6 | 0% | low | no |
| onion | 2,324 | -10,000 | -42,000 | -4 | 0% | high | yes |

## 5. Village roll-up (SYNTHETIC demo village, 40 farmers, 5 km radius, Rabi)

## 6. Post-harvest loss at stake (value per acre, upper bound)

Loss share (NABCONS 2022, or marked estimate) x usual revenue. This is the most that buyers lined up before sowing could protect; **the actual reduction is a hypothesis to measure in the pilot**, not a result.

| Crop | Loss share | Revenue ₹/acre | Value at stake ₹/acre | Perishable |
|---|---|---|---|---|
| banana | 7.6% | 335,366 | 25,488 | yes |
| tomato | 11.6% | 213,095 | 24,719 | yes |
| brinjal | 8.0% | 231,302 | 18,504 | yes |
| green_chilli | 8.0% | 144,072 | 11,526 | yes |
| potato | 8.0% | 127,069 | 10,165 | no |
| garlic | 6.0% | 136,924 | 8,215 | no |
| sugarcane | 7.3% | 108,995 | 8,000 | no |
| cauliflower | 8.0% | 82,921 | 6,634 | yes |

## 7. Pump sizing for 2 acres (8 h window, 40 m lift, 35% pump efficiency)

| Crop | Method | Peak need mm/day | Smallest pump HP | Flow m³/h | Solar kWp |
|---|---|---|---|---|---|
| wheat | flood | 5.2 | 5 | 8.7 | 4.7 |
| wheat | drip | 5.2 | 3 | 5.8 | 2.8 |
| cotton | flood | 5.7 | 5 | 9.7 | 4.7 |
| cotton | drip | 5.7 | 3 | 6.5 | 2.8 |
| tomato | flood | 4.9 | 5 | 8.2 | 4.7 |
| tomato | drip | 4.9 | 3 | 5.5 | 2.8 |

Drip lets the same land run on a smaller pump and a smaller solar array. Subsidy (PM-KUSUM B: 30% central + 30% state, farmer 40%) applies to the system cost the farmer is quoted; payback uses the farmer's own tariff or diesel price.

## 8. Assumptions, what is verified, and how to validate

**Verified from published sources:** FAO-56 crop coefficients, root depths and depletion fractions; FAO-33 Ky for nine crops; IMD rain classes; grid emission factor (CEA v19, 2023-24, via a secondary summary); diesel 2.68 kg CO2/L (carbon-content derivation); PM-KUSUM B subsidy split (secondary).

**Assumptions, not verified:** soil water-holding capacity by soil class; stage lengths (20/25/30/25%); effective rain 85%; profile 10% depleted at sowing; 60 mm gross per flood irrigation; pump lift 40 m and efficiency 35%; Ky = 1.0 for crops without a verified value; array 1.25 kWp per kW of pump; vegetable cost and price figures marked estimated in the crop table.

**Not modelled:** waterlogging and flooding losses, heat stress, pests and disease, market price movements in the water results, groundwater recharge.

**Pilot validation plan:** in one cluster, give 20 farmers the schedule and 20 matched farmers none; fit a flow meter or hour-meter on each pump; log irrigations, hours, litres of diesel or kWh, and harvest weight per acre for one season; compare against the same farmers' previous season and against the matched group. Replace every assumption above with measured values.
