# Krishi Sahay — panel briefing (2026-10-03)

## The product vision (from the founder)
For an Indian farmer: take their farm coordinates + soil type → ML model recommends **top 3 crops** →
farmer picks crop/variety + land area → **predict yield** → connect to **vendors within 50 km** (Haversine)
→ map vendor requirements to the farmer's options so the farmer knows **what to grow and how much** →
give **cultivation + irrigation guidance in their native language, as audio**.

Founder's latest ask: use a **verified dataset covering all widely grown Indian crops AND vegetables**,
and make sure recommendations are a **good profit deal** for farmers, given the current Indian reality:
price crashes, distress sales, over-production that gets wasted (tomato/onion/potato gluts), middlemen,
lack of storage, MSP only for some crops, etc.

## Tech stack / files (Streamlit, JSON files as DB, Python 3.11: `py -3.11`)
- `pytest.py` — main Streamlit app (~1400 lines): login/register (farmer/vendor with lat/lon), vendor
  "communities" auto-joined by farmers within 50 km, chat, **polls** (vendor posts "need X kg of product by date",
  farmers commit quantities), market prices (vendor-entered), farming tips. View routing via `st.session_state.view`.
  NOTE: the Together API key is hard-coded on purpose — the founder wants it kept as is. Do not propose removing it.
- `krishi/weather.py` — NEW: season climatology from Open-Meteo ERA5 archive at exact coords (~9–11 km grid),
  averaged over last 3 years for the selected season (Kharif/Rabi/Zaid); coordinate sanity checks.
- `krishi/crop_model.py` — NEW: loads `RandomForest.pkl` + `label_encoder.pkl`; soil-type presets; training-range
  checks; season filter; top-3 ranking; confidence levels; SoilGrids pH lookup.
- `krishi/crop_view.py` — NEW: 4-step Crop Advisor page (farm & season → soil → auto climate → results → guide).
  Guide = Together LLM (Llama-3.3-70B) → Google Translate → gTTS audio (no Odia voice).
- `krishi/ui.py` — NEW: theme CSS + hero / step header / crop card helpers. `.streamlit/config.toml` theme.
- Data: `farmers.json`, `vendors.json`, `communities.json`, `polls.json`, `market_prices.json`, `farming_tips.json`.
- Screenshots of the current Crop Advisor: `reviews/screens/1_farm_season.jpg`, `2_results.jpg`, `3_guide_audio.jpg`.

## What is NOT built yet
- No yield prediction, no land-area / variety input.
- No link between crop recommendation and vendor demand (polls) — the two halves of the app don't talk.
- No profitability (price × yield − cost), no glut / oversupply risk, no mandi price data.
- No map of vendors, no "how much to grow" plan.

## Hard evidence from testing the current ML model
Model = RandomForest (20 trees) on Kaggle "Crop Recommendation" (2200 rows, 22 crops, features N,P,K,temp,
humidity,pH,rainfall; widely believed to be semi-synthetic, not verified). Feature importance: rainfall .24,
humidity .22, K .17, P .15, N .11, temp .07, pH .05. Real-location tests with ERA5 climate + soil-type presets:
- Ludhiana (Punjab) Kharif → coffee 50%, maize 25%, jute 15%   (reality: irrigated rice, maize, cotton)
- Ludhiana Rabi → maize 10% (reality: **wheat** — but wheat is not even in the 22 classes)
- Thanjavur (TN rice bowl) Kharif → coffee 65%
- Nagpur (Vidarbha) Kharif → coconut 25%, mango, pigeon pea (reality: cotton, soybean, tur)
- Delhi Rabi → maize 15%, coffee 5%, lentil 5% — all "low confidence"
Missing major crops: wheat, sugarcane, mustard, soybean, groundnut, bajra, jowar, potato, onion, tomato,
all vegetables, spices. The model ignores irrigation, market, and district cropping history.

## Rules for panel members
- Do NOT edit any project file except your own review file in `reviews/`. Do NOT start the Streamlit server or use
  the browser (it's in use). Reading code, running small `py -3.11` snippets, and web research are fine.
- Be concrete: cite `file:line`, name exact datasets/URLs/APIs, give numbers. Propose things buildable in this
  Python/Streamlit codebase by a small team in ~1–2 weeks, plus a clear "later" list.
