# 13 — ML researcher: Round 2 response and FROZEN v1 spec

## 1. Agreements

- **The RandomForest leaves the decision path.** All four reviews agree on this. The CEO wanted it kept as a "filter", and I overrule that: the filter becomes the climate/water/pH ranges in the seed table described below.
- **Rank crops by money, not by model votes.** Show ₹ per acre for a normal year and for a bad year. Risk is a traffic light with a reason.
- **Use the CEO's score formula.** `S = π − λ(π − π_bad)` is the same as my risk-penalised utility, so I adopt it.
- **Four more points of agreement:**
  - Water is the first question the app asks.
  - Rainfed land and borewell land are planned separately.
  - The in-app planting registry plus vendor needs are the glut defence and the moat.
  - When we have no data for an area, the app says so on the card ("ask KVK") instead of showing a wrong #1.

## 2. Conflicts and my resolution

- **CEO's 25% cap and cluster quota vs my risk-penalised ranking.** These do different jobs, so we use both, in order:
  1. The score decides which crops come first.
  2. Caps and quotas decide how many acres each crop gets.
  3. Contracted area is allocated before both (see the A1–A5 algorithm in §4).
- **Planned acreage feeding the glut term, and the cold start.** With 5 users, "share planned" is noise, and a high share with no denominator would be false alarm. So:
  - The glut price cut only switches on once **at least 10 plans** for that crop exist within 50 km.
  - The denominator is a per-crop `cluster_absorb_acres` in the seed table, plus vendor-committed quantity.
  - Below 10 plans, the count is shown as information only ("6 farmers near you plan tomato") and does not change the price.
  - The static `glut_prone` flag (TOP crops, based on the 2025–26 crash evidence the CEO cited) carries the risk until then.
- **How to show P10/P90 to a farmer.** Our seed ranges are the bad and good harvest-month values of the last ~5 years, not modelled percentiles. Say exactly that:
  - "Normal year ₹28–36 hazaar/acre" (mid price × yield low–high).
  - "Worst of last 5 years: ₹–8,000" (low yield × low price).
  - No percentages. "Fits your land" is shown as 1–4 dots.
- **Rainfed vs borewell.** The farm becomes a list of `Plot`s, each with its own acres and water level:
  - `rain` = 0 irrigations, `till_dec` = 2, `till_mar` = 4, `all_year` = unlimited.
  - A crop is feasible on a plot if `irrigations_needed ≤ plot capacity` (or it is rainfed-OK in that season).
  - This reproduces Ramesh's rule: chana (2 irrigations) fits a well that lasts till March, wheat (5–6) does not.

## 3. Answers to questions put to me

- **CEO: replace the RF with a district prior plus a price model, and backtest π_bad against the 2023–26 crashes?** Yes, as v1.5. It needs the UPAg/Dataful APY CSVs and the CEDA monthly prices downloaded once. The backtest checks whether `glut_prone` crops got Medium/High risk in the crash seasons.
- **CEO: how to calibrate vendor demand when data is thin?** Count a poll quantity at 50% of face value (a Beta(2,2) prior on fulfilment). Update it per vendor from delivered/committed history.
- **Farmer: why show the model at all?** It should not have been shown. v1 ranks only crops that are grown in your state for that season, with rupee numbers.
- **Farmer: can the app predict a glut?** Not exactly. It uses three warnings: the crop's crash history (`glut_prone`), planned acres near you, and (in v1.5) mandi arrivals running above normal.
- **UI: a yield range and 4 buckets?** Yes. Yield lo–hi in quintal/acre, and `fit_dots` 1–4.
- **UI: how is low coverage flagged?** `coverage ∈ {"district", "state", "none"}`. With `"none"` the card is capped at 2 dots and shows the KVK line, and the crop can never be ranked #1.

## 4. FROZEN v1 spec (one engineer, about 1 day)

### Files to ship

**`krishi/data/crops_v1.csv`** has one row per (crop_id, state). `state="*"` is the national default; state rows override it. Launch with the 3 pilot states plus `*`.

| Column(s) | Content | Source to cite in `src_*` |
|---|---|---|
| crop_id, name_en, name_hi, name_mr | Crop IDs and names | — |
| seasons (`Kharif\|Rabi\|Zaid`), sow_month, duration_days | Crop calendar | ICAR/SAU package of practices |
| yield_q_acre_lo, yield_q_acre_hi | Yield range | DES *Agricultural Statistics at a Glance* / UPAg state yields; vegetables from NHB *Horticulture Statistics at a Glance*. Convert kg/ha → q/acre by ÷ 247 |
| cost_rs_acre | Cost per acre | CACP Price Policy reports (A2+FL); vegetables from NHB model-project or state horticulture department economics, marked `est` |
| price_q_lo, price_q_mid, price_q_hi | Harvest-month modal price (₹/q), worst / median / best of last 5 yrs | Agmarknet via the CEDA monthly download, nearest major mandi |
| msp_rs_q, procurement (0–1) | MSP and how reliably the state procures | CCEA/CACP 2026-27 (paddy 2441, wheat 2585, soybean 5708, cotton 8267, tur 8450, chana 5875). Procurement: 0.9 for Punjab/Haryana paddy & wheat, 1.0 for tur/urad/masoor under PM-AASHA, 0.2 default |
| irrigations_needed, rainfed_ok_seasons | Water need | ICAR / FAO-56 |
| tmin, topt_lo, topt_hi, tmax, ph_lo, ph_hi | Climate and soil ranges | FAO ECOCROP (GAEZ) |
| perishable, glut_prone, loss_frac, cluster_absorb_acres | Market risk inputs | CEO evidence and price CV; loss from NABCONS 2022 post-harvest loss study |
| src_yield, src_cost, src_price, as_of | Citation text per row | — |

