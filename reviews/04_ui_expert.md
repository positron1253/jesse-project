# 04 — UX / Product Design review (Krishi Sahay)

Reviewer: UX lead (low-literacy, low-bandwidth, multilingual Bharat apps). Streamlit 1.41.1 installed, so
`st.navigation`, `st.dialog`, `st.pills`, `st.segmented_control`, `st.audio_input`, `st.query_params` are all available.

## 1. Top UX problems (ranked)

1. **Login has no auth at all.** Pick-your-name dropdown, no secret (`pytest.py:675-687`). Anyone can be anyone; it also
   leaks the full user list. The logged-out landing page goes further and **publishes every farmer's name + exact farm
   coordinates** (`pytest.py:728-752`). Remove that table now.
2. **The core promise is split across silos.** Crop advice (`crop_prediction`, `pytest.py:964`) never hands off to vendor demand
   (polls in chat tabs, `pytest.py:1061-1153`) or prices (`pytest.py:1164`). The farmer gets "Maize 15%" and a dead end.
   The founder's flow (soil → crops → area → yield → vendors → plan → audio) appears on no single screen.
3. **The output is in jargon a farmer won't trust.** "Low match · 15% of model votes" (`ui.py:96`, screenshot 2), "#1 RECOMMENDATION:
   Coffee" for Delhi Rabi, N/P/K number inputs (`crop_view.py:107-111`), lat/long (`crop_view.py:58-68`, `pytest.py:706-708`),
   ERA5 grid point and elevation captions (`crop_view.py:151-155`), "SoilGrids" (`crop_view.py:113`). There's no ₹, no
   quintals, no acres anywhere in the result. A red "Low confidence" banner sitting over a #1 pick (screenshot 2) undermines
   the whole product.
4. **The language switch only changes the guide.** "Guidance language" sits in Step 1 (`crop_view.py:78`), but every label,
   button and the nav stay English, and the nav labels are inconsistent ("crop Prediction", `pytest.py:659`). A Hindi-only user
   can't get to the Hindi.
5. **It's desktop-first.** The sidebar is the only nav (`pytest.py:598-669`). On Android it collapses behind a tiny `>` and
   farmers won't find it. Three crop cards in `st.columns(3)` (`crop_view.py:202`) and 4-column number inputs stack into a long
   scroll. Wide layout (`pytest.py:21`) and 1150 px max width (`ui.py:17`) were designed on a laptop (screenshots 1–3).
6. **Too much typing.** Soil NPK, product names as free text (`pytest.py:1072`, `1247`), market "Location" free text, and
   poll quantity typed in without a unit hint for the farmer (`pytest.py:1131`).
7. **The audio is one 3-minute blob** (screenshot 3, `crop_view.py:243`). You can't jump to "irrigation", it takes 20–40 s
   to generate on every click (`crop_view.py:233`) and it isn't cached per crop+language. Odia has no audio (`crop_view.py:18`).
   Audio is the main channel for a low-literacy user, but it's built as an afterthought.
8. **Vendor demand form is thin.** A poll is product + qty + unit + deadline (`pytest.py:1071-1080`). It has no price offered,
   grade, pickup or delivery window, so a farmer can't judge whether it's a good deal. "Poll" and "commitment" are the wrong words too.
9. **Robustness and safety.** Chat renders user text with `unsafe_allow_html` (`pytest.py:1014-1046`), which allows HTML
   injection. The chat uses blue `#007BFF` bubbles off-brand. Heavy imports (matplotlib, seaborn, plotly, `pytest.py:13-16`)
   slow cold start. Plotly adds ~3 MB of JS on 2G/3G (`crop_view.py:215`).
10. **Sample data is presented as real.** "Delhi tomato ₹25.50" seeded by "Sample Vendor" (`pytest.py:546-564`).

## 2. Proposed IA

Use bottom-style top tabs instead of the sidebar, role-specific, with at most 4 destinations each. Use icon + one word.

**Farmer:** 🏠 Home · 🌱 My Farm Plan · 🛒 Buyers · 🔊 Guide (profile/language behind a 👤 chip in the header)
**Vendor:** 🏠 Home · 📢 My Needs · 🚜 Supply Coming · 💬 Farmers

