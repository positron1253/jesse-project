# Krishi Sahay: plan the crop to the water, schedule the water and power, sell what you grow

*Challenge 01 — Sustainable Agriculture: Energy, Water & Productivity*

## 1. The problem, in Indian terms

Farm power in India is large, subsidised and mostly unmanaged. Agriculture uses roughly **19–23% of the country's electricity**, groundwater supplies about **48% of irrigation water**, and there were about **22 million electric pumps** in 2021 (secondary compilations; the sources differ on the exact share). Irrigation timing is mostly by habit. The brief itself puts post-harvest losses at **15–20% of produce value**.

The smallholder's day-to-day problems are specific:

- **When and how much to water.** Fixed-date flood irrigation ignores rain and the soil's real need. In Maharashtra, farm feeders have often supplied power at night; the state promised 8 hours of daytime supply on agriculture feeders under MSKVY 2.0, and night irrigation exposes farmers to snakes and wild animals ([Hitavada](https://www.thehitavada.com/Encyc/2023/6/10/State-forms-new-solar-co-for-Mukhyamantri-Saur-Yojana-2-0-.html); 2023 reporting, current status not verified).
- **Which crop to plant.** Recommendation tools rank crops by soil match or by this year's rain. A dry spell or a flood in a later month is invisible to them. Costs and prices vary hugely, so a "best crop" can lose money in a bad year.
- **Where to sell.** Farmers plant what paid last year, everyone does the same, and the glut is wasted or sold below cost.
- **Language and literacy.** Advice that needs reading and typing in English does not reach most smallholders. Chatbots exist (Kisan e-Mitra has answered over 93 lakh queries; Bharat-VISTAAR is rolling out), but they answer questions; they do not turn a farmer's own land, water and local buyers into a plan.

## 2. What we built

**Krishi Sahay is a decision platform that connects four things nobody connects today: the crop, its water and power, the climate it will actually face, and the buyer.** A farmer, in their own language and by voice, goes through:

1. **Location.** On login the phone's GPS fills in the farm location and the app shows the place name (village, district, state). If the farm is elsewhere, the farmer searches a village or types latitude and longitude, and can save it to their profile. Everything below uses this location.
2. **Water and land.** How long their well or canal lasts (rain only / till December / till March / all year) and the land split into watered and rain-only plots.
3. **Soil.** If the farmer has a soil test, they type the numbers (pH, nitrogen, phosphorus, potassium, organic carbon) and see an approximate Low/Medium/High reading. If not, the app estimates pH, organic carbon, texture and water-holding capacity from satellite soil maps (SoilGrids) for the location. Nitrogen, phosphorus and potassium cannot be read from a map and stay unknown.
4. **Sowing date.** The farmer chooses when to start sowing. Every risk, water and temperature number uses that date, so the same crop can be a good or a bad choice depending on when it starts.
5. **Crops.** The crops that suit that land, ranked by profit per acre in a usual year **and a bad year**, with a plain risk light. Each crop is tested against the **last 30 seasons at that farm** from the chosen sowing date, on that plot's own water supply. Cards say things like "water-short in 23 of the last 30 seasons here", warn when very heavy rain (IMD's 115.6 mm/day class) is common, and show the latest mandi price against the usual harvest-time price. Market prices are refreshed live from Agmarknet in the background, with the stored five-year prices as a fallback.
6. **Plan and guidance.** How many acres of each crop, with caps so nobody puts the whole farm into a crop that can crash, a cultivation and irrigation guide as audio, and a voice assistant that knows the farmer's land, plan and weather and remembers the conversation (12 languages with voice today, 20 with text, all 22 with a free Bhashini account).
7. **My farm.** The selected crops with sowing dates and growth stage, the farm's irrigation system (method, source, pump, power, supply hours), and a **watering schedule from the sowing date**: observed weather up to now, the 15-day forecast, then a typical year. The farmer records when they actually watered and the next dates update. Water, pump hours, energy and CO₂ come with it.
8. **Sell.** Every open buyer need within 50 km (Haversine), all crops and future delivery windows, with a demand summary, filters, the farmer's own expected harvest alongside, and a two-step "commit my crop" with a reference code. The saved plan feeds a planting registry; buyers see totals only, never names.
9. **Village.** Everyone's saved plans added up into the village's irrigation demand, pumping power and CO₂, against the water available (an input from the Water Security Plan), with suggestions where a crop change would help. This is the bottom-up version of what Atal Bhujal Yojana asks gram panchayats to do ([PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2022/mar/doc202233033201.pdf)).

A Home screen with large icon tiles is the menu; every other page has a big Home button.

See `docs/architecture.svg` for the system, data, water/energy and money flows.

## 3. How the core works

**Climate risk and irrigation.** A daily FAO-56 soil-water balance. For every candidate crop and each of the last 30 seasons we simulate evapotranspiration (ERA5 via Open-Meteo), rain, root-zone depletion and, where water is available, irrigation. Yield loss follows the FAO-33 relation `1 − Ky(1 − ETa/ETc)`. The result is a distribution: median year, bad year (10th percentile), and the share of poor years. Excess rain is reported as the share of past seasons with a very heavy rain day. Seasonal forecasts are **not** used to rank crops because their skill for the Indian monsoon is limited at local scale; the long climate record is the safer basis.

