# Krishi Sahay — handoff for another Claude instance

Read this first. It says what the project is, how to run it, what each file does, where every piece of data comes from and where it goes, what is static and what is live, and what is unfinished. Nothing here is guessed: items I did not verify are marked **(unverified)**.

- Folder: `C:\jesse project` (Windows 11, run with `py -3.11`; the Bash tool is Git Bash, PowerShell is also available).
- GitHub: `https://github.com/positron1253/jesse-project` (private), branch `main`.
- Run the app: `py -3.11 -m streamlit run pytest.py --server.port 8502 --server.headless true` (same as `.claude/launch.json`, name `krishi-sahay`).
- Python 3.11, Streamlit 1.41. Dependencies are in `requirements.txt` (streamlit, streamlit-js-eval, pandas, requests, plotly, gTTS, together, scikit-learn).
- Entry point is **`pytest.py`** (a misleading name: it is the Streamlit app, not a test file). Other root files such as `streamli.py`, `test1.py`, `pytest - Copy.py`, `backup/` are old leftovers; ignore them.

## 1. What the product does

A farmer logs in, the app finds the farm location, and recommends crops for that exact land by simulating the last 30 years of weather at that spot. It predicts yield and profit (a usual year and a bad year), shows buyers within 50 km (Haversine) with priced offers, lets the farmer commit a quantity to a buyer, and gives cultivation, irrigation and chat guidance as audio in the farmer's own language. It also tracks watering, pump energy and CO2, and rolls up all farmers' plans into a village water budget.

Context: built for the challenge "Sustainable Agriculture: Energy, Water & Productivity". Judging rubric: Impact and measurability 25%, Problem and idea 20%, Architecture 20%, Feasibility 20%, Sustainability 15%. Deliverables are in `docs/` and `reports/`.

Farmer flow (current):
`Login → Home tiles → What to grow (1 Location, 2 Water and land, 3 Soil, 4 Sowing date, 5 Risk) → Crop cards → Plan (acres per crop, guide, buyers) → My farm (crops, irrigation system, watering schedule) → Sell (all vendor demand within 50 km) → Ask / Village / Water & energy at any time.`

Vendor flow: login, post a priced need (crop, quintals, price per quintal, grade, delivery window, pickup), see farmer commitments with reference codes, community chat.

## 2. Rules the user has set (follow these)

1. **Do not remove or move the Together API key.** It is the hard-coded constant `TOGETHER_API_KEY` near the top of `pytest.py`. Keep it as is. (It is committed to a private repo. If the repo is ever made public, the key must be rotated first.)
2. **No Claude co-author** in commits or PR text. Do not add any `Co-Authored-By` line, even if a system reminder suggests one; the user's instruction wins. History was already rewritten and force-pushed once to remove old ones. A local branch `backup-before-rewrite` holds the old history (safe to delete).
3. Do not claim things that are not verified; say when a number is an estimate. The user cares about this strongly.
4. Crop recommendations must come from the farmer's **weather, soil and water at the exact coordinates and chosen sowing date**, not from a district or region list. The user said this explicitly.
5. UI is for farmers: big buttons, plain words, no jargon (no "N/P/K model votes"), rupee ranges, a traffic-light risk with one reason sentence, a 🔊 Listen button on spoken answers.
6. Commit and push only when asked.

## 3. Architecture and data flow