Chat and Tips move under Buyers/Farmers. Market Prices merges into the Plan cards and the Buyers list, so it's no longer its own page.

### Farmer Home (mobile, 360 px)
```
┌──────────────────────────────┐
│ 🌾 Krishi Sahay   [हिं ▾] [👤]│
│ Namaste Prateek 🙏           │
│ ┌──────────────────────────┐ │
│ │ 🌱 Rabi 2026 plan        │ │
│ │ Wheat 3 ac · Mustard 2 ac│ │
│ │ Expected ₹1.6–2.1 lakh   │ │
│ │ [ ▶ Continue plan ]      │ │
│ └──────────────────────────┘ │
│ 🛒 3 buyers near you want:   │
│  Mustard 40 qtl · ₹5,800/qtl │
│  Potato 120 qtl · ₹1,100/qtl │
│ 🔊 Today: "Irrigate wheat"   │
│  [ ▶ 1:10 ]                  │
└──────────────────────────────┘
```

### The "Farm Plan" wizard (one page, 6 steps, progress dots, one decision per screen)
1. **📍 Your farm.** Big GPS button "Use my location", or a village search box (Census village/LGD list ⇒ lat/lon), or tap
   the map. Show the village name, never the numbers. Area: `st.number_input` with a unit pill **acre | bigha | hectare**,
   with bigha defined per state.
2. **🟫 Your soil.** Six soil-colour photo tiles (black/red/alluvial/sandy/laterite/clay) in a 3×2 grid, plus "I have a Soil
   Health Card" (NPK hidden behind it). Add a water tile row: **💧 Canal/borewell | 🌧️ Rain only**. Irrigation matters more
   than pH for a profit answer.
3. **📅 Season.** Kharif/Rabi/Zaid shown as month pills ("Jun–Oct, baarish"), preselected.
4. **🌾 Top 3 crops.** Cards as in §3. Let the farmer tick 1–3 crops.
5. **⚖️ How much of each.** The allocation slider (§3).
6. **✅ Your plan.** Summary, a "Tell buyers" button that publishes the plan as supply, and a link to the audio guide for each crop.

Persist each step in `farmers.json -> plans[]`, so Home shows "Continue plan".

### Vendor Home
```
┌──────────────────────────────┐
│ 📢 Post a need   [ + New ]   │
│ Your open needs              │
│  Mustard 40 qtl ▓▓▓▓░ 62%    │
│  Potato 120 qtl ▓░░░░ 15%    │
│ 🚜 Supply coming (50 km)     │
│  Mustard  310 qtl · 41 farms │
│  Wheat   1,900 qtl · 120     │
│  Potato   80 qtl ⚠ short     │
│ [ 🗺️ Map of farms ]          │
└──────────────────────────────┘
```

## 3. How to present the results

**Crop card**, one per row on mobile, so no squeezed columns:
```
┌──────────────────────────────┐
│ 🌾 गेहूँ Wheat        ★ Best   │
│ ₹ 28,000 – 36,000 profit/acre│
│ 18–22 qtl/acre · MSP ₹2,425  │
│ Price risk  ● Low            │
│ Fits your land ●●●○          │
│ 🛒 2 buyers want 300 qtl     │
│ [ ☐ Choose ]   [🔊 Why?]     │
└──────────────────────────────┘
```
- Lead with **₹ profit per acre as a range**, never a point value. Show yield as a range in qtl/acre.
- **Risk is a traffic light with a reason**, e.g. "🔴 High: tomato prices fell 60% in 3 of last 5 years" or "🟢 MSP crop".
  Glut risk should beat model fit when ranking for display.
- **Confidence shows as 1–4 dots labelled "Fits your land"**. Drop percentages and "votes". When confidence is low, don't put a scary
  banner over a #1 pick. Say "Fewer farms like yours in our data — check with KVK 📞 1800-180-1551" (Kisan Call Centre) on the card.
- Add a "🔊 Why?" button that plays a 15 s TTS clip: "Wheat is suggested because your soil is alluvial, you have a borewell, and the mandi price is steady."

