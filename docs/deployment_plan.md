# Deployment and scale-up plan

## 1. Who, where, which crops

| | Phase 0 (now) | Phase 1 pilot | Phase 2 | Phase 3 |
|---|---|---|---|---|
| **Geography** | Yavatmal reference site (Maharashtra seed rows) | One cluster in Yavatmal district (about 5 villages) | Other districts of Maharashtra, then the other Atal Bhujal states (Gujarat, Haryana, Karnataka, Madhya Pradesh, Rajasthan, Uttar Pradesh) | National, state by state as crop tables are added |
| **Farmers** | Demo accounts | 60–80 smallholders (rain-fed + borewell/well), phone + PIN, set up by an FPO or field agent | A few thousand through FPOs and panchayats | Open sign-up |
| **Crops** | 30 in the table | Rabi: chana, wheat, mustard, onion, masoor. Kharif: cotton, soybean, tur, sesame, jowar | Add the state's major crops, vegetables with measured costs | Region-specific tables |
| **Languages** | 12 with voice, 20 text | Marathi, Hindi (reviewed by native speakers) | + Bhashini for all 22 | all 22 |
| **Partners** | none | One FPO, the local Krishi Vigyan Kendra, 3–5 vendors, the gram panchayat | State agriculture / energy agencies, DISCOM feeder data | PM-KUSUM and Atal Bhujal programme teams |

Pilot crops are chosen from where the app already has measured (not estimated) numbers; vegetables enter only once local cost and price data replace the estimates.

## 2. Farmer and user profiles

- **Smallholder, rain-fed plus a well or borewell that fails before summer** (the core user): decides crops in May (Kharif) and October (Rabi), borrows against the crop, sells to a local trader or the mandi, reads little, uses a shared basic phone. Needs: normal-year and bad-year rupees, water by plot, a buyer before sowing, Marathi/Hindi voice.
- **FPO / field agent:** onboards farmers, reads the village screen, aggregates produce.
- **Vendor / trader / processor:** wants quantity and quality at a known date.
- **Gram panchayat / Water Security Plan team:** wants demand against supply before the season.

## 3. Unit economics (formulas; only the verified inputs have numbers)

| Item | Per farmer per month | Source / status |
|---|---|---|
| Language model | about **US$0.05** (30 chat turns × about 1,500 tokens × US$1.04 per million tokens) | rate from Together's model list; token counts are an estimate |
| Speech-to-text | not confirmed | Whisper on Together; check the account's rate |
| Translation / text-to-speech | free public endpoints in the pilot | **not suitable for scale**; replace with Bhashini (free) or a paid API |
| Weather, prices, soil | free (Open-Meteo, CEDA, SoilGrids) | free tiers; confirm terms for commercial use |
| Hosting | not costed | depends on the platform chosen |
| Field agent | not costed | the main real cost in the pilot |

Who pays (hypotheses to test, not facts): vendors and processors pay for demand matching and the supply-coming dashboard; programmes (Atal Bhujal, PM-KUSUM state agencies) pay for village-level water and pump-sizing analytics; farmers use it free. Farmer-side value per acre comes from the simulation (water, energy, yield) and the avoided-loss upper bound, to be measured in the pilot.

## 4. Rollout steps

1. **Weeks 1–2: harden.** Native-speaker review of Marathi and Hindi; replace estimated vegetable costs with local data; enter the farmers' real pump details; test on low-end phones and slow networks.
2. **Weeks 3–6: pilot.** Onboard the cluster; vendors post real offers; field agent checks the first plans.
3. **Season 1: measure.** Matched groups (20 with the schedule, 20 without), hour-meters or flow meters on each pump, litres or kWh, harvest weight per acre, price received. Replace every simulation assumption with a measured value.
4. **Season 2: scale** within the district via the FPO and the panchayat; add the district's crop rows and Bhashini voice.
5. **Then** other Atal Bhujal states, state by state.

## 5. Risks and how they are handled

| Risk | Handling |
|---|---|
| Wrong or stale prices and costs | Cited table, estimates flagged and capped, live Agmarknet prices shown beside offers, pilot data replaces estimates |
| Over-trust in a model | Usual/bad-year ranges, "ask your KVK" line, no profit promises, estimated-number crops never ranked first |
| Language errors | Native review, English text one tap away, text always shown beside audio |
| Free translation/TTS endpoints fail at scale | Fail soft to text; Bhashini adapter in place |
| Chat and personal data | Phone + PIN (hashed), no public farmer list, chat stored as text per account, Clear button; move to a managed database and add consent text before the pilot |
| Everyone follows the same advice and herds | Planting registry, caps per crop and per cluster, warnings when nearby plans pile up |
| Power-window assumptions wrong | The farmer enters their own supply hours |
| Vendors default | Offers recorded with reference codes; payment record per vendor from the pilot; escrow only later |

## 6. Success measures for the pilot

Water and energy per acre against matched farmers; yield and price received; unsold or discarded produce; share of plans that include a confirmed buyer; weekly active farmers who return; percentage of advice farmers say they understood without help.
