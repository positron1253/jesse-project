# Design artefacts

## 1. Wireframes (farmer, mobile; the built screens follow these)

```
FARM PLAN, step 1 of 3                 FARM PLAN, step 2: crops
┌──────────────────────────┐           ┌──────────────────────────┐
│ ▓▓▓▓░░░░░░░  1/3         │           │ ▓▓▓▓▓▓▓░░░░  2/3         │
│ Your farm                │           │ Best crops for your land │
│ Farm: 📍 Ner, Yavatmal   │           │ Season [Kharif][Rabi][Z] │
│  [Change farm location]  │           │ 📈 rain -29% vs earlier  │
│ Water for your land?     │           │ ┌──────────────────────┐ │
│ (Rain only)(Till Dec)    │           │ │🌾 Masoor      ★ Best │ │
│ (Till Mar)(All year)     │           │ │Usual ≈ ₹20k–25k /acre│ │
│ Unit (•Acre)( Guntha)... │           │ │Bad year: ₹16k /acre  │ │
│ Land with water [ 1.5 ]  │           │ │🟢 Low risk · reason  │ │
│ Land rain only  [ 2.0 ]  │           │ │💧 water-short 6/30   │ │
│ Soil [Black / Regur   ▾] │           │ │[☑ Choose] [🔊 Listen]│ │
│ ▸ I have a Soil Card     │           │ └──────────────────────┘ │
│ Risk (Safe)(Balanced)(+) │           │ ┌ Brinjal … 🧪 rough ┐   │
│ [  See best crops ➜   ]  │           │ [⬅ Back][Make my plan ➜] │
└──────────────────────────┘           └──────────────────────────┘

FARM PLAN, step 3: plan                ASK (voice chat)
┌──────────────────────────┐           ┌──────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓  3/3         │           │ Ask Krishi Sahay         │
│ How much to grow         │           │ Language [हिन्दी ▾]      │
│ Water land · 1.5 acre    │           │ 💬 मेरे खेत में…  (you)  │
│  Masoor   ────●──── 1.0  │           │ 💬 मसूर बोइए…  [🔊]      │
│  Brinjal  ─●──────  0.5  │           │     ▸ Show in English    │
│ Rain land · 2 acre       │           │ 🎙️ [ Tap to speak ]      │
│  Masoor   ────────● 2.0  │           │ ⌨️ Or type here…         │
│ Usual ₹73k–1.1L  Bad ₹56k│           │ 🔒 chat saved · [Clear]  │
│ ⚠ rough numbers          │           └──────────────────────────┘
│ [ Save my plan ]         │
│ ▸ 💧 Water, power, CO₂   │           VILLAGE
│ ▸ ⚙️ Right-size pump     │           ┌──────────────────────────┐
│ ▸ 🚿 Water today?        │           │ Village water and power  │
│ Buyers near you (50 km)  │           │ Season [Rabi] Radius 5km │
│  Sakshi · 3 km · ₹6,800  │           │ Water available [150000] │
│  [I can give] → confirm  │           │ 40 farmers 142 ac        │
│ 🔊 Audio guide           │           │ Demand 43,085 m³ (P50)   │
└──────────────────────────┘           │ ✅ enough even dry year   │
                                       │ table + bar chart        │
VENDOR: Post need                      │ ▸ where a crop change    │
┌──────────────────────────┐           │   would save water       │
│ Crop [Masoor ▾] Qty 100  │           └──────────────────────────┘
│ Price ₹/quintal [ 6800 ] │
│ Grade (A)(B)(FAQ)        │
│ From 2027-02 → 2027-03   │
│ Pickup (I collect)(Deliv)│
│ [ Post need ]            │
└──────────────────────────┘
```

Design rules used: one decision per screen, big tap targets, rupee ranges (not percentages), a traffic light with one reason sentence,
the 🔊 button on every spoken answer, no jargon (no N/P/K, no "model votes"), English / Hindi / Marathi UI with the guide and chat in 20 languages.

## 2. Data model (JSON files today; one table each when moved to a database)

