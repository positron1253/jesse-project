# Submission pack: Challenge 01, Sustainable Agriculture (Energy, Water & Productivity)

| Brief asks for | Where |
|---|---|
| Detailed solution write-up (how it works, assumptions, why it suits Indian smallholders) | [solution_writeup.md](solution_writeup.md) |
| System / architecture diagram (components, data, energy, money flows) | [architecture.svg](architecture.svg) |
| UX wireframes, data-model designs, process and service design, sensor/pump design | [design_artifacts.md](design_artifacts.md) |
| Software prototype | the app: `py -3.11 -m streamlit run pytest.py` (see the repository README) |
| Quantified benefit against a stated baseline, with assumptions | [../reports/impact_report.md](../reports/impact_report.md) (regenerate with `py -3.11 scripts/run_impact.py`) |
| Deployment and scale-up plan: crops, geographies, farmer profiles, unit economics | [deployment_plan.md](deployment_plan.md) |

## How this maps to the judging criteria

| Criterion (weight) | Where it is addressed |
|---|---|
| Problem understanding and idea quality (20%) | write-up §1–2; expert reviews in `../reviews/` (CEO, farmer, ML researcher, UI expert) |
| Architecture and design (20%) | `architecture.svg`, `design_artifacts.md`, `../krishi/` module layout |
| Impact and measurability (25%) | `../reports/impact_report.md`: stated baselines, ranges across 30 seasons, sensitivity, honest negatives, pilot validation plan |
| Feasibility and affordability (20%) | write-up §7, `deployment_plan.md` (software only, open data, per-farmer cost, risks) |
| Sustainability (15%) | water, pump energy and CO₂ per acre and per village (`impact_report.md` §2–5, §7); village water roll-up |

Everything quantified is a **simulation against a stated baseline**, not field evidence. Assumptions that are not verified from a published source are listed in the report (§8) and in `../krishi/water.py`.