**Profit and risk.** Profit per acre = yield × farm-gate price × (1 − post-harvest loss) − cost, using a cited seed table (CACP costs, NHB/DES yields, Agmarknet prices through the CEDA open API, MSP from PIB, NABCONS loss shares). The bad year combines low price with the climate-driven bad yield. Crops whose numbers are estimates are never called low risk, are discounted in ranking, are never ranked first while a measured-data crop is profitable, and are capped at a quarter of the land.

**Water → power → money.** Pumped volume is converted to energy with `E = ρ g H V / (3.6·10⁶ η)` and to CO₂ with the CEA grid factor (0.727 kg/kWh) or 2.68 kg/L for diesel. Pump sizing and payback take the farmer's own tariff or diesel price and the PM-KUSUM Component B split (30% central + 30% state, farmer 40%) as inputs; no prices are built in.

## 4. Key assumptions (all listed in `reports/impact_report.md` §8)

Verified: FAO-56 Kc, root depth and depletion tables; FAO-33 Ky for nine crops; IMD rain classes; the grid emission factor; the diesel factor; the PM-KUSUM B subsidy split. **Assumptions, not verified:** soil water-holding capacity by soil class, crop stage lengths, effective rain 85%, pump lift 40 m and efficiency 35%, 60 mm per flood irrigation, Ky = 1.0 where no verified value exists, 1.25 kWp of panels per kW of pump, and the cost and price figures marked "estimated" in the crop table (mostly vegetables). **Not modelled:** waterlogging, heat stress, pests, market-price effects on the water results.

## 5. Why it suits Indian smallholders

- **Voice first, native language, no typing coordinates.** Hindi, Marathi, Bengali, Telugu, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Nepali and English work today; Odia, Assamese and seven more are text-only until a free Bhashini account is connected.
- **Designed for a basic phone and thin data** (light pages, audio generated once and cached, only the farmer's own inputs needed). This has **not yet been tested** on low-end devices or slow networks; the pilot plan includes that test.
- **Honest numbers.** "Usual year" and "bad year" in rupees, plain-word reasons, a "ask your KVK" line when confidence is low, and no promise of profit.
- **Rain-only and well-irrigated land are planned separately**, which matches how Vidarbha-type farms are actually split.
- **No hardware needed.** Soil moisture is modelled from weather; a sensor can be added later (see `docs/design_artifacts.md`).

## 6. Quantified benefit (simulation; baseline stated; see `reports/impact_report.md`)

Reference site Yavatmal, Maharashtra, black soil, 30 seasons of weather. Baseline: the crop's usual number of flood irrigations on fixed dates, 60 mm each, no rain adjustment. Per acre per season (median; range across seasons in the report):

| Crop | Water saved by scheduling (flood) | Water saved by scheduling + drip | Yield vs baseline |
|---|---|---|---|
| Cotton (Kharif) | 17% | 44% | same |
| Tomato (Rabi) | 35% | 57% | same |
| Onion (Rabi) | uses 20% more | 20% less | +28% relative yield |
| Wheat (Rabi) | uses 67% more | uses 11% more | +7% relative yield |
| Chana, mustard, tur | uses more | uses more | +59% / +51% / +17% relative yield (usual practice is a deliberate 2-irrigation shortcut) |

The honest message: where the usual practice already waters enough (cotton, tomato, and onion with drip), scheduling and drip save between a fifth and over half of the water at equal or better yield and cut pump energy and CO₂ in proportion (cotton: about 202 kWh and 147 kg CO₂ per acre per season at the assumed pump). Each single watering is capped at 60 mm net, what a farmer can realistically apply. Where the usual practice is a shortcut, the schedule spends more water and lifts yield; that is a productivity gain, not a saving, and we report it as such. The largest water lever is **crop choice on the same well**, which the village roll-up and the ranking make visible. Post-harvest losses at stake are quantified per crop (for example tomato about ₹24,700 per acre at an 11.6% loss share) as an **upper bound** for what buyers lined up before sowing could protect; the actual reduction is a pilot hypothesis, not a result.

## 7. Feasibility and affordability

Software only, open data, free weather and price APIs, a farmer needs a basic phone. Variable cost per farmer is tiny: the language model costs about US$1.04 per million tokens (Together's published rate for the model in use), so 30 chat turns a month at about 1,500 tokens each is roughly **US$0.05 per farmer per month**. Hosting and the speech-to-text price were not confirmed and are not costed. Text-to-speech and translation currently use free public endpoints that are fine for a pilot but not for scale; Bhashini (free, government) is the scale path. See `docs/deployment_plan.md`.

## 8. Sustainability

Less pumping means less electricity or diesel per unit of crop (energy and CO₂ computed from first principles with stated factors), less groundwater drawn when scheduling and efficient methods replace calendar flooding, and crops matched to the water that exists. The village roll-up lets a panchayat see demand against supply before the season, which is where groundwater is actually protected.

## 9. Limits we state plainly

Only Maharashtra has state-specific rows; vegetables' costs and yields are estimates; the water model covers drought, not waterlogging or pests; the benefit figures are a simulation until the pilot measures them; the Hindi and Marathi text is machine-translated and needs native review; Bhashini voice for the extra languages is built from its documentation and untested against the live service.
