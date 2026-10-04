# crops_v1.csv schema (one row per crop_id + state; state="*" = national default)

| column | type | meaning |
|---|---|---|
| crop_id | str | lowercase id, e.g. `soybean`, `green_chilli` |
| state | str | `*` (national default) or `Maharashtra` |
| name_en, name_hi, name_mr | str | display names (Devanagari for hi/mr) |
| category | str | cereal / pulse / oilseed / cash / vegetable / spice / fruit |
| seasons | str | `|`-separated subset of `Kharif|Rabi|Zaid` |
| sow_months | str | e.g. `Jun-Jul` |
| duration_days | int | sowing to (first) harvest |
| harvest_months | str | e.g. `Oct-Nov` |
| yield_q_acre_lo, yield_q_acre_hi | float | quintal per acre; lo ≈ poor/average-low year state yield, hi ≈ good year / progressive-farmer realistic. 1 t/ha = 4.047 q/acre; kg/ha ÷ 247.1 = q/acre |
| cost_rs_acre | int | paid-out cost + family labour (CACP A2+FL) per acre, latest year, inflated to 2026 if older (state why) |
| cost_est | 0/1 | 1 if cost is an estimate (no CACP figure) |
| price_q_lo, price_q_mid, price_q_hi | int | harvest-month modal mandi price ₹/quintal: worst / median / best of the last ~5 years |
| price_est | 0/1 | 1 if price range is estimated rather than read from Agmarknet/CEDA/official reports |
| msp_rs_q | int or empty | MSP 2026-27 (Kharif) / RMS 2026-27 (Rabi) ₹/q, empty if none |
| procurement | float 0-1 | realistic chance the farmer can actually sell at MSP in this state (0.2 default; Punjab paddy ~0.9; PM-AASHA pulses higher) |
| irrigations_needed | int | typical number of irrigations if not rain-fed (99 = needs assured irrigation all season, e.g. sugarcane/banana) |
| rainfed_ok_seasons | str | `|`-separated seasons in which it can be grown rain-fed (usually `Kharif` or empty) |
| tmin, topt_lo, topt_hi, tmax | float | season mean temperature limits °C (FAO ECOCROP absolute/optimal ranges) |
| ph_lo, ph_hi | float | optimal soil pH range |
| perishable | 0/1 | sold fresh within ~2 weeks of harvest |
| glut_prone | 0/1 | history of price crashes / TOP crop |
| loss_frac | float | post-harvest loss fraction (NABCONS 2022) |
| cluster_absorb_acres | int | rough acres a 50 km cluster can absorb without crashing local price (judgement; perishables small) |
| src_yield, src_cost, src_price, src_other | str | short citation with URL for each number group |
| as_of | str | date of the source data, e.g. `2025-26` |
