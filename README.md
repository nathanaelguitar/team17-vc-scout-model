# VC Scout: Startup Valuation and Unicorn Screening

Cornell Capstone, Project #32: Startup Growth and Investment.

This repository contains Team 17's Cornell capstone work on startup valuation
and unicorn screening. It includes the original valuation benchmark, the
round-level Capital IQ classifier, the submitted presentation, and the data
quality checks used to produce them.

## Contents

| Path | What it is |
|---|---|
| `deliverable/Team17_Model_Definition_Initial_Results.pptx` | The submission deck (10 slides) |
| `deliverable/Team17_Model_Definition_Initial_Results.pdf` | PDF version for quick preview |
| `model_pipeline.py` | End-to-end pipeline: cleaning, feature engineering, train/test split, cross validation, hyperparameter tuning, model comparison, diagnostics, sensitivity checks, chart rendering |
| `model_stats.json` | Every number in the deck, produced by the pipeline (source of truth) |
| `charts/` | The five deck charts as transparent PNGs |
| `data/gold/` | Clean model inputs and Capital IQ classifier outputs |
| `models/` | Saved classifier, metrics, and feature importance tables |
| `docs/` | Data limitations and planned extensions |
| `analysis/audit_trail/` | Supporting valuation audit tables and presentation inputs |
| `data/Unicorn_Companies.csv` | The dataset (1,074 unicorn companies, from the Kaggle "Startup Growth and Investment" dataset) |
| `dashboards/` | The VC Scout interactive dashboard and the project status dashboard (self-contained HTML; open directly in a browser or serve with `python3 -m http.server`) |

## Valuation benchmark

Predict `ln(Valuation in $B)` for unicorn companies from publicly listed fields. Because every row already reached unicorn status, this is framed strictly as a conditional-on-unicorn valuation-scale model, never as a startup success predictor (survivorship bias).

**Features:** ln(Funding), Industry (15 sectors), Continent, Era (Pre-2021 / 2021 / Post-2021), Years to unicorn, Investor count.

**Sample:** 1,074 raw rows, 1,060 modeled (excluded: 12 unknown funding, 1 zero funding, 1 negative years-to-unicorn anomaly). 80/20 train/test split (848/212, seed 17), 5-fold cross validation inside the training set. Funding efficiency is deliberately NOT a feature because it contains the target.

## Results

| Model | CV R² | Test R² | MAE (ln) |
|---|---|---|---|
| Baseline (mean) | -0.01 | 0.00 | 0.62 |
| Linear (OLS) | 0.36 | 0.45 | 0.45 |
| Ridge (alpha=30) | 0.37 | 0.45 | 0.45 |
| Lasso (alpha=0.005) | 0.38 | 0.45 | 0.45 |
| KNN (k=25) | 0.41 | 0.47 | 0.46 |
| Random Forest (600 trees, depth 4) | 0.44 | 0.49 | 0.44 |
| **Gradient Boosting (200 trees, lr 0.03, depth 2)** | **0.46** | **0.51** | **0.44** |

- Champion: **Gradient Boosting**, tuned by GridSearchCV over 99 hyperparameter combinations across five grids.
- Median absolute error: 37% of valuation vs 77% for the naive baseline.
- Funding elasticity from the OLS companion model: about 0.57 (a 1% funding increase is associated with a 0.57% higher valuation, so diminishing returns; confirms EDA hypothesis H3).
- Permutation importance: ln(Funding) dominates (1.16 R² drop when shuffled), Industry (0.06) and Continent (0.05) are secondary.
- Robustness: test R² stays at 0.51 when the 520-company 2021 cohort is excluded and when valuations are winsorized. Bootstrap simulation (2,000 resamples): 95% CI for test R² is 0.39 to 0.61.

## Reproduce

```bash
python3 -m pip install -r requirements.txt
python3 model_pipeline.py
```

Deterministic (seed 17). Regenerates all charts in `charts/` and `model_stats.json`. Runtime is a couple of minutes on a laptop.

## Expanded dataset (75,230 companies)

`data/expanded/startup_master.csv` widens the sample from 1,074 unicorns to 75,230 companies so unicorns can be compared against soonicorns and funded non-unicorn control groups. Built by `build_expanded_dataset.py` from the committed snapshots in `data/raw/` (refresh them with `fetch_raw_data.sh`).