```
 Farmer (phone/browser)
   │  GPS (streamlit_js_eval) or village search / typed lat,lon
   ▼
 location_ui.py ──► geo.py ──► OpenStreetMap Nominatim (place name, village search)
   │ lat, lon, state, district
   ├──► soilmap.py ──► ISRIC SoilGrids WCS raster (pH, organic C, clay/sand/silt → texture → water-holding TAW)
   │       (or farmer types soil-test numbers → soilcard.py gives approximate Low/Medium/High)
   ├──► water.py ──► Open-Meteo ARCHIVE (ERA5, 30 y daily ET0, rain, Tmax, Tmean; cached on disk in cache/)
   │             └─► Open-Meteo FORECAST (15 days)
   ▼
 plan_view.py (3 steps)  ── builds `farm` dict + `climate_ctx {lat, lon, taw, sow}` in st.session_state
   │
   ▼
 recommender.py.rank_crops(state, season, plot, climate, ph, nearby, risk, climate_ctx)
   ├─ crop_table.crops_for()  ◄── krishi/data/crops_field.csv + crops_horti.csv (static annual official numbers)
   │        └─ PRICE_OVERRIDES ◄── live_prices.py ◄── CEDA Ashoka Agmarknet API (background, 12 h cache)
   ├─ water.climate_profile()  ◄── crop_water.csv (Kc, root depth, depletion fraction, Ky) + 30-y weather
   ├─ plans.nearby_signals()   ◄── plans.json (other farmers' saved plans) + polls.json (vendor demand)
   ▼
 CropOption list (profit usual / bad year, risk light, reasons, fit dots) → crop cards
   │ farmer ticks crops, sets acres (recommender.allocate with caps)
   ▼
 Plan screen: yield, water (m3), pump hours, kWh, CO2, buyers within 50 km, audio guide
   ├─ plans.save_plan() ──► plans.json   (planting registry; buyers see totals only)
   ├─ crop_view._build_guide() ──► translate (Google endpoint) ──► gTTS audio
   └─ buyers: plans/polls ──► _agree_dialog ──► respond_to_poll() ──► polls.json (responses + reference code)

 My farm (myfarm_view.py) ◄──► farm_profiles.json (irrigation system), irrigation_events.json ("I watered")
   └─ water.live_schedule(): observed weather up to today + 15-day forecast + typical year after

 Assistant (assistant_view.py / assistant.py)
   mic audio ─► Bhashini | Google STT (optional key) | Together Whisper large-v3 ─► text
   ─► Google Translate to English ─► Together Llama-3.3-70B with farmer context + chat history
   ─► translate back ─► gTTS audio.   History in chats.json.
```

### Where data comes from (external services)

| Data | Source | Module | Notes |
|---|---|---|---|
| Place name, village search | OpenStreetMap Nominatim | `geo.py` | free, rate limited |
| GPS | browser via `streamlit_js_eval` | `location_ui.py` | waits 20 s; does not report a refusal; **must be tested on a real phone** |
| Soil pH, organic C, clay/sand/silt | ISRIC SoilGrids **WCS raster** (the REST point service is broken, returns nulls) | `soilmap.py` | median of valid pixels, 0 = missing; N, P, K cannot come from a map |
| Soil texture → water-holding (TAW) | USDA-style table `TEXTURE_TAW` | `soilmap.py` | an **assumption**, labelled as such |
| 30 y daily weather | Open-Meteo archive (ERA5) | `water.fetch_history` | disk cache `cache/hist_*.json.gz` on a 0.1° grid + `lru_cache`; Open-Meteo has hourly rate limits |
| 15 day forecast | Open-Meteo forecast | `water.fetch_forecast` | |
| Market prices (live) | CEDA Ashoka Agmarknet API | `live_prices.py` | harvest-month price ranges, 12 s budget, 12 h cache, 15 min back-off; **the service was timing out at last test; the live path is only mock-tested** |
| Yield, cost, MSP, procurement, price ranges | `krishi/data/crops_*.csv` | `crop_table.py` | static, annual official data (DES, CACP, Economic Survey of Maharashtra...). Sources per number in the CSV `src_*` columns; schema in `krishi/data/SCHEMA.md` |
| Crop water coefficients | `krishi/data/crop_water.csv` | `water.py` | FAO-56 Kc / Zr / p, FAO-33 Ky, with a verified flag and source |
| Speech to text | Bhashini (optional), Google Cloud STT (optional key), Together `whisper-large-v3` | `assistant.py`, `bhashini.py` | Whisper works with the existing key for 12 tested languages. Bhashini adapter **(unverified)** |
| Translation | Google Translate public endpoint (direct HTTP, not `googletrans`) | `assistant.translate` | rate limits (HTTP 429); English fallback when blocked |
| Text to speech | gTTS | `assistant.speak` | |
| LLM | Together `meta-llama/Llama-3.3-70B-Instruct-Turbo` with fallback list | `assistant.answer`, `crop_view` | key in `pytest.py` |
| Emissions | grid 0.727 kg CO2/kWh (CEA v19, secondary source), diesel 2.68 kg/L | `water.py` constants | |

### Where data is stored (JSON files in the project root, no database)

