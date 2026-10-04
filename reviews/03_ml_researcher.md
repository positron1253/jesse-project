# 03 — Applied ML researcher: data and recommender review

## 1. Diagnosis of the current model

- **The labels are the main problem, more than the algorithm.** `RandomForest.pkl` is a 20-tree `RandomForestClassifier`. It has no depth limit (trees are 11–17 deep, 2,768 nodes in total) and was trained on the Kaggle "Crop Recommendation" set: 2,200 rows, exactly 100 per crop, 22 crops. The rows carry no location, date, yield or price. The author's Kaggle description says the data was built by *augmenting* Indian rainfall, climate and fertiliser data, so the label means "a typical profile for this crop". It is not an observed outcome. Treat it as a semi-synthetic teaching dataset with no provenance. Nothing trained on it can be checked against reality.
- **The model gives the same answer almost everywhere.** I tested it with `py -3.11`, using the alluvial preset (`crop_model.py:37`, N80 P45 K40 pH7.2) at 30 °C. It predicts **coffee** for every rainfall from 50 to 250 mm/month at humidity 55–70%, and only moves to jute or rice at 85% humidity. This explains the Ludhiana and Thanjavur "coffee" results in CONTEXT.md. The soil-type presets put NPK close to the Kaggle coffee cluster.
- **There is a units mismatch.** `weather.py:60` feeds in ERA5 mean *monthly* rainfall on the assumption that Kaggle used the same unit. Kaggle never documents its rainfall unit, so the core feature mapping is guesswork.
- **Things the model leaves out:** irrigation (Punjab rice is ~100% irrigated), what the district actually grows, prices and costs. Its 22 classes cover less than half of India's cropped area: there is no wheat, sugarcane, mustard, soybean, bajra, jowar, potato, onion, tomato or spices. `confidence_level` (`crop_model.py:150`) shows an uncalibrated RF vote share as "confidence", and that misleads farmers.

**Verdict:** take the RF out of the ranking path completely (details in §5). Do not keep it even as a weak feature: its training data has no causal link to Indian outcomes, so adding it only adds noise.

## 2. Dataset verdict

Verification was done on 2026-10-03. My sandbox cannot reach some NIC-hosted APIs: `api.data.gov.in` refused the connection, and `desagri.gov.in` and `data.icrisat.org` timed out. Where that happened I verified through live mirrors or recent secondary listings, marked **Y\***. `upag.gov.in`, `agmarknet.gov.in`, `nhb.gov.in`, `soilhealth.dac.gov.in`, the IMD grid page, `gaez.fao.org` and `bhuvan.nrsc.gov.in` all returned HTTP 200.

