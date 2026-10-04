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
| wheat | Rabi | 5 | 1,214 | 0.93 | 1,606 (-32%, -96 to -30) | 1.00 | 1,071 (+12%, -31 to +13) | 1.00 | 45 | 32 |
| chana | Rabi | 2 | 486 | 0.63 | 1,730 (-256%, -270 to -177) | 1.00 | 1,153 (-138%, -147 to -85) | 1.00 | -208 | -151 |
| mustard | Rabi | 2 | 486 | 0.66 | 2,149 (-343%, -437 to -253) | 1.00 | 1,433 (-195%, -258 to -135) | 1.00 | -295 | -214 |
| onion | Rabi | 12 | 2,914 | 0.75 | 3,486 (-20%, -30 to -1) | 0.96 | 2,324 (+20%, +13 to +33) | 0.96 | 184 | 134 |
| tomato | Rabi | 12 | 2,914 | 1.00 | 1,990 (+32%, +23 to +48) | 1.00 | 1,327 (+54%, +49 to +66) | 1.00 | 494 | 359 |
| cotton | Kharif | 6 | 1,457 | 1.00 | 1,017 (+30%, +21 to +100) | 1.00 | 678 (+53%, +47 to +100) | 1.00 | 243 | 176 |
| tur | Kharif | 2 | 486 | 0.86 | 1,188 (-145%, -266 to -139) | 1.00 | 792 (-63%, -144 to -59) | 1.00 | -96 | -69 |

**Reading it honestly**
- Where the baseline already waters enough (cotton, tomato, wheat with drip), scheduling and an efficient method cut water at equal yield.
- Where the usual practice is a deliberate shortcut (chana and mustard get about 2 irrigations and reach roughly 63–66% of full yield), the scheduler uses **more** water and lifts yield. That is a yield gain, not a water saving. Negative "saved" figures above mean extra water.

## 3. Sensitivity of the energy result to pump assumptions (cotton, Kharif, levers 1+2, per acre)

| Pump efficiency | Lift 30 m | Lift 40 m | Lift 60 m |
|---|---|---|---|
| 25% | 255 kWh (185 kg CO2) | 340 kWh (247 kg CO2) | 509 kWh (370 kg CO2) |
| 35% | 182 kWh (132 kg CO2) | 243 kWh (176 kg CO2) | 364 kWh (264 kg CO2) |
| 50% | 127 kWh (93 kg CO2) | 170 kWh (123 kg CO2) | 255 kWh (185 kg CO2) |

Energy scales with lift and inversely with efficiency, so the farmer's own pump details should replace these assumptions.

## 4. Crop choice on the same well: how much it moves water and money (Rabi, well lasts till March, per acre)

This is the size of the crop-choice lever, not a claimed saving: the farmer's alternative crop is not known.

| Crop | Irrigation m³ | Usual profit ₹ | Bad year ₹ | ₹ per m³ | Poor-yield seasons | Risk | Numbers estimated |
|---|---|---|---|---|---|---|---|
| coriander | 496 | -3,000 | -15,000 | -6 | 0% | high | yes |
| wheat | 1,071 | -5,000 | -14,000 | -5 | 0% | high | yes |
| maize | 1,111 | -9,000 | -22,000 | -8 | 0% | high | yes |
| chana | 1,153 | 9,000 | 3,000 | 8 | 0% | low | no |
| brinjal | 1,159 | 155,000 | 101,000 | 134 | 0% | medium | yes |
| green_chilli | 1,227 | 35,000 | -19,000 | 29 | 0% | medium | yes |
| jowar | 1,273 | -7,000 | -11,000 | -6 | 0% | high | no |
| cabbage | 1,284 | 7,000 | -13,000 | 5 | 0% | high | yes |
| tomato | 1,327 | 73,000 | -27,000 | 55 | 0% | high | yes |
| cauliflower | 1,393 | 28,000 | 3,000 | 20 | 0% | medium | yes |
| mustard | 1,433 | 10,000 | 6,000 | 7 | 0% | low | no |
| masoor | 1,507 | 22,000 | 16,000 | 15 | 0% | low | no |
| onion | 2,324 | -10,000 | -42,000 | -4 | 0% | high | yes |

## 5. Village roll-up (SYNTHETIC demo village, 40 farmers, 5 km radius, Rabi)

- Planned crop mix: **43,085 m³** of irrigation water in a usual year (40 irrigated acres).
- If every irrigated acre went to the *thriftiest* profitable crop for its water supply: 36,093 m³.
- If every irrigated acre went to the *thirstiest* profitable crop: 46,363 m³.
- The demo plans are random draws and say nothing about what real farmers grow; the point is that the roll-up exists and the range is wide. Water available per village is an input (Water Security Plan), so no gap is claimed here.

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
