# VC Scout: Model Definition and Initial Results (Team 17)

Cornell Capstone, Project #32: Startup Growth and Investment.

This repo contains Team 17's "Model Definition and Initial Results" deliverable: a fully reproducible modeling pipeline on the Unicorn Companies dataset, the slide deck built from its outputs, and every chart and statistic used in the deck.

## Contents

| Path | What it is |
|---|---|
| `deliverable/Team17_Model_Definition_Initial_Results.pptx` | The submission deck (10 slides) |
| `deliverable/Team17_Model_Definition_Initial_Results.pdf` | PDF version for quick preview |
| `model_pipeline.py` | End-to-end pipeline: cleaning, feature engineering, train/test split, cross validation, hyperparameter tuning, model comparison, diagnostics, sensitivity checks, chart rendering |
| `model_stats.json` | Every number in the deck, produced by the pipeline (source of truth) |
| `charts/` | The five deck charts as transparent PNGs |
| `data/Unicorn_Companies.csv` | The dataset (1,074 unicorn companies, from the Kaggle "Startup Growth and Investment" dataset) |

## The task

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
pip install pandas scikit-learn matplotlib numpy
python model_pipeline.py
```

Deterministic (seed 17). Regenerates all charts in `charts/` and `model_stats.json`. Runtime is a couple of minutes on a laptop.

## Team 17

Mia Murphy, Finn Kliewer, Kayvon Jafarzadeh, Nathanael Gill, Om Patel