| Dataset | URL | Access | Coverage | Granularity | Years | Verified | Role |
|---|---|---|---|---|---|---|---|
| **DES district APY** (Area-Production-Yield) | upag.gov.in → APY District; mirror dataful.in/datasets/5608 (UP) | Free CSV/XLSX download, Govt OGD terms | ~50 crops: cereals, pulses, oilseeds, cotton, jute, sugarcane, **potato, onion, garlic, sweet potato, tapioca, banana, dry chillies, turmeric, ginger, coriander, coconut** | **District × season × crop** | 1997-98 → 2024-25 | Y\* (UPAg live; Dataful lists 1997-98 to 2024-25 with 40 crops for UP) | **Backbone:** district cropping prior plus yield distribution |
| ICRISAT–TCI District Level Database | tci.cornell.edu/data, data.icrisat.org/dld | Free (open access) | 20 states, 571 districts. Major field crops A/P/Y, irrigated area by crop, farm harvest prices. Fruits and vegetables as **area totals** only | District (1966 boundaries, apportioned) | 1966–2017 | Y (TCI page live) | Irrigation-share-by-crop adjustment; long-run trends. Not for current boundaries |
| NHB / DA&FW Horticulture statistics | nhb.gov.in/statistics; agriwelfare.gov.in | Free PDF/XLS | All vegetables, fruits, spices, flowers | **State** × crop (no national district series) | 2011-12 → 2025-26 | Y | State-level vegetable yield and area trend; glut context |
| **Agmarknet mandi prices and arrivals** | agmarknet.gov.in; data.gov.in resource `9ef84268-d588-465a-a308-a864a43d0070` (current daily) | data.gov.in API, free key (official page notes the API sometimes needs a "Request API") | 300+ commodities, 4,549 markets (Jan 2025): min/max/modal price **and arrivals** | Mandi × variety × day | ~2003 → today | Y\* | Harvest-month price, volatility, oversupply |
| **CEDA Ashoka Agri Market** (cleaned Agmarknet) | agmarknet.ceda.ashoka.edu.in | Free download; **API with free key** (CEDA data portal) | 344 commodities, 650+ districts | Mandi/district, daily and monthly | 2000 → present, monthly refresh | Y (site live, data to Oct 2025) | **Preferred bulk price source** for the offline file |
| DES Cost of Cultivation / CACP price-policy reports | desagri.gov.in; cacp.da.gov.in | Free PDF/XLS | ~25 principal crops (incl. onion and potato in some states), A2, A2+FL, C2 ₹/ha | State × crop | 1996 → ~2022-23 | Y\* | Cost term. Vegetables need state horticulture or NHB model-project costs (manual) |
| Soil Health Card nutrient dashboard | soilhealth.dac.gov.in/nutrient-dashboard | Free CSV export | N, P, K, S, Zn, Fe, Cu, Mn, B, pH, EC, OC | State → district → block → village | 2015 → | Y (portal live) | District/block soil defaults to replace the presets at `crop_model.py:36` |
| FAO ECOCROP (inside GAEZ) | gaez.fao.org/pages/ecocrop-search; R `Recocrop` (1,710 taxa) | Free | Tmin/Topt/Tmax, rain, pH, duration | Crop-level ranges | static (no longer maintained) | Y | Agro-climatic suitability (hard filter) |
| FAO GAEZ v4 suitability rasters | gaez.fao.org | Free (check CC licence) | ~50 crops, rainfed vs irrigated | 5′ / 30″ grid | 1981–2010 baseline | Y | Later: a second suitability opinion |
| IMD gridded rainfall | imdpune.gov.in/cmpg/Griddata | Free NetCDF, cite Pai et al. 2014 | India daily rainfall | 0.25° | 1901–2024 | Y | Later: replace ERA5 rain (ERA5 is biased in monsoon orography) |
| ERA5 via Open-Meteo | archive-api.open-meteo.com | Free, no key | T, RH, rain | ~10 km | 1940 → | Y (already used) | Temperature and season climate |
| SoilGrids pH | rest.isric.org | Free API | pH, texture | 250 m (modelled) | static | Y (already used) | pH fallback |
| Bhuvan LULC | bhuvan.nrsc.gov.in | WMS, registration for downloads | Land use/cover | 1:50k | 2005-06 → | Y | Later: is the pin on cropland? |
| ICAR / SAU package of practices | icar.org.in, state agricultural universities | PDFs | Sowing windows, varieties, fertiliser | Agro-climatic zone | — | Partial (scattered) | Curated `crop_params.csv` and the LLM guide grounding |
| **Kaggle Crop Recommendation** | kaggle.com/datasets/atharvaingle/crop-recommendation-dataset | Free | 22 crops, 100 rows each | no location | none | Exists, **not valid** | **Drop** |

**Answer to the founder's question.** No single verified dataset covers all crops and vegetables at district level. The best verified combination is:
- **DES district APY (via UPAg)** for which crops a district grows and their yields. It includes potato, onion, garlic, chillies, turmeric, ginger and banana.
- **Agmarknet (via CEDA API or data.gov.in)** for prices and arrivals of every vegetable. Mandi arrivals also stand in for "is tomato or okra grown and traded near here", which no public district series covers.
- **NHB state horticulture statistics** for vegetable yields where APY has none.
- **Cost of Cultivation/CACP** for costs.
- **ECOCROP plus ICAR calendars** for agronomy.

## 3. Recommended architecture

Pipeline: (lat, lon) → district → candidates → yield → price → profit and risk → top-3.

1. **Locate the district.** Point-in-polygon on simplified district boundaries: datameet/maps or geoBoundaries ADM2, about 3 MB simplified. Then map names to APY names through a hand-checked `district_map.csv`, because district names drift and split over time.
2. **Candidate generation.** Each crop c gets two scores.
   - **Suitability**, ECOCROP-style trapezoid on each factor:
     `S_c = min(f_T(T_season), f_W(W_eff), f_pH(pH))`
     Effective water is `W_eff = rain_season + I`, where `I` = crop water need if the farmer says "canal/tubewell, full", 0.5 × need if "partial", and 0 if rainfed.
     Hard filters: `S_c ≥ 0.4`, and the crop's sowing month must fall in the chosen season (`crop_params.csv`).
   - **History prior** from APY, using the last 5 years for this district and season:
     `H_c = share of season area`. A crop counts as "verified local" if it was grown in ≥3 of the 5 years with area ≥ 200 ha.
     If it fails that test, check neighbouring districts (adjacency list). Vegetables with no APY entry count as local if the nearest 3 mandis report arrivals in ≥3 of the 5 years. Anything else is labelled "**new for your area — trial plot only**" and can never reach rank 1.
