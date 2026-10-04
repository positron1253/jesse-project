# 14 — UI expert, round 2 response (frozen v1 UI spec)

## 1. Agreements

- **Ranking by money, not by "votes".** The CEO, farmer and ML researcher all ask for this, and I agree. The "% of model votes" UI, `out_of_range` and the red banner come out (ML §5). The card is built around ₹/acre.
- **Water is the first question, not N/P/K** (Farmer §2, ML §3 `W_eff`, CEO irrigation factor). N/P/K moves behind a "Soil Health Card" expander.
- **Location by GPS or a list, never typed coordinates** (all three reviews).
- **Polls become priced offers** with price, grade, delivery window and pickup (CEO §4, Farmer §4). The quantity is locked once the vendor accepts.
- **Planted-acreage registry and glut warning** (CEO anti-herding, ML in-app acreage). The UI's job is to surface it in plain words.
- **"New for your area" can never be rank 1** (ML §3). The UI enforces this visually as well.

## 2. Conflicts and resolution

| Topic | Tension | Resolution |
|---|---|---|
| Expected vs bad-year profit | CEO wants π and π10 always shown. ML has P10/med/P90. Too many numbers for Ramesh. | **Two numbers only.** Show "Usual year ≈ ₹38,000/acre" in large type and "Bad year: loss ₹8,000" on the line below, red when negative. Round to ₹1,000 and never show decimals or P90. Use Indian grouping (₹1,20,000). |
| Risk | CEO uses λ-score, ML uses P(π<0) buckets | Show one badge 🟢 Low / 🟡 Medium / 🔴 High (ML's P(π<0) cut-offs) plus **one reason sentence** from `reasons[0]`. No λ slider in v1. Default λ = 1 (medium). |
| Quota / cap | CEO risk_cap (25% of land for TOP crops) plus cluster quota. Messages could read as scolding. | Show the cap **in the allocation step**, never on the card. Example: "Keep tomato to 1 acre or less. 140 acres already planned near you." The slider max is set to the cap, so the farmer can't make an error. |
| Forward-contract terms | CEO lists price type, advance, penalties. Low literacy makes a one-tap mistake likely. | v1 has fixed price only, plus grade, window and pickup. A farmer taps "I can give" → `st.dialog` reads the 4 terms back in large text with 🔊 → the farmer types the quantity → a "Yes, I agree" button (primary) next to "Not now". Advance and penalties come later. |
| Rainfed vs borewell plots | Farmer has 2 plots. ML takes a single irrigation value. | **Two area boxes**: "Land with water" and "Land with rain only". The engine is called once per plot with the matching irrigation value, and the plan lists both plots. |
| 6-step wizard | Too much for 1 day | **3 screens**: ① Farm (place, water, land) ② Crops (season pill + 3 cards) ③ Plan (allocation, buyers, audio). Soil is a single optional select on ①. |

## 3. Answers to questions put to me

- **CEO, "normal vs bad year":** see the table above. The 🔊 button on each card speaks the same two numbers plus the reason, so the audio and the screen always match.
  **CEO, "140 acres near you":** show it as a sentence with a number and a 🚜 icon, no charts.
  **CEO, "accept contract":** the confirmation dialog plus a typed quantity makes it two deliberate actions.
- **Farmer:** yes, screen ① is exactly your three things: village/GPS, water (None / Till Dec / Till Mar / All year), and language with voice. N/P/K is off the default path, and orchards are unticked by default. Testing: 10 farmers, ₹8k phone, throttled "Slow 3G" in DevTools before the field test. Success = they produce a plan with no help in under 3 minutes.
- **ML researcher:**
  - Ranges are shown as rounded "≈" values; P10 appears only as "bad year".
  - "New for your area" becomes a grey chip "🧪 New here — try on a small plot first", sorted below local crops, with allocation capped at 0.5 acre.
  - Irrigation input is 1 tap (pills) and area is 1 number box with an acre/bigha/hectare pill. Voice input waits until later (Bhashini).

## 4. FROZEN v1 UI spec (Streamlit 1.41, ~1 engineer-day)

**Global**
- `krishi/i18n.py` with `t(key)` and `locales/en.json` (+ `hi.json`, `mr.json` auto-translated). Current language lives in `st.session_state.lang`, mirrored to `st.query_params["lang"]`.
- Header row: app name · language `st.selectbox` (native names) · logout.
- Replace the sidebar nav with `st.segmented_control` at the top of the main area, mapped onto the existing `st.session_state.view`. Hide the sidebar after login.
- CSS: base font 18 px, buttons min-height 48 px, Noto Sans + Noto Sans Devanagari via Google Fonts `<link>`.
- Escape chat text with `html.escape`. Delete the public user tables at `pytest.py:728-752`.

**Nav**
- Farmer: `nav.plan` 🌱 Farm Plan (default) · `nav.buyers` 🛒 Buyers · `nav.group` 💬 Group chat · `nav.tips` 💡 Tips.
- Vendor: `nav.needs` 📢 My needs (default; open needs + "Supply coming" table) · `nav.post` ➕ Post need · `nav.group` · `nav.prices` 💰 Prices.

**Login/Register (sidebar until logged in)**
- Role: two buttons `role.farmer` / `role.vendor`.
- Fields: `f.name`, `f.phone` (10 digits), `f.pin` (4 digits, `type="password"`; store a pbkdf2 hash).
- Location: `loc.gps` button (`get_geolocation`). If ML's `geo.locate_district` exists, show "📍 {district}"; otherwise show "📍 Location saved". Fallback: an expander `loc.manual` with the existing lat/lon inputs.
- Login: phone + PIN.

**Farm Plan, screen ① Farm** (`st.session_state.plan_step = 1`)
- `p1.title` "Your farm".
- Location line `p1.place` (district or "your saved field") plus `loc.gps` "Use my current location".
- `p1.water` "Water for your land?" as `st.pills`: `w.none` None (rain only) · `w.dec` Till December · `w.mar` Till March · `w.all` All year. Default: `w.none`.
- `p1.land_water` "Land with water" and `p1.land_rain` "Land with rain only" as number inputs, step 0.5, default 0 / 2. Unit pill `u.acre` / `u.bigha` / `u.hectare`, default acre. Store the value in acres (bigha = 0.62 acre default, editable later).
- Optional `p1.soil` select (existing soil types, default "Don't know"). Expander `p1.card` "I have a Soil Health Card" holds the existing N/P/K/pH inputs.
- Button `btn.next` "See best crops".

**Screen ② Crops**
- Season `st.pills` from `wx.SEASONS`, default the current season, with labels `s.kharif` "Kharif (Jun–Oct, rain)" and so on.
- `p2.title` "Best 3 crops for your land". One card per row:
  ```
  🌾 Soybean (सोयाबीन)                ★ Best
  Usual year ≈ ₹38,000 per acre          [card.usual]
  Bad year: loss ₹8,000                  [card.bad_loss] / card.bad_profit
  Yield 6–9 quintal/acre                 [card.yield]
  🟡 Medium risk — prices fell below MSP in 2 of last 5 years   [risk.*, reasons[0]]
  🛒 2 buyers want 300 quintal           [card.buyers]
  🧪 New here — try on a small plot first   [card.new]  (only if !is_local_verified)
  [ ☐ Choose ]   [ 🔊 Listen ]
  ```
- If the engine returns no profit for a crop, show `card.no_price` "Price data not available yet" and sort it last.
- Low-data notice (single line, not a banner): `p2.ask_kvk` "Not sure? Call Kisan Call Centre 1800-180-1551".
- Buttons `btn.back` and `btn.make_plan` (needs ≥1 crop chosen).

**Screen ③ Plan**
- One `st.slider` per chosen crop per plot, 0.5-acre steps. Max = min(plot area, cap). The default split is proportional to score. Show `plan.left` "{x} acre not used" until the sliders add up to the plot area.
- Totals: `plan.usual_total` "Usual year ≈ ₹{x}" and `plan.bad_total` "Bad year ≈ ₹{y}".
- Warnings: `warn.cap` "Keep {crop} to {n} acre or less" and `warn.glut` "{n} acres of {crop} already planned near you".
- Button `btn.save_plan` "Save my plan" writes to `crop_plans.json` and shows `msg.saved` "Saved ✔".
- Buyers list under the plan, distance-sorted: `buyer.line` "{vendor} · {km} km · wants {qty} quintal {crop} · ₹{price}/quintal · {pickup}" with an `btn.can_give` "I can give" button that opens the confirm dialog (`dlg.title`, `dlg.terms`, `dlg.qty`, `btn.agree`, `btn.not_now`).
- Guide: crop pill, then `btn.guide` "Get audio guide". Keep the existing single audio file (chapters come later). Cache it in `st.session_state` keyed by (crop, lang).

**Vendor ➕ Post need** (`st.form`, extends `create_poll`)
- `v.crop` select from the engine crop list, `v.qty` + `v.unit` (default quintal), `v.price` ₹/quintal (required).
- `v.grade` pills A / B / FAQ (default FAQ). `v.from`, `v.to` dates (default today+90 / +120). `v.pickup` pills `pk.vendor` "I collect from village" / `pk.farmer` "Farmer delivers". `v.place` text, shown only for delivery.
- Submit `btn.post` "Post need". `v.min_days` warning if the window starts in under 60 days ("Farmers need time to grow").
- "Supply coming" table: crop · planned quintal · farms, from `crop_plans.json` within 50 km.

**Strings to translate in v1:** every key named above (`nav.*`, `role.*`, `f.*`, `loc.*`, `p1.*`, `w.*`, `u.*`, `s.*`, `p2.*`, `card.*`, `risk.low|medium|high`, `plan.*`, `warn.*`, `msg.*`, `buyer.*`, `dlg.*`, `btn.*`, `v.*`, `pk.*`), about 80 strings. Crop names come from `crop_params.csv` per language, not from a hard-coded Hindi map. Chat, tips and vendor free text stay untranslated.

**Out of v1:** chaptered audio, voice input, village search list, advance/penalties, dark mode, `st.navigation` multipage refactor.
