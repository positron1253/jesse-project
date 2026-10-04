# 11: CEO response to the panel (round 2)

## 1. Where I agree and endorse

- **Farmer (02):** Ramesh's line *"a farmer doesn't need advice, he needs a price"* is the product spec.
  - I endorse his ranked needs in full: ₹/acre with a bad-year loss, a buyer and price **before sowing**, area split by **rainfed vs borewell land**, and the water question ("till which month?").
  - His soybean example (mandi about ₹4,170 vs MSP ₹5,328) is exactly why MSP cannot be assumed.
- **ML (03):** I concede one point. I had kept the Random Forest as a "suitability filter". The researcher is right that the labels are semi-synthetic, so even as a filter it only adds noise. **Remove it from the path.** I endorse:
  - the district APY history prior combined with ECOCROP suitability;
  - CEDA's cleaned Agmarknet data as the bulk price source;
  - the ranking `U = E[π] − λ·max(0, −π_P10)`;
  - the golden tests (Ludhiana → wheat, Kolar tomato flagged high risk);
  - adding in-app planned acreage as a glut signal.
- **UI (04):**
  - Removing the public table that lists every farmer's name and coordinates (`pytest.py:728-752`) is a **must-fix**, not a UX nicety.
  - The one-page Farm Plan wizard, ₹ ranges instead of "votes", the risk light that always gives a reason, and the vendor form with price, grade and pickup with no free text are all right.
  - The "Supply coming (50 km)" vendor view is the same planting registry I proposed, seen from the buyer's side. That is the moat, and I fully back it.

## 2. Conflicts and my resolution

**Data scope vs the 2-week timeline.** The ML plan (around 60 crops, all-India boundaries, a backtest for every district) is a quarter's work.
- **Resolution: one pilot district, Yavatmal.** It matches the farmer persona and gives a good mix: MSP crops (cotton, soybean, tur, chana, wheat), plus glut-prone onion and a few vegetables. About 12 crops in total.
- api.data.gov.in refuses connections even from this Indian machine, so **v1 ships an offline snapshot**: `mandi_monthly.parquet` for about 5 nearby APMCs (Yavatmal, Wani, Pusad, Digras, Ner) plus Lasalgaon as the onion benchmark, built from CEDA/Agmarknet exports.
- `refresh_live_prices()` is optional. It runs only if the founder's data.gov.in key works, and otherwise the app shows "prices as of <date>".
- Validation covers the golden tests and a single 2019–2024 backtest for Yavatmal only.

**Glut quotas vs farmer freedom.** We never block a farmer.
- The quota is **soft**. A crop whose cluster quota is full loses its rank-1 slot, gets a price haircut in the ₹ range, and shows a plain warning: "140 acres of onion already planned near you for March."
- The quota is **hard only for platform-brokered contracts**: vendor demand is allocated first come, first served, and nobody can accept more than the open quantity.

**PIN login vs speed.** Keep phone + 4-digit PIN. It takes about 2 days and stops impersonation. OTP comes later.

**MSP floor weighting.** The researcher's floor is binary: MSP counts only where procurement is strong. Mine is weighted. Merge them:
- `floor = MSP × r(state, crop)`, where `r` comes from a small hand table.
  - About 0.9 for Punjab/Haryana wheat and paddy.
  - About 0.6 for tur, urad and masoor under PSS, discounted for payment delay.
  - About 0.3 for soybean and cotton in Vidarbha, given Ramesh's CCI queues and late payment.
  - 0 for crops with no MSP.
- The card shows the status in words: "MSP ₹5,708, but government buying is slow here."

**Forward contracts vs the farmer's trust asks** (₹1–2k/acre advance, UPI payment within 48 hours, quality agreed upfront, FPO as the middle party). v1 cannot move money, so it **records and enforces terms socially**:
- **Contract card:** price type (fixed / floor "not below MSP" / mandi ± x), grade and moisture %, who measures (FPO or APMC), delivery window, pickup point, advance amount, and payment due within 48 hours.
- **State machine:** `offered → accepted → sown (qty locked) → delivered → paid`. The advance and the final payment are made by UPI outside the app. Both sides confirm each step against the reference code.
- The vendor's **on-time payment rate and rejection rate** are shown on every offer.
- Escrow through the FPO's bank account or a payment aggregator comes later.

## 3. Answers to questions put to me

- **Farmer: "Who pays you?"** The vendor does: 1–2% on contracted sales, plus a dashboard subscription. The app is free for farmers, and the fee is stated on every contract.
- **Farmer: "What if a vendor backs out?"** In v1 we cannot guarantee the sale, and we will say so. What we do:
  - The FPO relists the stock to other vendors in the cluster.
  - The defaulting vendor's record shows the default publicly, and the advance is not refunded.
  - Later, escrow makes that penalty automatic.
- **Farmer: partners?** Yes. FPO and KVK Yavatmal co-sign the crop parameters, and their name appears on the advice.
- **ML: λ default?** Default to downside protection: λ = 1, and λ = 2 for rainfed-only farmers under 2 ha. Always show the bad-year number.
- **ML: who refreshes the data?** The founder, quarterly during the pilot, using `scripts/build_data.py`. `crop_params.csv` is curated together with KVK.
- **ML: is "we don't know" acceptable?** Yes, and it is better than a wrong #1. It shows as "ask KVK" mode.
- **UI: who is the v1 user?** A farmer **helped by an FPO field agent** for setup. After that the farmer uses it alone through audio.
- **UI: launch languages?** Maharashtra, in Marathi and Hindi, with English as a fallback.
- **UI: show MSP/mandi prices that disagree with vendor offers?** Yes. Transparency is the product. An offer below the mandi rate is labelled as such.

## 4. Final TOP 7 must-haves for v1 (Yavatmal end-to-end demo)

1. **Profit engine** (`krishi/recommender.py`): APY prior, ECOCROP filter, offline price snapshot, MSP × r, DES cost. Output: ₹/acre P10–P90 range plus the bad-year figure. Random Forest removed.
2. **Farm inputs that matter:** GPS or village picker; water (none / till Dec / till Mar / all year); up to 2 parcels (rainfed and irrigated) with area in acres.
3. **Marathi/Hindi result cards:** ₹ range, risk light with a reason, MSP status in words, and "buyers nearby want X qtl at ₹Y".
4. **Vendor need as a forward contract:** the terms card, the state machine, quantity locked at sowing, and the vendor's payment record.
5. **"How much" plan:** contracted area first, then capped spot area. Includes the `crop_plans.json` registry, soft glut warnings and the vendor's "Supply coming" view.
6. **Safety basics:** phone + PIN, delete the public user/coordinates table, html-escape chat, delete the fake seed prices.
7. **Chaptered, cached audio guide**, grounded on `crop_params.csv` (sowing date, seed rate, fertiliser in bags, number of irrigations, key pest).

**CUT from v1:**
- the Kaggle Random Forest and its confidence %;
- NPK boxes in the default path;
- all-India coverage;
- any dependency on the live API;
- Plotly on farmer pages;
- an ML price forecast;
- escrow and in-app payments;
- SMS/WhatsApp OTP;
- the vendor map (list only);
- weather and pest alerts;
- voice input;
- Odia TTS;
- dark mode;
- a LightGBM yield model;
- satellite acreage checks;
- the perennials checkbox (drop it, or untick it by default).