**Vendor map:** `st.pydeck_chart` with a ScatterplotLayer (vendors sized by demand qtl) and a 50 km ring, with the farm as the pin. Below it, a
list sorted by distance ("Sharma Traders · 12 km · wants Mustard 40 qtl · ₹5,800 · pickup from village"). The list is the
primary element, the map is a toggle (`st.segmented_control(["📋 List","🗺️ Map"])`). That saves bandwidth, because pydeck tiles are heavy.

**"How much to grow":** a stacked bar of the farmer's acres (green/yellow segments) with one `st.slider` per chosen crop
in 0.5-acre steps that must sum to total area. Show a default suggestion: "Grow 3 acres wheat, 2 acres mustard. Buyers already want
40% of your mustard." Live ₹ total plus a warning if one crop's share is more than 70% or exceeds nearby demand ("⚠ Too much potato —
buyers want only 80 qtl within 50 km").

**Audio guide:** split it into chapters, each its own short MP3 (60–90 s) shown as a big row: 🚜 Land prep · 🌱 Sowing · 💧 Water ·
🧪 Fertiliser · 🐛 Pests · 🌾 Harvest & selling. Each row gets ▶ and ✔ ("done"). Generate all chapters once per (crop, season,
state, language), cache to disk (`audio_cache/{hash}.mp3`), and serve from cache. After a few users, every common combo is instant.
Text goes behind an "📄 Read" expander.

## 4. Registration / login

- **v1 (demo-safe):** register with **phone number + 4-digit PIN** (hash the PIN with `hashlib.pbkdf2_hmac`, store the salt). Log in with phone
  + PIN on number-pad inputs. Never list users. Role is chosen with two big picture tiles (🚜 Farmer / 🏪 Buyer) before anything
  else. Language is chosen **first**, on the very first screen, as script-native buttons (हिन्दी, ਪੰਜਾਬੀ, தமிழ், ...).
  Keep the user's session in `st.session_state` and the lang in `st.query_params["lang"]`, so a shared link opens in the right language.
- **Location:** use `get_geolocation()` (already imported, `pytest.py:17`) behind a "📍 Use my location" button. Fall back to village search
  (offline CSV of LGD villages with centroids, `st.selectbox` with type-ahead), and optionally a tap-to-pin map. Coordinates
  are stored, never shown.
- **Later:** SMS OTP (MSG91/Twilio Verify), WhatsApp login, `st.login` (OIDC, Streamlit ≥1.42) for vendors, and an FPO/agent
  "assisted mode" where one field agent registers many farmers.

## 5. Vendor UX

**Post a need** (`st.dialog`, everything picked, no free text):
crop (icon grid from the master crop list) · quantity + unit (qtl default) · **price offered ₹/qtl** (pre-filled with nearby mandi
modal price, editable) · **grade** (A/B/FAQ chips with photo hint) · **delivery window** (date range) · **pickup** (🚚 I collect /
🏠 Farmer delivers to [address]) · advance % (optional).
The farmer sees it as: "Sharma Traders wants 40 qtl mustard, ₹5,800/qtl, 15–30 Mar, they pick up from your village."
They answer with "I can give [ 10 ] qtl" using a stepper.

**Supply pipeline:** aggregate every published Farm Plan within 50 km by crop and harvest month. Show it as a table with the columns
expected qtl range, number of farms, and committed vs. planned. Highlight shortfalls ("Potato: you need 120, 80 planned") with a
"Post need" shortcut. This is the vendor's reason to keep using the app, and it's what feeds the farmer's glut warning.

## 6. Visual design system

- **Colour tokens:** keep the green primary `#2e7d32` (5.1:1 on white, AA). Add semantic risk colours
  `#1b5e20/#f9a825/#c62828` that **always pair with an icon and a word**, never colour alone. Use amber text `#7a5200` on amber
  backgrounds for contrast. Replace the chat blue `#007BFF` with green tints.
- **Type:** load Noto Sans + Noto Sans Devanagari/Bengali/Tamil/Telugu/Gurmukhi/Gujarati/Kannada/Malayalam/Oriya via Google
  Fonts, but only the active script (subset by `lang`). Base size 18 px, line-height 1.6 (Indic matras clip at 1.2), headings
  22–26 px. ₹ amounts in Indian grouping (₹1,60,000 / "1.6 lakh") via `babel.numbers.format_currency(x,'INR',locale='hi_IN')`.
