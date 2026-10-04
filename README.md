# Krishi Sahay

Helps an Indian farmer decide **what to grow and how much**, for buyers near them.

Farm location (village search / GPS) → water and land → **top crops ranked by profit per acre** (normal year and bad year, with risk) → **how many acres of each** → buyers within 50 km (Haversine) with written offers → cultivation and irrigation guide as **audio in Hindi / Marathi / English** (more languages in the guide).

## Run

```bash
py -3.11 -m pip install -r requirements.txt
py -3.11 -m streamlit run pytest.py
```

Old accounts (no phone/PIN) are under *Login → Demo accounts*. New accounts use mobile number + 4-digit PIN.

## How the recommendation works (`krishi/`)

| File | Job |
|---|---|
| `recommender.py` | Profit per acre = yield × farm-gate price × (1 − post-harvest loss) − cost. Ranks by `S = usual − λ·(usual − bad year)`. Water decides which crops are feasible. Caps keep fresh vegetables and glut-prone crops to a share of the land. |
| `crop_table.py`, `data/crops_field.csv`, `data/crops_horti.csv` | 30 crops × (all-India, Maharashtra). Every number group has a source URL in the `src_*` columns. See `data/SCHEMA.md`. |
| `live_prices.py` | Official Agmarknet monthly prices and arrivals via CEDA Ashoka's open API (no key). Optional data.gov.in via `DATA_GOV_IN_API_KEY`. |
| `plans.py` | Planting registry (`plans.json`) and nearby signals: other farmers' planned acres, open vendor demand. |
| `weather.py`, `geo.py` | ERA5 season climate for the farm, village search, state/district lookup. |
| `plan_view.py`, `i18n.py`, `locales/` | Farmer screens; English / Hindi / Marathi UI strings. |
| `languages.py`, `bhashini.py` | 20 Indian languages + English; which provider covers typed text / voice in / voice out. Bhashini (free account) adds voice for all 22 scheduled languages; adapter written from its docs and **not yet tested against the live service**. |
| `assistant.py`, `assistant_view.py` | **Ask** tab: speak or type in your language; speech-to-text (Whisper on Together, or Google Cloud Speech-to-Text if `GOOGLE_STT_API_KEY` is set in `.streamlit/secrets.toml` or the environment) → answer with your farm, plan and nearby buyers as context and the last 14 messages as memory → reply translated and spoken. Chats saved per account in `chats.json` (text only). |

`reviews/` holds the expert-panel reviews (CEO, farmer, ML researcher, UI expert) that shaped this design.

## Known limits — read before a field pilot

- **Only Maharashtra has state-level rows**; other states fall back to all-India numbers and show "new here".
- **Vegetable costs are estimates** (`cost_est=1`) and yields are from 2015–18. The app flags them as rough, never calls them low risk, ranks them below measured crops, and caps them at 25% of the land. Verify with a local horticulture officer before relying on them.
- Costs are CACP A2+FL, so profit **counts family labour as a cost**; many field crops show a loss for an average farmer. That is what the data says, not a bug.
- `hi.json` / `mr.json` are machine-translated (`scripts/translate_locales.py`). Have a native speaker review them. Odia has no audio voice.
- Mandi prices are modal prices (higher than farm-gate); the app applies a 0.92 farm-gate factor.
- The old Kaggle RandomForest is no longer used for decisions.
- Together API key stays hard-coded in `pytest.py` as requested; the guide model is `Llama-3.3-70B-Instruct-Turbo` (the old 3.1-8B is no longer serverless).

## Language support (tested 2026-10-03)

| | Languages |
|---|---|
| **Voice in + voice out + text, works now** | Hindi, Marathi, Bengali, Telugu, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Nepali, English. Whisper transcribed a test sentence at 87–100% text match in 9 of 10 languages tested (Malayalam was the weakest and flaky). These were clean synthetic voices, not real farmers, so expect lower accuracy in the field. |
| **Text only until Bhashini is configured** | Odia, Assamese, Sanskrit, Sindhi, Konkani, Maithili, Dogri, Manipuri (Meitei), Santali. Google Translate handles the text; Whisper/gTTS have no usable voice for them. |
| **Not supported** | Bodo, Kashmiri (Google Translate cannot translate them). |

To turn on voice for the text-only languages: copy `.streamlit/secrets.toml.example` to `secrets.toml` and add your free Bhashini keys.