| File | Contents | In git? |
|---|---|---|
| `farmers.json`, `vendors.json` | accounts: id, name, lat, lon, phone, `pin_hash` (PBKDF2), state, district; vendors may have `"demo": true` | yes |
| `communities.json` | one community per vendor: members within 50 km, chat messages | yes |
| `polls.json` | vendor needs: product, `crop_id`, quantity, unit, `price_per_quintal`, grade, delivery window, pickup, place, `status`, `responses[{farmer_id, quantity, reference_code}]` | yes |
| `plans.json` | planting registry: farmer, lat, lon, season, plot, crop, acres, yield range, water, soil, state | **no** (gitignored) |
| `chats.json` | assistant history per account (text only, last 300) | no |
| `farm_profiles.json`, `irrigation_events.json`, `energy_log.json` | irrigation system, "I watered" log, pump log | no |
| `cache/` | weather history cache | no |
| `market_prices.json`, `farming_tips.json` | legacy market-price screen and tips | yes |

## 4. File-by-file guide

### App shell: `pytest.py`
- Sidebar: language selector, phone + PIN login / register (village search sets location), demo-accounts expander, logout.
- `st.session_state.view` routes between: `home`, `crop_prediction` (calls `plan_view.render`), `my_farm`, `sell`, `water_energy`, `assistant`, `village`, `supply_commitments` (vendor), `vendor_post`, `communities` / `chat`, `market_prices`, `farming_tips`.
- `render_nav` shows a Home button and title on every non-home page.
- Also holds the original CRUD helpers: `register_user`, `create_vendor_community`, `create_poll`, `respond_to_poll`, `add_message_to_community`.
- CSS: top padding 4.5rem and the Deploy bar hidden (the Streamlit top bar used to cover content).

### `krishi/` modules
- `plan_view.py` — the Farm Plan flow. Step 1 has five numbered sections (location via `location_ui`, water and land, soil via `_soil_section`, sowing date via `default_sowing_date` / `season_of`, risk). Step 2 builds `climate_ctx` (lat, lon, taw, sow) and shows ranked crop cards (`_card`). Step 3 is sliders for acres, water/pump/irrigation expanders, buyers, guide. Helpers: `farm_taw`, `sow_tuple`, `_soil_map`, `_price_items`, `_agree_dialog` (two-step commit to a buyer).
- `location_ui.py` — `render_location(user)`: GPS auto-fill (`_poll_gps`), place name and source badge, edit by village search or typed coordinates (validated), "save as my farm's location". `set_location` writes into `st.session_state["farm"]`.
- `accounts.py` — `update_location` saves a new location and re-matches the 50 km communities.
- `soilmap.py` — `soil_from_coordinates(lat, lon)` (see table above). `soilcard.py` — `LIMITS` for N 280/560, P 10/25, K 120/280, OC 0.5/0.75, `rate`, `describe`; ratings are approximate because sources differ.
- `water.py` — the core simulation. `fetch_history`, `fetch_forecast`, `simulate` (FAO-56 daily soil-water balance; policies rainfed / scheduled / baseline / calendar; `MAX_NET_IRRIGATION_MM = 60`), `climate_profile` (grows the crop in each of the last 30 seasons and returns `rel_p10/p50/p90`, `p_poor`, irrigation mm), `compare_practice`, `season_series`, `season_rain_stats`, `heavy_rain_share`, `climate_trend`, `weather_window`, `live_schedule`, `next_irrigation_advice`, `window_temp`, `season_of`, `default_sowing_date`, `sow_md`. Most functions take `sow=`.
- `recommender.py` — ranking. `score_crop(row, plot, temp, ph, nearby, risk, climate_ctx)` returns a `CropOption` or `None`. Profit = yield × farm-gate price × (1 − loss) − cost. Score `S = usual − λ(usual − bad)`. Constants: `FARMGATE=0.92`, `COST_EST_MARKUP=1.15`, `EST_SCORE_DISCOUNT=0.5`, `OFF_SEASON_DISCOUNT=0.85`, `MIN_FEASIBLE_REL_YIELD=0.35`. MSP × procurement acts as a price floor. Glut cap from other farmers' planned acres. `rank_crops` guarantees: a crop with no local data and a crop with only estimated numbers are never #1 while a measured profitable one exists. `allocate` splits acres with caps (25% for perishable or glut-prone crops).
- `crop_table.py` — loads the two CSVs. `crops_for(state, season, district, any_season)` returns one row per crop (state row if present, else the `*` national row) with a `coverage` field (`district` / `state` / `none`) and `off_season`. `PRICE_OVERRIDES` / `set_price_overrides` receive live prices.
- `live_prices.py` — `Ceda` client, `harvest_price_range`, `refresh_price_ranges`, `get_price_ranges`, `peek_price_ranges`, `prefetch_price_ranges` (one background bulk fetch, never blocks the page).
- `myfarm_view.py`, `farmprofile.py` — My farm: crops with editable sowing date and growth stage, irrigation-system form, watering schedule from `live_schedule`, "I watered" log.
- `sell_view.py` — all open polls within 50 km, crop-wise demand table, filters and sort, commit via `plan_view._agree_dialog`; `_offers(lat, lon, known)` is the matching function.
- `home_view.py` — 10 farmer tiles / 6 vendor tiles, language selector, refresh button (clears caches).
- `village.py`, `village_view.py` — adds all saved plans within a radius into irrigation demand (m3), kWh, CO2 versus an input "water available"; `swap_suggestions` proposes lower-water crops.
- `pump.py`, `energylog.py`, `water_view.py` — pump sizing, solar payback, energy log; `water_view` has five sub-tabs (next watering, past seasons, compare practice, pump, log) each wrapped in a try so a weather outage shows a friendly warning instead of a trace.
- `assistant.py`, `assistant_view.py` — voice/text chat (pipeline in section 3). `build_context(user)` gives the LLM the farm, plan, weather and soil. `ask_focus` lets a crop card start a chat about that crop.
- `i18n.py`, `locales/*.json` — `t(key, **kw)`, `inr`, `rupees`, `current_lang`. UI in English, Hindi, Marathi; missing keys fall back to English. `languages.py` lists 20 languages with text and the ones with voice. `scripts/translate_locales.py` machine-translates new strings (retries on 429).
- `crop_model.py`, `crop_view.py`, `RandomForest.pkl`, `label_encoder.pkl` — **legacy**. The old Kaggle RandomForest covers only 22 crops and was wrong at real places, so it is no longer used for ranking. `crop_view._build_guide` (cultivation guide builder) is still used. An optional labelled "ML second opinion" using the forest was offered; the user has not answered.
- `weather.py`, `geo.py`, `auth.py` (PBKDF2 PIN hashing, phone/PIN validation), `ui.py`, `bhashini.py` — small helpers.