- **Tap targets:** minimum 48 px (raise `ui.py:65` from 44). Full-width primary buttons. One primary per screen.
- **Icons:** emoji are fine for v1 (no asset download). Later, a crop photo sprite under 100 KB.
- **Dark mode:** the current `config.toml` forces light. Keep light for v1 (outdoor sun glare favours light). Define colours as CSS vars
  so that a dark theme is a token swap later. Avoid hard-coded `#fff` in `ui.py:29,43`.

## 7. Streamlit implementation notes

- Restructure into `st.navigation({...}, position="hidden")` plus a custom top tab bar (`st.page_link` in `st.columns`) that stays
  visible on phones. Hide the sidebar with CSS `[data-testid="stSidebar"]{display:none}` on mobile. Use one `pages/` file per destination.
- Use `layout="centered"` and `max-width: 720px`. Use cards via `st.container(border=True)`. Use `st.pills` / `st.segmented_control`
  for every small choice instead of radios. Use `st.audio_input` for "speak your village / quantity" (later: Bhashini ASR).
- **i18n:** add a `krishi/i18n.py` with a `t(key)` function backed by `locales/{lang}.json`. Pre-translate the ~150 UI strings once (Google
  Translate, then human-check Hindi/Marathi/Tamil), never at runtime.
- **Low bandwidth:** cache everything with `st.cache_data` (climate, mandi prices, guides, TTS). Drop Plotly from farmer pages and use
  CSS bars (already in `ui.py:49`). Make the map lazy, behind a toggle. Wrap the result block in `st.fragment` so slider moves
  don't rerun the whole page. Show a clear "Saved ✔" after every write, because users retry on slow nets. Make every write idempotent.
- Escape chat text (`html.escape`) or use `st.chat_message`.

## 8. Copy guidelines (farmer-facing)

Use short, second-person, verb-first copy, with no English acronyms in the main text.
- "Aapke khet ke liye sabse achhi 3 fasal" (not "Top-3 recommendations")
- "Is fasal se ₹28–36 hazaar munafa / acre" · "Daam girne ka khatra: kam 🟢"
- "Pakka nahi — apne KVK se poochh lein 📞" (instead of "Low confidence")
- "Paas ke 2 kharidaar 300 quintal chahte hain"
- Buttons: "▶ Suniye", "✔ Ho gaya", "Plan banaiye", "Kharidaar ko bataiye"

## 9. v1 (1–2 weeks) vs later

**v1:** phone+PIN login and remove the public user table; a language-first screen with an i18n file for UI strings (hi, en,
plus 2 more); top-tab nav; GPS/village location; soil photo tiles plus an irrigation question; area + unit; Farm Plan wizard
with ₹ range (MSP/Agmarknet modal price × yield range − state cost table), traffic-light risk, dots confidence; vendor
"need" with price/grade/pickup; nearby-buyer list (map optional); allocation sliders; chaptered cached audio; html-escape chat.
**Later:** SMS/WhatsApp OTP; Bhashini voice input and Odia TTS; PWA/offline shell; WhatsApp audio push ("water your wheat today");
FPO assisted mode; price alerts; vendor ratings and payment escrow; dark mode; crop photo assets.

## 10. Questions

- **CEO:** Is the v1 user the farmer alone, or a field agent/FPO operator assisting farmers? That changes literacy assumptions
  completely. Which 2–3 states and languages launch first? Is it OK to show MSP/mandi prices that might disagree with vendor offers?
- **Farmers (test with 5):** Do you say acre, bigha or killa? Would you trust a ₹ number from an app, or more if it names a nearby
  buyer? Do you prefer audio in chapters, or one story? Who in your house uses the phone?
- **ML researcher:** Can you output a yield **range** (P10–P90) and a calibrated "fits your land" score in 4 buckets? Can glut risk
  come from Agmarknet arrivals and price volatility per district? How do you want low-coverage regions flagged, so the UI can switch to
  "ask KVK" mode instead of showing a wrong #1 (coffee in Delhi)?
