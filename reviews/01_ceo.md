# Panel review 01: Agritech CEO (lens: does this make farmers money, and is it a business?)

**Verdict.** Today Krishi Sahay is two separate demos. One is a crop classifier that tells a Ludhiana farmer to grow coffee. The other is a vendor "poll" board with no price on it. Neither moves a rupee into a farmer's pocket yet. The good news is that the polls already hold the most valuable idea in the app: **local forward demand**. Most agritech apps never get that. Build the profit engine around the polls, not around the Random Forest.

## 1. Top problems (ranked)

1. **Recommendations ignore money entirely.** `krishi/crop_view.py:173-176` ranks crops by `predict_proba` alone. No price, cost, yield or market signal goes in. The classes (`krishi/crop_model.py:48-69`) leave out wheat, mustard, soybean, sugarcane, onion, potato, tomato and every vegetable, which are exactly the crops where profit or loss is decided. Telling Thanjavur to grow coffee at 65% (CONTEXT.md) is not just wrong. It costs a farmer a season.
2. **Polls are not commitments.** `create_poll` (`pytest.py:226-260`) stores product, quantity and deadline only. It has **no price, no grade or spec, no delivery location, and no advance payment**. `respond_to_poll` (`pytest.py:263-310`) lets a farmer change the quantity at any time. It marks a poll "fulfilled" once pledges add up (`:296`), even though nothing has been delivered. Real data in `polls.json` shows deadlines on the **same day the poll was created** (onions, created 2025-03-25, deadline 2025-03-25). That is spot buying, not something a farmer can plan sowing around. Onion takes about 120 days.
3. **Price data is fake or anecdotal.** `pytest.py:545-560` seeds made-up prices ("Tomatoes ₹25.5, Delhi"). Prices are otherwise typed in by vendors at city level (`add_market_price`, `:397`). Vendors have every reason to understate them. Free, official, mandi-level daily data exists (see table).
4. **No glut protection, and the app could cause one.** If 300 farmers in a 50 km cluster all see "tomato = most profitable", you have recreated the Kolar crash. Tomato in Kolar fell to ₹2–5/kg and in MP to ₹2/kg in March 2025, and farmers left the crop unharvested ([The Week](https://www.theweek.in/wire-updates/national/2025/03/24/bes9-mp-tomato-prices.amp.html), [Outlook Business](https://www.outlookbusiness.com/explainers/farmers-in-india-struggle-with-falling-tomato-prices-whats-behind-the-price-drop)). In May 2026 onion fetched ₹5–7/kg at the mandi while retail was ₹25 ([Down To Earth](https://www.downtoearth.org.in/amp/story/agriculture/onions-dumped-potato-crops-destroyed-why-falling-farm-prices-are-not-lowering-retail-food-bills)). Potato was down about 41% year on year in April 2026 ([AgroSpectrum](https://agrospectrumindia.com/news/24/33874/tomato-prices-spike-potato-slides-in-volatile-mandi-markets.html)). The app's own planting data is the best defence we have, and today nothing captures it.
5. **Policy reality is not modelled.**
   - MSP only helps where procurement actually happens. PM-AASHA lets NAFED/NCCF procure 100% of state tur, urad and masoor through 2028-29 ([Down To Earth](https://www.downtoearth.org.in/amp/story/agriculture/government-approves-pm-aasha-continuation-allows-procurement-of-tur-urad-masur-under-price-support-scheme)). That is a real price floor the app should surface.
   - Paddy MSP for 2026-27 is ₹2,441/qtl ([DT Next](https://www.dtnext.in/news/business/govt-hikes-paddy-msp-by-rs-72-to-rs-2441qtl-sunflower-seed-sees-steepest-rise-at-rs-622)).
   - Export policy swings onion prices. The 20% duty was withdrawn on 1 Apr 2025 ([Down To Earth](https://www.downtoearth.org.in/amp/story/agriculture/much-awaited-relief-for-onion-farmers-centre-removes-export-restrictions)).
   - Operation Greens has not stabilised TOP prices. Only 34% of the 2024-25 budget was spent by October 2024 ([Drishti](https://www.drishtiias.com/daily-updates/daily-news-analysis/underutilization-of-operation-greens-scheme/print_manually), [DTE](https://www.downtoearth.org.in/amp/story/agriculture/why-has-governments-operation-greens-scheme-aka-tomato-onion-potato-top-failed)). Do not assume the state will rescue a glut.
6. **The 50 km radius is hard-coded crow-flies distance** (`pytest.py:131,157`). Profit depends on freight cost per kg, not on Haversine distance.

## 2. Recommended solution design

**Unit of decision:** one crop-season per farmer, for a chosen area. For each candidate crop *c* (start with roughly 30 crops in the farmer's district from the DES/UPAg crop list, not the 22 Kaggle classes):

```
Yield        Y_c   = district avg yield (UPAg/DES) × irrigation factor (0.6 rainfed … 1.0 irrigated)
Cost         K_c   = DES Cost A2+FL per ha for the state (vegetables: NHB/NHRDF model cost sheets), inflated by CPI
Harvest mo.  t_h   = sowing month + crop duration
Price dist.  P_c   = modal prices for month t_h at the 3 nearest Agmarknet mandis, last 5 years
               P50 = median, P10 = 10th percentile (the "bad year")
Floor        F_c   = MSP × procurement_reliability(state, crop)   (0 for non-MSP crops; ~1 for tur/urad/masoor under PSS; ~0.9 Punjab/Haryana paddy & wheat; ~0.2 elsewhere)
Expected     P̂_c  = max(F_c, P50 × glut_adj_c)
Loss         L_c   = post-harvest loss share (tomato ~0.15, onion ~0.20 without storage, grains ~0.05)

Profit/acre  π_c     = Y_c × P̂_c × (1 − L_c) − K_c
Bad-year     π10_c   = Y_c × max(F_c, P10 × glut_adj_c) × (1 − L_c) − K_c
Score        S_c     = π_c − λ·(π_c − π10_c)     (λ ≈ 0.5 for smallholders; they cannot survive a loss year)
```

**Glut adjustment, using our own data plus mandi arrivals.**
- `arrival_anom = (arrivals last 60 days) / (same window, 3-year mean)` at nearby mandis. When anomaly > 1.2 and the crop is perishable, cut P50 by about 10–25%.
- `app_share = (acres already planned for c in the 50 km cluster, from the app) / (cluster absorption A_c)`.
  - `A_c = vendor-committed qty + α × avg harvest-window arrivals at nearest mandis` (α ≈ 5–10% is what the cluster can add without moving the price).
- `glut_adj_c = 1 − β × max(0, app_share − 1)`, with β ≈ 0.3 for perishables and 0.1 for grains/pulses.

**How much to grow (this is the core feature).**
- `contracted_area_c = Σ(accepted poll qty for this farmer) / Y_c`. This acreage is priced and safe.
- `spot_area_c = min(remaining land × risk_cap_c, remaining cluster quota)`, where `risk_cap_c` is 25% of land for TOP crops and 100% for MSP-procured crops.
- Output looks like: **"2 acres tur (MSP floor ₹/qtl), 0.5 acre tomato contracted to Vendor X at ₹12/kg for 4 t, 0.5 acre onion spot. Bad-year income ₹__, normal ₹__."** Always show the bad-year number.

**Anti-herding.** Every plan the farmer saves is written to `crop_plans.json` (farmer_id, crop, acres, sow date, harvest week). The cluster quota for each crop is `A_c / Y_c` acres. When the quota fills, that crop drops in the ranking for everyone else and the app shows: "Already 140 acres of tomato planned near you for the same harvest weeks." Stagger harvest weeks as well, because a glut is about timing as much as volume. **This planting registry is the moat.** Neither the government nor the mandi has acreage intentions before sowing.

**Data flow:**
1. A nightly job pulls Agmarknet/data.gov.in data for the district's mandis into a `prices/` parquet file.
2. MSP and DES cost tables are kept as static CSVs refreshed each season.
3. The plan engine (`krishi/profit.py`) reads those tables, the polls and `crop_plans.json`, and returns a ranked plan.
4. The Random Forest becomes an agronomic suitability filter only. Exclude a crop only if a district-crop history table (DES/UPAg area statistics) says nobody grows it there.

## 3. Verified data sources

"Reachable" = I got HTTP 200 from here on 2026-10-03. The data.gov.in API host refused connections from our network. It is documented and widely used, so test it from an Indian IP with your own key.

| Source | URL | Access | Coverage | Frequency | Verified |
|---|---|---|---|---|---|
| Agmarknet 2.0 (price + arrivals) | https://agmarknet.gov.in | Web report/CSV export; portal upgraded Nov 2025, mobile app | 4,300+ mandis, 300+ commodities incl. all vegetables, min/max/modal price + arrivals (t) | Daily | Y (200) |
| data.gov.in mandi price dataset | https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi | REST `api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`, free API key; also `variety-wise-daily-market-prices-data-commodity` | Agmarknet feed, current day only. **History: archive it yourself** | Daily | Partial (documented; API refused from here) |
| eNAM trade data | https://enam.gov.in/web/dashboard/trade-data | Web dashboard (no public API) | 1,522 mandis, 1.79 cr farmers, ₹4.4 lakh cr traded by Jun 2025 ([LS answer](https://eparlib.sansad.in/bitstream/123456789/2998079/1/AU1504_HVk1tf.pdf)) | Daily | Y (200) |
| CACP MSP | https://cacp.da.gov.in | PDF price-policy reports → hand-built CSV | 22 MSP crops + FRP sugarcane, includes A2+FL and C2 projections | Per season | Y (200) |
| DES Cost of Cultivation | https://desagri.gov.in/document-report-category/cost-of-cultivation-production-related-data-archive/ ; mirror https://ckandev.indiadataportal.com/dataset/cost-of-cultivation | Excel/PDF; IDP CSV | ~25 principal crops by state, A1…C2 per ha, yield. Limited vegetable coverage (onion, potato in some states) | Annual, about 2-year lag | Partial (desagri timed out here; IDP mirror indexed) |
| UPAg | https://upag.gov.in | Web dashboards | Area, production, yield, prices, MSP in one place (MoA&FW, since 2023) | Weekly to seasonal | Y (200) |
| NHB price/arrival bulletins | https://nhb.gov.in/info_bulletin.html | Web/PDF reports | Fruits and vegetables, major markets; also cold-storage database | Daily/weekly/monthly | Y (200) |
| DoCA Price Monitoring | https://fcainfoweb.nic.in | Web reports | Retail and wholesale prices of 22 essentials incl. onion, potato, tomato, about 500 centres | Daily | Y (200) |

## 4. Vendor side: making demand real

- **Why a vendor would post:** guaranteed, graded, aggregated volume on a date, below the mandi landed cost (no commission agent's 6–8% cut, less freight). Target vendors are FPOs, processors, hotel/QSR kitchens, modern-trade collection centres and exporters. Single traders are a weaker fit.
- **The poll must become a forward contract:**
  - Price type: fixed, floor, or "mandi modal on delivery day ± x".
  - Grade spec (Agmark/FAQ size and defects).
  - Delivery window of at least one crop cycle in the future, and a pickup point.
  - A token advance of 2–5% held by the platform or FPO.
  - Penalties for side-selling and rejection.
- **Trust:**
  - The reference code (`pytest.py:268`) becomes a contract ID with a QR code, scanned at weighbridge and delivery.
  - Two-way ratings, on-time payment rate, rejection rate.
  - Lock a farmer's quantity once sowing is confirmed. Today it is editable forever.
- **Matching:** keep the 50 km radius but rank by landed cost (`freight ₹/kg × road km`). Let an FPO aggregate many small pledges into one vendor contract.

## 5. Business model and go-to-market

- **Free for farmers.** Revenue comes from:
  - a 1–2% take on contracted GMV, collected from the vendor;
  - a vendor subscription for demand-planning dashboards (the planting registry is gold for processors);
  - later, input bundles (seed/fertiliser) matched to the plan, and credit underwritten by contracts.
- **Go-to-market:** one district, one FPO, 2–3 crops (e.g., one MSP pulse + tomato + onion). Onboard farmers through FPO and KVK staff with WhatsApp/IVR. The first 10 vendors are signed by hand. Prove one season in which contracted farmers beat the mandi price, then replicate.

## 6. Questions for other panelists

- **Farmer:** Would you accept a fixed price at sowing that is below a good-year mandi price, in exchange for certainty? What token advance would make a vendor's promise believable? How many acres do you dare to put in tomato?
- **ML researcher:** Can we replace the Kaggle Random Forest with a district-crop suitability prior (DES area statistics) plus a harvest-month price model (seasonal naive + arrivals regression), and backtest π10 against 2023–2026 crashes? How should a vendor-demand prior be calibrated when there is little data?
- **UI expert:** How do we show "normal year vs bad year income" and "140 acres already planned near you" to a low-literacy user, with audio? How should "accept contract" work so it is never a one-tap mistake?

## 7. Must-haves

**v1 (1–2 weeks)**
1. Nightly Agmarknet/data.gov.in ingestion and history archive. Delete the fake seed prices.
2. Static MSP and DES cost CSVs, and a crop list that includes wheat, mustard, soybean, onion, potato, tomato and 10 or more vegetables.
3. `profit.py` producing π, π10 and a score. Results page ranks by profit, with the Random Forest as a filter only.
4. Poll fields: price type and value, grade, delivery window, pickup point. Quantity locked after acceptance.
5. A `crop_plans.json` registry plus the cluster quota and glut adjustment.
6. An area and land input, and a "how much to grow" plan output.

**Later**
- Road-distance landed cost.
- Escrow/advance payments.
- eNAM/FPO integration.
- Price forecasting model.
- Storage/warehouse-receipt option for onion and potato.
- Export-policy alerts.
- Credit and insurance tied to contracts.
- Satellite acreage checks against declared plans.