3. **Yield, in kg/acre.**
   - Base: `Ŷ = median(Y_{d,c,t-5..t-1}) × trend_adj`, from a Theil–Sen slope capped at ±3%/yr.
   - Irrigation: `× k_irr`. Take the ratio from DLD irrigated area share by crop. Example: rainfed farmer in a 95%-irrigated wheat district gives k ≈ 0.65, clipped to the range 0.5–1.0.
   - Band: P10/P90 from the empirical spread of detrended residuals over 10 years. Use NHB state yields for vegetables that have no APY data, and widen the band ×1.5.
   - Land area enters linearly, with a market-absorption check: if `area × Ŷ` exceeds 5% of the nearest mandi's harvest-month arrivals, warn about price impact.
   - Variety: v1 uses crop-level numbers only. The variety the farmer picks only changes the guide and the duration.
4. **Price.**
   - Harvest month: `m_h = sow_month + duration`.
   - Modal prices from the nearest k ≤ 5 mandis within 100 km, deflated by CPI.
   - `P̂ = median over 5 yrs of P_{m_h}` (CPI-adjusted to today), with P10/P90 across years.
   - MSP floor: `P̂ = max(P̂, MSP)` only for crops and states with real procurement (wheat and paddy in Punjab, Haryana, MP, Telangana, Chhattisgarh). Elsewhere MSP is shown but not assumed.
5. **Profit and risk, per acre.**
   `π = Ŷ·P̂·(1−loss_c) − C_c`
   - `C_c` = A2+FL cost (state, inflated to today). `loss_c` = post-harvest loss: 5% for grains, 15–25% for tomato and leafy vegetables.
   - Downside: `π_P10` from 200 bootstrap draws of paired (yield residual, price) years, so that correlations are kept.
   - Risk factors:
     - price CV in the harvest month (>0.35 = high);
     - **glut flag**: last season's arrivals are >25% above the 5-yr median *and* prices are trending down;
     - **sowing surge**: APY district area growth >20% year on year;
     - **in-app planned acreage**: the sum of farmers' committed acres for crop c within 50 km, from `polls.json` and the new plan records.
   - Rank by `U = E[π] − λ·max(0, −π_P10)`, with λ = 0.5, 1 or 2 for risk appetite high, medium or low. A farmer-facing "Risk: Low / Medium / High" uses P(π<0) < 10%, 10–30% or >30%.
   - When a vendor poll exists, swap `P̂` for the poll price, discounted for default risk.

## 4. Validation plan

The current app shows no validation numbers at all, so these are the gates:

- **Backtest split.** Build everything using data up to year t−1 and evaluate on year t, for t = 2019–2024. There must be no leakage of same-year APY or prices.
- **Crop-mix recall.** For each district and season, measure Recall@3 of the actual top-3 crops by area. The history prior makes this easy, so also run **leave-district-out**: hide the district's own APY and use only neighbours plus suitability. Target Recall@3 ≥ 0.7, and NDCG measured against area shares.
- **Yield.** District-crop MAPE of `Ŷ` against the realised yield. P10–P90 coverage should be 75–85%.
- **Price.** Predicted harvest-month price (made at sowing time) against the realised price. Report MAPE and band coverage separately for vegetables, which will be much worse.
- **Profit ranking.** Per district-year, Spearman between predicted and realised crop profits, plus regret against an oracle top-1. It must beat two baselines: "most-area crop" and "MSP crop".
- **Calibration.** Reliability plot of predicted P(π<0) against realised loss frequency. If it is off, apply isotonic recalibration, and show confidence only once calibrated.
- **Golden sanity tests** (pytest, run in CI): Ludhiana Kharif → rice/maize/cotton and Rabi → wheat. Thanjavur Kharif → rice. Nagpur Kharif → cotton/soybean/tur. Nashik Rabi → onion in the top 3. Kolar → tomato flagged as high risk.
- **Field check.** 20–30 farmers and one KVK scientist rate the top 3 blind.

## 5. Implementation plan

**What to do with the RandomForest:** remove the call at `crop_view.py:174-176`, and remove `TRAIN_RANGES`, `out_of_range` and `confidence_level` from the UI. Move `RandomForest.pkl` to `backup/`. Keep `fetch_soil_ph` and the soil inputs: they feed the pH suitability and the LLM fertiliser guide.