**Crops (30):**
- Cereals: rice, wheat, maize, jowar, bajra, ragi.
- Pulses: tur, chana, moong, urad, masoor.
- Oilseeds: soybean, groundnut, mustard, sesame.
- Cash crops: cotton, sugarcane.
- Vegetables: potato, onion, tomato, brinjal, okra, cauliflower, cabbage, green chilli, bottle gourd.
- Spices: garlic, turmeric, coriander.
- Fruit: banana.

Every row must be filled by hand with a citation, and **no uncited numbers** are allowed. Rows where cost or price is marked `est` lose 1 fit dot.

**Optional `krishi/data/district_crops.csv`** (state, district, season, crop_id, area_ha) holds the 5-year mean from the Dataful/UPAg APY CSVs for pilot districts. If it exists, it sets coverage to "district" for crops grown on ≥200 ha.

**`plans.json`** is the new registry: farmer_id, lat, lon, season, crop_id, acres, harvest_month.

### Scoring (per plot, per crop)

```
Feasible if: season in seasons, AND (irrigations_needed <= cap(plot.water) OR season in rainfed_ok_seasons)
fit   = min(trap(T_season; tmin,topt_lo,topt_hi,tmax), trap(pH; ph_lo-0.5,ph_lo,ph_hi,ph_hi+0.5)); drop if fit < 0.3
dots  = 4 if fit>=.85, 3 if >=.65, 2 if >=.45, else 1; minus 1 if est; cap 2 if coverage=="none"
k_w   = 0.75 if crop is irrigated-normally but plot is rain/till_dec and still feasible, else 1.0
Y_lo, Y_hi = yield_lo*k_w, yield_hi*k_w ;  Y_mid = (Y_lo+Y_hi)/2
g     = 0 if n_plans<10 else clip(beta*max(0, planned_acres/(cluster_absorb_acres+vendor_q/Y_mid) - 1), 0, 0.5)
        beta = 0.3 if perishable else 0.1
floor = msp_rs_q * procurement
P_mid = max(price_q_mid*(1-g), floor);  P_bad = max(price_q_lo*(1-g), floor)
π_mid = Y_mid*P_mid*(1-loss) - cost ; π_bad = Y_lo*P_bad*(1-loss) - cost
normal range = [Y_lo*P_mid*(1-loss)-cost, Y_hi*P_mid*(1-loss)-cost]
S     = π_mid - λ*(π_mid - π_bad),  λ = 0.75 / 0.5 / 0.25 for risk appetite low / medium (default) / high
risk  = High if π_bad < -0.25*cost or (glut_prone and π_bad<0); Medium if π_bad<0 or (P_hi-P_lo)/P_mid>0.6; else Low
        (floor>=0.8*price_q_mid -> at most Medium). Each rule appends a reason string.
rank by S; coverage=="none" can never be #1.
```

### Allocation ("how much to grow")

- **A1.** Contracts first. For each accepted vendor commitment: acres = qty / Y_lo, placed on the best feasible plot, priced at the contract price.
- **A2.** For each plot, fill the remaining acres greedily in **0.5-acre steps** (0.25 if the plot is under 1 acre), in order of S. Each crop is limited by:
  - `cap_share × farm_acres`, where cap_share = 0.25 if glut_prone, 0.6 by default, 1.0 if procurement ≥ 0.8;
  - the cluster quota for glut_prone crops, `max(0, cluster_absorb_acres − planned_acres)`, once n_plans ≥ 10.
- **A3.** Use at most 3 crops per plot. Any area left over goes to the best uncapped crop (S > 0); if there is none, mark it "leave/fallow — ask KVK".
- **A4.** Output a `FarmPlan` with rows per plot (crop, acres, qtl lo–hi, ₹ normal range, ₹ worst), totals, and a warning when one crop exceeds 70% or exceeds nearby demand.
- **A5.** "Save plan" writes to `plans.json`, which feeds n_plans and planned_acres for everyone else.

### Signatures

```python
# krishi/crop_table.py
def load_crops(path="krishi/data/crops_v1.csv") -> pd.DataFrame
def crops_for(state: str, season: str, district: str | None = None) -> pd.DataFrame   # merged with "*" defaults, adds coverage

# krishi/recommender.py
@dataclass
class Plot: name: str; acres: float; water: Literal["rain","till_dec","till_mar","all_year"]
@dataclass
class CropOption: crop_id: str; name: str; plot: str; fit_dots: int; coverage: str
    yield_q_acre: tuple[float,float]; price_q: float; msp: float | None
    profit_normal: tuple[float,float]; profit_worst: float; score: float; risk: str; reasons: list[str]
def rank_crops(state, season, plot: Plot, climate: dict, ph: float, nearby: "NearbySignals",
               risk_appetite="medium", district=None, top_n=3) -> list[CropOption]
def allocate(plots: list[Plot], options: dict[str, list[CropOption]], contracts: list[dict],
             nearby: "NearbySignals") -> "FarmPlan"

# krishi/plans.py
def save_plan(farmer_id: str, lat: float, lon: float, season: str, plan: "FarmPlan") -> None
def nearby_signals(lat, lon, season, km=50) -> "NearbySignals"   # n_plans/planned_acres per crop, vendor qty from polls.json

# krishi/live_prices.py  (OPTIONAL; key from env/st.secrets DATA_GOV_IN_API_KEY)
def fetch_recent_modal(state: str, commodity: str, days=30, timeout=8) -> pd.DataFrame | None
# If >=3 records exist: show "today's mandi ₹X" beside the card. Never replaces price_q_mid in v1; failures are silent.
```

`climate` comes from the existing `weather.fetch_season_climate`. `ph` comes from the soil tile preset or SoilGrids. The state comes from the registration dropdown.
