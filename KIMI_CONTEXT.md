# VC Scout — Project Context for Kimi

## What this project is

VC Scout is a Cornell capstone project (Team 17, Project #32) that builds a machine learning pipeline to predict the valuation of unicorn companies — private startups worth $1B or more. The goal is to give venture capitalists a quantitative tool to estimate how large a company could grow, conditional on it already reaching unicorn status.

The repo is at: https://github.com/nathanaelguitar/team17-vc-scout-model

## What we built

The pipeline follows a medallion architecture:

- **Bronze** — raw ingested data from a curated audited startup master (75,230 rows, sourced from CB Insights, Wikipedia, Crunchbase 2015, and SEC Form D filings)
- **Silver** — cleaned and validated unicorn + soonicorn rows (2,736 rows after deduplication, funding correction, and removal of impossible data)
- **Gold** — two model-ready outputs:
  - `valuation_gold.csv` — 827 unicorn rows with log-transformed valuation and funding, used for the regression model
  - `classifier_gold.csv` — 3,422 rows with controls capped at 20%, for a future classifier

The sklearn model (`model_pipeline.py`) runs six algorithms against the gold valuation dataset. The current champion is **Random Forest** (test R² = 0.363, 5-fold CV R² = 0.329).

### Features used

| Feature | Type | Permutation importance |
|---|---|---|
| ln(Funding) | Numeric | 0.742 — dominant signal |
| Continent | Categorical | 0.051 |
| Industry group | Categorical | 0.035 |
| Years to unicorn | Numeric | 0.012 |
| Select investor count | Numeric | ~0.000 (capped at 4 by source) |
| Era (Pre-2021 / 2021 / Post-2021) | Categorical | ~0.000 |

### Industry groups (only 5 in current data)

Enterprise Software, AI & Data, Fintech, Hardware & Industrials, Health & Bio

## The core problem: data is too thin

827 rows is a small dataset for ML. The model explains only ~36% of valuation variance. The main reasons it can't do better:

1. **Survivorship bias** — every row already crossed $1B, so the model can't learn what separates a $1B company from a $10B company from first principles; it only sees winners
2. **Weak feature set** — funding amount alone drives 74% of the model's signal. We have almost no information about the company itself: no team data, no growth metrics, no product description, no investor quality, no revenue
3. **Capped investor count** — CB Insights only lists 3–4 "select investors" per company, so investor_count tops out at 4 and carries no information
4. **Only 5 industry buckets** — the original data collapses 15+ sectors into 5 groups, losing resolution
5. **No time-series** — we have a single funding snapshot per company, not a trajectory of rounds

## Why we need PitchBook data

PitchBook is the most comprehensive private-market database available. Adding it would fix nearly every gap above.

### Specific fields we need from PitchBook

**Funding rounds (deal-level, not just total)**
- Round date, round size, round type (Seed / Series A / B / C / Growth)
- Pre-money and post-money valuation at each round
- Lead investor name and fund type (corporate VC, tier-1 VC, family office, etc.)

This turns each company from a single point into a funding trajectory. The shape of how a company raised — how fast, how much dilution, which investors led — is far more predictive than total funding alone.

**Investor quality signals**
- Whether a tier-1 fund (a16z, Sequoia, Accel, etc.) participated
- Number of co-investors per round
- Whether the lead investor has a track record of backing unicorns

The current `select_investor_count` field is capped at 4 and tells us nothing about investor quality. PitchBook has full investor rosters and fund classifications.

**Company fundamentals**
- Employee count over time (headcount growth is a strong proxy for revenue growth)
- Revenue range or ARR band (available for many companies in PitchBook)
- Last known valuation and the date it was set
- Business model (B2B SaaS, marketplace, deep tech, etc.)

**Exit outcomes**
- IPO price and post-IPO market cap
- Acquisition price and acquirer
- Time from last private round to exit

Exit data lets us close the loop: we can train a model that predicts not just "what is this company worth now" but "what will it be worth at exit."

**Broader company coverage**
- PitchBook covers ~3.5M companies globally, including pre-unicorn companies
- This lets us add a proper negative class: companies that raised $50M–$500M and never became unicorns
- Without this, any classifier we build will only have seen success stories

### What this unlocks for the model

| Current state | With PitchBook |
|---|---|
| 827 unicorn rows | 5,000–20,000 rows with valuation data |
| 1 funding snapshot | Full round-by-round trajectory |
| 5 industry groups | 20+ sector classifications |
| Investor count capped at 4 | Full investor roster + tier labels |
| No revenue data | ARR band / revenue range for ~40% of companies |
| No headcount data | Employee count at multiple time points |
| No exit ground truth | IPO/acquisition price and timing |

With PitchBook data the model could realistically reach test R² of 0.55–0.70 on valuation prediction, and a unicorn classifier (will this company reach $1B?) becomes viable.

### Access path

PitchBook offers academic licenses. Cornell likely already has institutional access through the SC Johnson College of Business. The team should:

1. Check if Cornell has a PitchBook academic subscription (contact the library or the finance department)
2. If yes, request a bulk export of North American and European companies with at least one funding round since 2010
3. Key tables to request: `companies`, `deals`, `investors`, `exits`, `people` (founder data)

A Crunchbase Pro export is a reasonable fallback if PitchBook access can't be obtained — it covers similar fields at lower depth.

---

*Repo state as of 2026-07-29. Champion model: Random Forest, test R² = 0.363, trained on 827 gold-layer rows.*