| Tier | Rows | What it is |
|---|---|---|
| `unicorn_current` | 1,400 | On the CB Insights live unicorn list, July 2026 valuations (includes 2023-2026 entrants missing from our 2022 file) |
| `unicorn_exited` | 207 | Former unicorns with exit outcome, date, and exit valuation (IPO / acquired / closed), from Wikipedia (CC BY-SA) |
| `unicorn_delisted` | 223 | In our 2022 snapshot but no longer listed and no recorded exit |
| `soonicorn_proxy` | 908 | Operating non-unicorns with $100M+ total funding (funding as valuation proxy, since private valuations are not public) |
| `control_funded` | 64,150 | Funded non-unicorn startups from the Crunchbase Dec-2015 open export (CC-BY): funding totals, industry, geography, founded dates, and operating/acquired/IPO/closed status |
| `control_accelerator` | 8,342 | YC (current, daily-updated), Techstars, and 500 Global portfolio companies with outcome labels but no public funding amounts |

Extras:
- `data/expanded/unicorn_valuation_panel.csv`: 1,672 unicorns tracked across four valuation snapshots (2022, 2024, 2025-07, 2026-07); 838 companies have all four points. Example: Stripe 95 to 70 to 70 to 159 ($B).
- `data/expanded/formd_2026q2_raises.csv`: 5,728 US operating-company raises filed with the SEC in Q2 2026 (Form D, public domain), including 238 mega-raises of $100M+ sold, a current-quarter soonicorn signal.

Honest notes: valuations exist only for the unicorn tiers (private non-unicorn valuations are not public anywhere); the big control group's funding and status are as of the Dec-2015 snapshot (no free bulk source is fresher); the soonicorn tier uses funding as a proxy for valuation and is labeled accordingly. Every row comes from a verified real source; several candidate datasets were rejected during sourcing for being synthetic.

**Attribution:** unicorn valuations from CB Insights' public Global Unicorn Club list (2024 / 2025 / 2026 snapshots); former-unicorn outcomes from Wikipedia (CC BY-SA 4.0); control group from the Crunchbase 2015 Data Export (CC-BY, via the notpeter/crunchbase-data mirror); accelerator data from the YC public directory (via yc-oss/api, MIT), Techstars' public portfolio index, and 500 Global's public portfolio API; current raises from SEC EDGAR Form D quarterly data sets (public domain). Academic coursework use.

## Capital IQ unicorn classifier

The original matched-pair classifier remains in the repository for audit
purposes, but it is not the recommended screening model. Its controls are
matched at a positive company's outcome date and do not have verified
three-year outcome coverage; its very high historical AUC is therefore not a
credible population-probability result. See
[`docs/layer_b_model_audit.md`](docs/layer_b_model_audit.md).

The runnable replacement available from the existing transaction exports is a
transaction-observed ranking model. It uses a company’s first two observed
financings to rank the chance that Capital IQ subsequently records a `$1B+`
event within three years. It does not emit a unicorn probability.

```bash
python3 scripts/layer_b_transaction_observed_ranker.py
pytest -q
```

The current ranker trains through 2019, selects its model in 2020, and has an
untouched 2021–2022 test result of ROC-AUC 0.804 (bootstrap 95% interval
0.710–0.879), PR-AUC 0.642, and 2.49x top-decile lift over its observed-event
base rate. It writes a fitted artifact to
`models/capitaliq_transaction_observed_ranker.joblib`, a live candidate list
to `data/layer_b_v2/transaction_observed/current_candidates_ranked.csv`, and
an explicit model card alongside it. Details and release limits are in
[`docs/transaction_observed_ranker.md`](docs/transaction_observed_ranker.md).

For a calibrated fixed-horizon classifier, use `layer_b_v2_pipeline.py` after
supplying history-complete Capital IQ company coverage, lifecycle, valuation,
and transaction exports. It refuses to create negatives until coverage spans
the full outcome horizon.

## Team 17

Mia Murphy, Finn Kliewer, Kayvon Jafarzadeh, Nathanael Gill, Om Patel