| Entity | Key fields |
|---|---|
| `farmers.json` / `vendors.json` | id, name, latitude, longitude, phone, pin_hash (PBKDF2), state, district, created_at |
| `plans.json` (planting registry) | id, farmer_id, lat, lon, season, plot (`rain`/`water`), crop_id, acres, yield_q_lo/hi, water (level), soil, state, created_at, demo |
| `polls.json` (priced offers) | id, community_id, vendor_id, product, crop_id, quantity, unit, price_per_quintal, grade, delivery_from/to, pickup, place, status, responses[{farmer_id, quantity, reference_code}] |
| `chats.json` | user_id → [{id, role, text, text_en, lang, ts}] (text only, last 300) |
| `communities.json` | vendor community, members with distance, messages |
| `krishi/data/crops_*.csv` | one row per (crop, state or `*`): seasons, yield lo/hi, cost, price lo/mid/hi, MSP, procurement, irrigations, climate ranges, loss share, flags, and source URLs per number group (schema in `krishi/data/SCHEMA.md`) |
| `krishi/data/crop_water.csv` | Kc ini/mid/end, root depth, depletion fraction, Ky, whether each is verified, source |

## 3. Process and service design

- **Farmer journey:** register (phone + PIN, location by village search) → Farm Plan (3 screens) → save plan → see buyers → confirm offer (dialog reads terms back, then types quantity) → UPI payment and delivery outside the app → Ask / Village / Water panels as needed.
- **Vendor journey:** register → post a priced need (price required, delivery window at least 60 days out is encouraged) → see supply coming near them (totals) → receive farmer commitments with reference codes.
- **Panchayat / FPO journey:** open Village screen → set water available (from Water Security Plan) → read demand vs supply and crop-change suggestions.
- **Trust design (from the farmer review):** written price, MSP shown beside offers, reference codes, equal confirmation steps, vendors' payment record to be shown from pilot data.

## 4. Optional sensor and pump automation (DESIGN ONLY, not built)

The brief says hardware is not expected, so this is a reference design that plugs into the existing schedule.

```
soil-moisture probe (capacitive, 2 depths) ─┐
rain gauge (tipping bucket, optional)       ├─► low-power microcontroller + radio ─► gateway/phone ─► Krishi Sahay
pump current/hour meter + relay ────────────┘                                         (adds readings to the schedule)
```

- **Control rule (proposed):** run the pump only inside the farmer's power/sun window, only when modelled *and* measured depletion pass the crop's trigger (`Dr ≥ RAW`), never when the 24 h forecast gives rain above a threshold, stop at the target depth or a hard daily cap. A manual override always wins.
- **Safety:** relay interlocks with the starter, dry-run protection from the current sensor, and an advice-only mode (no relay) as the default.
- **Data:** `sensor_readings(farm_id, probe_id, ts, vwc_pct, depth_cm)`, `pump_events(farm_id, ts_on, ts_off, kwh_or_hours)`; the model's soil-water state is nudged toward the measured value.
- **Not claimed:** sensor cost, power draw and accuracy were not verified. Before building, validate on one farm against a gravimetric soil sample.


## 5. Farmer flow, version 2 (current)

`Login → Home tiles → What to grow (1 Location by GPS or edited, 2 Water and land, 3 Soil: test numbers or satellite estimate, 4 Sowing date, 5 Risk) → Crops → Plan (acres, guide, buyers) → My farm (crops, irrigation system, schedule) → Sell (all demand within 50 km) → Ask / Village / Water & energy at any time.`

```
MY FARM                                     SELL
┌──────────────────────────┐                ┌──────────────────────────┐
│ 🏠 Home   My farm        │                │ 🏠 Home   Sell to buyers │
│ [My crops][Irrigation]   │                │ Crops in demand ≤ 50 km  │
│ [Watering schedule]      │                │ Crop   Buyers Qty  ₹/q   │
│ 🌾 Chana · 1.5 acre      │                │ Tur      1    120  7,800 │
│  Day 20 of ~110: growing │                │ Chana    1     80  5,900 │
│  Sowing [ 14 Sep ] 💾 💬 🗑│                │  my harvest ≈ 8 q        │
│ 🚿 Flood / Borewell 5 HP │                │ [Filter crops][Sort ▾]   │
│ 💧 Next watering 29 Oct  │                │ 🛒 Tur · Sakshi · 3 km   │
│  date  status  mm  m³  h │                │  ₹7,800 · FAQ · Nov–Dec  │
│  ✅ I watered [date][mm] │                │  [ Commit my crop ]      │
└──────────────────────────┘                └──────────────────────────┘
```