### Data, docs, scripts
- `krishi/data/crops_field.csv`, `crops_horti.csv`: 30 crops. **Only `*` (national) and `Maharashtra` rows exist**; no Telangana rows. Columns: seasons, sow/harvest months, duration, yield lo/hi per acre, cost, price lo/mid/hi, MSP, procurement share, irrigations needed, rainfed-OK seasons, temperature and pH ranges, perishable, glut_prone, loss fraction, cluster-absorb acres, `*_est` flags and `src_*` URLs.
- `docs/`: `solution_writeup.md`, `architecture.svg`, `design_artifacts.md`, `deployment_plan.md`, `README.md`. `reports/impact_report.md` + `impact_results.json` come from `scripts/run_impact.py`. `reviews/` holds the expert-panel critiques (CEO, farmer, ML researcher, UI).
- Scripts: `run_impact.py` (water-saving versus baseline, 30 seasons), `translate_locales.py`, `seed_demo_village.py` (synthetic plans around Yavatmal, `--clear` removes), `seed_demo_vendors.py` (see below).

## 5. Static versus live

| Part | Status |
|---|---|
| Location, soil estimate, 30-y weather, forecast, sowing date, water balance, feasibility, yield scaling, bad-year loss | **computed per farm and per sowing date** |
| Market price | live from CEDA when reachable, else stored five-year harvest-month range |
| Yield, cost of cultivation, MSP, procurement share, loss fraction, glut capacity | **static** annual official numbers in the CSVs |
| Texture → water-holding (TAW) | static assumption table |
| Vendor needs, farmer commitments, plans | stored JSON, live as users add them |

"Cached" means a result is saved and reused instead of fetching again: `lru_cache`/`st.cache_data` (in memory, lost on restart), the disk cache for weather history (survives restart), and the 12 h price cache. The Home refresh button clears them.

## 6. Recent changes (latest session)

