# Review 02 — Farmer panelist: Ramesh Patil, Yavatmal (Vidarbha)

*44 years old, 3.5 acres: 2 acres of rainfed black soil, plus 1.5 acres on a borewell that dries up by March. Cotton and soybean in Kharif; chana or wheat in Rabi if there is water; onion and vegetables on the borewell patch. I studied to 8th standard and speak Marathi. I use an ₹8,000 Android phone with patchy 4G, mostly for WhatsApp and YouTube. I have a KCC loan.*

## 1. My season, my problems

I make my real decision in **May**, not when the rain comes. By May I have to arrange money for seed, DAP and labour, and that means renewing the KCC loan or borrowing from the input dealer at his rate. The dealer gives credit, so in practice he also decides which seed I buy. I do not sow until we get 75–100 mm of rain. If I sow early and the rain stops, I sow again, and that is ₹4,000–5,000 an acre gone.

Who do I trust? First my neighbours. I look at what is standing in their fields and ask what they got last year. Then the krushi seva kendra dealer, though he is selling something. KVK only when a scientist comes to the village. YouTube for spraying and pest videos, but half of those are seed companies advertising. WhatsApp groups pass on mandi rates and rumours.

My fears, in order:
- **Rain.** Late monsoon, a long dry spell in August, then too much rain at harvest that rots soybean pods.
- **Pest.** Pink bollworm destroyed my cotton even though it was "Bt". It has become resistant, so we spray more and pay more ([India Environment Portal](https://indiaenvironmentportal.org.in/news-clippings/the-pink-bollworm-menace-adds-to-maharashtra-cotton-farmers-distress)). In 2017, farmers here died from pesticide poisoning while spraying ([Deccan Herald](https://www.deccanherald.com/amp/story/india%2F15-die-pesticide-poisoning-yavatmal-2027977)).
- **Price.** Soybean MSP was ₹5,328 for 2025-26 and is ₹5,708 for 2026-27. Last year Maharashtra mandi prices fell to around ₹4,170 in September, below MSP ([Global Agriculture](https://www.global-agriculture.com/india-region/soybean-prices-slide-below-msp-despite-lower-acreage-in-kharif-2025/), [2026-27 MSP](https://www.global-agriculture.com/india-region/india-raises-msp-for-kharif-crops-for-2026-27-soybean-seed-sees-7-increase-per-quintal/)). The government procurement centre takes weeks, wants registration and moisture checks, and pays late. The trader pays cash today, so I sold to him below MSP. Cotton MSP is ₹8,267 (medium staple), but CCI buying opens late and the queues are long.
- **Onion crash.** Lasalgaon summer onion has been around ₹1,250 a quintal, with lows near ₹555, while it costs about ₹1,800 to grow ([Commodity Board](https://commodity-board.com/indian-onion-glut-drives-prices-to-one-year-low-farmers-deep-in-losses)). And when prices finally go up, the government releases buffer stock and pushes them down again ([Free Press Journal](https://www.freepressjournal.in/pune/nashik-onion-prices-fall-at-lasalgaon-after-centre-releases-buffer-stock)). I have no storage, so I sell in the glut.
- **Debt.** Yavatmal recorded about 102 farmer suicides between January and May 2026 ([UNI](https://test.uniindia.com/news/west/crime-mah-suicide-farmers/3837184.html)). I knew two of those men. For a farmer, an app that gives bad advice is not a small mistake.

**Why do I over-plant what paid last year?** Because it is the only price signal I have. Everyone sees that tur or onion paid ₹X last year and everyone plants it, and then it crashes. Nobody tells us how much the whole taluka is sowing. If an app could tell me that, it would be worth more than any fertiliser tip.

## 2. Walking through the app, screen by screen

**Login and sidebar.** Everything is in English: "Communities", "Supply Commitments", "crop Prediction". My son can read it but I cannot read it quickly. "Supply Commitments" sounds like a legal paper, and I would be afraid to touch it.

**Step 1, "Your farm & season".** It shows "Farm location: 28.6139, 77.2090". Those numbers mean nothing to me, and I can see from the map that this is Delhi, not my village. The fix it offers (crop_view.py:58) is to "open Google Maps → long-press your field → copy the numbers" and type latitude and longitude into boxes. **I would never do this.** Give me a "my field is here" button that uses the phone's GPS while I stand in the field, or let me pick my village from a list. Kharif, Rabi and Zaid with months is good, I understand that. The box "Also suggest orchard / plantation crops (mango, banana, coconut…)" comes **already ticked** (line 74). Coconut in Yavatmal? That should start unticked. Marathi is in the language list, which is good, but it is a dropdown hidden on the right side.

**Step 2, "Your soil".** "Black / Regur (Deccan, cotton soil)" I recognise. Then come Nitrogen (N), Phosphorus (P), Potassium (K) and pH boxes with numbers like 40, 30, 80. I have a Soil Health Card somewhere, but the card says "low / medium / high" in Marathi with colours. I cannot match it to these boxes. "Estimate pH from soil map (SoilGrids)", what is SoilGrids? Also, the app treats my farm as one soil, but my rainfed land and my borewell land behave like two different farms.

**Step 3, "Local climate (automatic)".** It shows "ERA5", "grid point", "elevation", "Avg humidity %". Fine, it is automatic, so I would just scroll past. But it never asks the most important question of all: **do you have water, and until which month?**

**Results.** This is where I would close the app. The screenshot says "Maize 15% of model votes, Coffee 5%, Lentil 5%", all in red, "Low match". What are "model votes"? Who voted? The context file says that for Nagpur in Kharif it suggests coconut and mango. My village has grown cotton, soybean and tur for 50 years, and **none of the three is even in the top list** (soybean is not in the model at all). If the first screen recommends coffee, I will not open it a second time, and I will tell my WhatsApp group it is nonsense. At least it is honest when it says "Low confidence… discuss with KVK", and I respect that. But a red warning on every result means the app is telling me not to trust it.

The crop names are in Hindi, "मक्का" and "मसूर" (crop_model.py), even when I choose Marathi. In my language maize is "मका", and chana is "हरभरा".

**Step 4, the guide.** There is an audio player, 3 minutes 5 seconds. Audio is the best idea in the whole app. But it is a robot Google voice reading a long essay, and it starts with "first prepare your land well". I know how to prepare my land. I need sowing date, seed rate per acre, which variety, the fertiliser dose in bags, and how many irrigations. Plus a warning of the kind: "If you see rosette flowers in cotton in August, that is pink bollworm, spray X at Y ml per pump."

**What builds trust:** advice that matches what I already know is right (cotton, soybean, tur) and then adds something I did not know, such as "intercrop tur, the price outlook is better", or rupees per acre that look like my own numbers. **What destroys trust:** coffee, percentages, English, and asking me for numbers I don't have.

## 3. What I actually need, ranked

1. **Profit per acre in ₹ and the risk**, for example: "Soybean: cost ₹22,000, likely income ₹30,000–45,000, bad-year loss ₹8,000." Use MSP (soybean ₹5,708, cotton ₹8,267, tur ₹8,450, chana ₹5,875 per [The Statesman](https://www.thestatesman.com/india/union-cabinet-approves-increase-in-msp-for-14-kharif-crops-1503593495.html) / [Tribune](https://www.tribuneindia.com/news/india/govt-raises-wheat-msp-by-6-59-to-rs-2585-per-quintal-for-2026-27)) and real Agmarknet mandi rates.
2. **Who will buy, at what price, before I sow.** A vendor saying "I will take 10 quintal of soybean at ₹5,500 in October" is worth more than any recommendation.
3. **How much area of each crop**: "2 acres cotton+tur, 1.5 acres soybean then chana." Split it the way I farm, rainfed land and borewell land.
4. **Voice in Marathi, both ways.** Let me speak my question and hear the answer. Short pieces, under a minute each.
5. **Work on slow internet**: small pages, audio I can download once and play later, and maybe WhatsApp delivery.
6. **A water plan for my borewell**: "Your well lasts till March, so chana (2 irrigations) is safe and wheat (5–6) is not."
7. **Pest and weather alerts**: pink bollworm pheromone trap counts, and "rain in 3 days, don't spray".
8. **Schemes**: PM-Kisan, PMFBY insurance deadlines, how to register for MSP procurement, and where the nearest CCI or NAFED centre is.
9. **Glut warning**: "Many farmers near you are planting onion this year."

## 4. Trust between vendors and farmers

- **Price fixed upfront, in writing in the app**, with a floor: "not below MSP". If the market rises, share some of it.
- **Small advance at sowing**, even ₹1,000–2,000 an acre, which shows the vendor is serious. At harvest, **payment within 48 hours by UPI**, and show each vendor's payment record.
- **Quality rules written before sowing**: moisture %, grade, and who measures it. Most fights start at the weighbridge and the moisture meter. Allow a third-party check, from the FPO or the APMC.
- **Both sides get ratings**: vendors who reject the crop at harvest when prices fall, and farmers who sell to someone else when prices rise.
- **Go through an FPO or a group.** My 10 quintals mean nothing to a big buyer, but a village group's 500 quintals do.
- **No hidden commission.** Say clearly what the platform takes.

## 5. Questions

**For the CEO:** Who is paying you, me or the vendor? If a vendor backs out and my crop is unsold, what happens? Will you partner with FPOs, KVK Yavatmal, and the Maharashtra agriculture department so the advice carries their name?

**For the ML researcher:** Why does a model without soybean, wheat, onion or tur get shown to Vidarbha farmers at all? Can you train it on district crop statistics (what actually grows in Yavatmal) and then rank crops by profit and risk instead of "votes"? How will you predict a glut before it happens?

**For the UI expert:** Can the first screen be just three things: my village (or GPS), my water (none / till December / till March / all year), and a big Marathi voice button? Can you remove N, P and K from the default path? Can you test it with ten farmers like me, on a ₹8,000 phone, in a field with one bar of signal?

*Ramesh Patil — "शेतकऱ्याला सल्ला नको, भाव हवा" (A farmer doesn't need advice, he needs a price.)*