**New modules:**
```python
# krishi/geo.py
def locate_district(lat: float, lon: float) -> DistrictRef  # state, district, apy_key, neighbours
# krishi/data/loaders.py   (st.cache_resource; parquet)
def load_apy() -> pd.DataFrame; def load_crop_params() -> pd.DataFrame
def load_mandi_monthly() -> pd.DataFrame; def load_costs() -> pd.DataFrame; def load_msp() -> pd.DataFrame
# krishi/suitability.py
def suitability(crop: str, climate: dict, ph: float, irrigation: str) -> SuitScore  # score, limiting_factor
# krishi/history.py
def district_prior(d: DistrictRef, season: str, years: int = 5) -> pd.DataFrame  # crop, area_share, years_grown, y_p10, y_med, y_p90, trend, source
# krishi/prices.py
def harvest_price(crop: str, lat: float, lon: float, month: int, radius_km: int = 100) -> PriceEstimate  # p10, med, p90, cv, n_mandis, glut_flag, msp
def refresh_live_prices(crops: list[str]) -> None   # CEDA/data.gov.in, 24 h cache, silent fallback
# krishi/recommender.py
def recommend(lat, lon, season, irrigation, area_acres, soil=None, risk_appetite="medium", top_n=3) -> list[Recommendation]
# Recommendation: crop, profit_per_acre(med,p10,p90), yield_per_acre, price, cost, risk_level, reasons[list[str]], is_local_verified
```

**Shipped offline** (`krishi/data/`, about 15–25 MB in total):
- `apy_district.parquet` (all years, about 6 MB)
- `district_boundaries.geojson` (simplified)
- `district_map.csv`
- `crop_params.csv`: about 60 crops. ECOCROP ranges plus ICAR sowing/harvest months, duration, water need, loss factor, Hindi names.
- `crop_name_map.csv`: APY ↔ Agmarknet ↔ ECOCROP names
- `mandi_monthly.parquet`: commodity × mandi × month medians and arrivals, 2015 onwards
- `mandi_locations.csv`: geocoded once by hand or script, because Agmarknet has no coordinates
- `costs.csv`, `msp.csv`

**Fetched live:** ERA5 and SoilGrids (already cached) and the last 30 days of prices. When offline the app falls back to the shipped data and shows "prices as of <date>".

**v1, about 2 weeks:**
- Days 1–3: data pulls, name mapping, parquet build script (`scripts/build_data.py`).
- Days 4–6: suitability, history and yield.
- Days 7–9: prices and profit.
- Day 10: UI cards. Replace the probability shown by `crop_card` with ₹/acre, a P10–P90 range, a risk badge and three plain-language reasons.
- Days 11–12: backtest notebook and golden tests.

**Later:**
- IMD rainfall.
- GAEZ irrigated vs rainfed suitability.
- Block-level Soil Health Card defaults.
- Variety-level yields from state agricultural university trials.
- A LightGBM yield model on APY + weather + NDVI (Sentinel-2), with honest year-blocked CV.
- Price forecasting (seasonal ARIMA, or gradient boosting on arrivals and lagged prices).
- A crop-plan ledger so that planned acreage feeds the glut signal.
- A monthly automated data refresh.

## 6. Questions

- **CEO:**
  - Should we optimise for expected profit or for downside protection by default (λ)?
  - Can we commit someone to a monthly data refresh and to curating `crop_params.csv` with a KVK partner?
  - Is it acceptable to show "we don't know" for vegetables that have no local data?
- **Farmer:**
  - What irrigation do you have, and for how many months?
  - Where do you actually sell: which mandi or trader, and how far away?
  - Can you store produce?
  - How much loss could you survive in one season?
- **UI expert:**
  - How do we show a ₹ range and risk without false precision (for example "₹18k–32k per acre, Medium risk")?
  - How do we display "new for your area" warnings?
  - How do we take irrigation and area input in 2 taps and in audio?

Sources: [UPAg (Vikaspedia)](https://en.vikaspedia.in/viewcontent/agriculture/agri-directory/unified-portal-for-agricultural-statistics?lgn=en), [Dataful district APY (UP)](https://dataful.in/datasets/5608/), [Dataful horticulture master](https://dataful.in/datasets/19373), [TCI/ICRISAT DLD](https://tci.cornell.edu/data), [data.gov.in mandi resource](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi), [India Data Portal Agmarknet](https://ckandev.indiadataportal.com/dataset/apmc-arrivals-and-prices), [CEDA Agri Market](https://agmarknet.ceda.ashoka.edu.in), [Agmarknet MCP (CEDA API)](https://glama.ai/mcp/servers/Krishna-Baldwa/agmarket-mcp), [FAO ECOCROP](https://www.fao.org/geospatial/data-and-tools/data-portals/ecocrop/en), [Recocrop](https://cropmodels.r-universe.dev/Recocrop/doc/manual.html), [IMD gridded rainfall](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html), [Soil Health Card data](https://ckandev.indiadataportal.com/dataset/soil-health-card/resource/024cf507-4281-4c89-a40e-37b5add3a4df), [NHB statistics](https://www.nhb.gov.in/statistics/Publication/Horticulture%20Statistics%20at%20a%20Glance-2018.pdf).