1. **Season is a soft gate** (`crop_table.crops_for(any_season=True)` + `score_crop`): previously a crop was dropped unless its listed seasons included the sowing season, so rice (listed Kharif only) never showed for Rabi sowing. Now off-season crops are tested with the weather simulation for the chosen date; they need temperature fit ≥ 0.65 and `p_poor` < 0.30, get a 0.85 score discount, and carry the reason `off_season` (text in `locales/en.json`; not yet translated to Hindi/Marathi).
2. **Demo data for Sangareddy / Kandi (17.5991 N, 78.1266 E)**: `py -3.11 scripts/seed_demo_vendors.py` creates 6 fictional vendors (phones 9000000001–9000000006, PIN 1234, `"demo": true`) in Sangareddy, Patancheru, Shankarpally, Sadasivpet, Narsapur and Bowenpally (5–40 km) with 18 priced needs (rice, maize, tomato, brinjal, okra, chilli, chana, jowar, groundnut, masoor, onion, cabbage, cauliflower, coriander), delivery Jan–May 2027. Price = table mid × 1.05, never below MSP; **they are not real quotes**. `--clear` removes them. These records are committed in `vendors.json`, `polls.json`, `communities.json`.

## 7. Known issues and what is unfinished

- **Telangana economics are not real data.** Test at Kandi, 1 Nov sowing, water all year: vegetables rank first, lentil is around 10th, rice appears at about −₹1,000/acre because the national row uses ₹1,970/quintal and assumes only 45% procurement at MSP. Telangana buys most paddy at MSP, so true profit is probably higher. Fix with an official Telangana rice price and procurement share (and cost of cultivation); do not invent numbers. If a number is unavailable keep the `*_est` flag so it is never ranked #1.
- Off-season crops use the usual-season price and yield; the card says so.
- Soil N, P, K have no map source; they stay unknown unless the farmer types soil-test numbers.
- Vegetable rows are partly estimated and flagged "rough numbers".
- No demo **farmers/plans** around Sangareddy: the Village screen and the "too many farmers planting" warning are empty there. `scripts/seed_demo_village.py` is centred on Yavatmal (Maharashtra, black soil); a Sangareddy version (state Telangana, red soil) was proposed, not built.
- Live price path is only mock-tested (CEDA was timing out). Re-check when it recovers.
- Hindi/Marathi strings added recently are not machine-translated yet: run `py -3.11 scripts/translate_locales.py` when Google Translate stops returning 429.
- GPS needs testing on a real phone (desktop test used a fixed location).
- Open-Meteo has an hourly request limit; heavy testing triggers 429. The disk cache means each 10 km cell is fetched once.
- Whisper covers 12 languages; Bhashini (22 languages) needs a free account and is **(unverified)**.
- The sensor / pump automation is design only (in `docs/design_artifacts.md`), not built.
- Latest impact numbers (per acre, 30 seasons, Yavatmal black soil, `reports/impact_report.md`): cotton 17% less water with scheduling / 44% with drip; tomato 35% / 57%; onion 20% more / 20% less (+28% yield); wheat 67% more / 11% more (+7% yield); chana, mustard, tur use more water for +59% / +51% / +17% yield. These were produced under stated assumptions; read the report before quoting them.

## 8. How to test

- There is no test suite in the repo. Earlier checks used Streamlit `AppTest` (headless) by priming `st.session_state` (pills/segmented controls and keyed checkboxes do not drive well through AppTest), and direct Python calls such as `recommender.rank_crops(...)` and `sell_view._offers(...)`.
- Quick ranking check:
  ```python
  from datetime import date
  from krishi import recommender as R, water
  ctx = {"lat": 17.60, "lon": 78.13, "taw": water.SOIL_TAW["unknown"], "sow": date(2026, 11, 1)}
  opts = R.rank_crops("Telangana", "Rabi", R.Plot("p", 1.0, "all_year"), {"temperature": 24.0}, 7.0,
                      R.NearbySignals(), top_n=0, climate_ctx=ctx)
  ```
- Before pushing UI work, run the app and click through Home → What to grow → Sell as a farmer and as a demo vendor.

## 9. Suggested next steps (in order)

1. Add verified Telangana (or any new state) rows to the crop CSVs with source URLs; keep `*_est` flags where numbers are not verified.
2. Seed Sangareddy demo farmers and plans for the Village screen.
3. Translate new locale strings; re-verify live prices; test GPS on a phone.
4. Optional: the labelled ML second opinion; real sensor/pump integration.
