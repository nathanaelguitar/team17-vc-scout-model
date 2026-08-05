# Layer B unicorn model audit

## Bottom line

The current score is not a defensible estimate of future unicorn probability. It is a highly accurate classifier of a constructed historical comparison: companies with a supplied `>= $1B` private-placement outcome versus companies selected from a supplied `< $1B` round extract and indexed at the positive company’s outcome date. The supplied data contain legitimate pre-outcome funding signal, but the observed performance is materially inflated by source-selection and missing-history artifacts.

The strongest evidence is that an intentionally constructed missingness-only model has forward ROC-AUC 0.816, a one-feature model using `days_since_last_pre_round` has ROC-AUC 0.904, and funding-history-only features have ROC-AUC 0.962. In contrast, company characteristics only have ROC-AUC 0.569. Matching metadata (`match_method`, which explicitly identifies positives as `positive_self`) produces ROC-AUC 1.000 and is correctly excluded from the production feature contract. See [the complete metrics](../analysis/layer_b_audit/results/leakage_ablation_baseline_metrics.csv).

## What was audited

The current implementation is `capitaliq_time_etl.py` → `data/gold/capitaliq_classifier_time_safe.csv` → `classifier_pipeline.py`.

| Question | Confirmed implementation / evidence |
| --- | --- |
| Unit of observation | One company-level row. The Gold table has 4,068 rows: 2,034 positive and 2,034 control rows, in 2,034 two-row matched groups. |
| Positive label | First supplied private-placement round with post-money valuation `>= $1B`; 3,000 qualifying transaction rows collapse to 2,034 companies. |
| Negative label | A company selected from supplied sub-$1B placement rows that is not in the positive export or known-unicorn Bronze tier. This proves neither permanent non-event nor full observation. |
| Positive prediction time | The positive’s first supplied `$1B+` outcome date. Feature rounds are required to be strictly earlier. |
| Control prediction time | The *matched positive’s* outcome date, not the control’s own event/landmark date. This is written as `index_date` in `capitaliq_control_matches.csv`. |
| Feature cutoff | `event_date < index_date`; `max_feature_round_date < index_date` is asserted in `capitaliq_time_etl.py` and holds for all Gold rows. |
| Matching | Deterministic one-to-one selection from eligible controls: industry+continent when possible (570 pairs), then industry (35), continent (56), otherwise date-only (1,373). It does not match age, round count, funding, or recency. |
| Split boundaries | The existing random holdout and CV group by `matched_positive_company`, so the two rows of a pair stay together. The forward split is by shared `index_year` (<2024 vs 2024+). It does not prevent the same investor, industry, or source-extraction relationship from crossing time boundaries. |
| Duplicate entities | No duplicated `company_key` exists in Gold. Canonical-name matching is conservative, but it cannot rule out related legal entities or name changes. |

The raw source audit is machine-readable in [source_and_construction_audit.json](../analysis/layer_b_audit/results/source_and_construction_audit.json). It found 37,858 supplied sub-$1B round rows across 30,247 companies; 3,000 `$1B+` rows across 2,034 companies; and 809 companies in both low-round and event exports. The latest supplied transaction date is 2026-07-29.

## Confirmed artifacts and limitations

There is no direct post-outcome feature leakage in the implemented feature builder: each retained round is before its row’s index date, and outcome valuation is not passed to the model. That is an important but insufficient guardrail.

The following construction artifacts are confirmed:

1. Controls are guaranteed to have an observed pre-index sub-$1B round because matching requires `first_control_date < positive.outcome_date`. Positives are not required to have observed pre-outcome history in that export. As a result, 1,247/2,034 positives (61.3%) have no observed pre-round versus 0/2,034 controls. `max_feature_round_date` is missing for exactly the same 1,247 positives and no controls. This is a label-revealing source-history indicator, not a business signal.
2. All controls use the positive’s event date. Their history therefore has a mechanically different observation window: positive median `days_since_last_pre_round` is -1 (no observed history), while control median is 81 days. The control and positive have the same calendar year by construction (SMD 0.00), but not comparable history construction.
3. The outcome extraction itself screens on valuation. A company absent from the `$1B+` export may be censored, unrecorded, acquired, inactive, have an unobserved valuation, or reach the threshold after the extract. The raw files provide no coverage start/end date, operating status, closure/exit date, or complete valuation history to resolve this.
4. Matching fields are direct leakage if accidentally used. The deliberate diagnostic achieves perfect separation because positives are labelled `positive_self`; the fields remain excluded from `classifier_pipeline.py`.

The matched balance table confirms material residual differences. Positives versus controls have SMD -0.46 for pre-round count, -0.36 for days since last pre-round, +0.42 for pre-index funding total, and +0.36 for maximum funding. See [numeric balance](../analysis/layer_b_audit/results/matched_pair_balance_numeric.csv) and [categorical balance](../analysis/layer_b_audit/results/matched_pair_balance_categorical.csv). The requested pre-match pool table is [pre_match_available_pool_balance_numeric.csv](../analysis/layer_b_audit/results/pre_match_available_pool_balance_numeric.csv): it is explicitly labelled non-time-aligned because each available control is represented at its own last supplied round, so it documents selection imbalance but is not a valid causal balance comparison.

## Forward diagnostic results

All results below use the historical target, train index years 2010–2023 (2,996 rows), and test 2024–2026 (1,072 rows). They are not an estimate of deployment performance.

| Forward diagnostic | ROC-AUC | PR-AUC | Brier | Interpretation |
| --- | ---: | ---: | ---: | --- |
| All current RF features | 0.966 | 0.971 | 0.071 | Strong only for the constructed target. |
| Remove `days_since_last_pre_round` | 0.966 | 0.971 | 0.072 | The artifact is a feature family, not just one column. |
| Funding-history only | 0.962 | 0.968 | 0.075 | Almost all measured discrimination is in history/extract patterns. |
| Strongest feature only: days since last round | 0.904 | 0.921 | 0.121 | Implausibly high for a generic startup-screening task. |
| Missingness/source-history indicators only | 0.816 | 0.843 | 0.140 | Confirms a substantial label-revealing artifact. |
| Company characteristics only | 0.569 | 0.551 | 0.236 | Weak, near-shallow discrimination. |
| Logistic regression | 0.947 | 0.956 | 0.097 | The task is largely separable without a complex model. |
| Shallow depth-2 tree | 0.912 | 0.904 | 0.102 | The task is substantially simple under this construction. |
| Training-prevalence-only baseline | 0.500 | 0.500 | 0.250 | Required no-signal reference; the historical matched sample has forced 50% prevalence. |
| Matching variables only (intentional leakage check) | 1.000 | 1.000 | 0.000 | Direct label metadata; never use as a feature. |
| Permuted training labels | 0.599 | 0.604 | 0.244 | Sanity check; residual deviation reflects finite sample/noise, not useful signal. |

The complete report includes precision, recall, specificity, F1, log loss, calibration intercept/slope, and confusion counts for every row. The companion figure is [forward_ablation_roc_auc.png](../analysis/layer_b_audit/figures/forward_ablation_roc_auc.png).

Permuting `days_since_last_pre_round` *within pairs* increased AUC to 0.974. This is not evidence that the feature is harmful; it demonstrates that pair-local permutation is not a valid importance test here because pair membership and source-history asymmetry are themselves part of the constructed target. This diagnostic is retained and explicitly flagged rather than interpreted as model improvement.

## Calibration, ranking, and cohort robustness

A strict three-period protocol was also run: train through 2022 (2,794 rows), fit calibration on 2023 (202 rows), and score the untouched 2024–2026 test (1,072 rows). The uncalibrated RF has ROC-AUC 0.964, Brier 0.073, calibration intercept -0.384 and slope 0.857. Platt-on-2023 leaves AUC unchanged but worsens Brier to 0.074 and has slope 0.710; isotonic overfits the small calibration set (log loss 0.456). See [calibration metrics](../analysis/layer_b_audit/results/chronological_calibration_metrics.csv) and [reliability figure](../analysis/layer_b_audit/figures/chronological_calibration_and_score_distribution.png).

The apparent top-bucket precision is 100% in the current held-out constructed sample (top 1%, 5%, 10%, and 20% all have 2.0× lift over its artificially 50% base rate). This is not a deployable screening claim: real startup prevalence is nowhere near the forced 1:1 matched-pair prevalence and the target is biased. Details are in [screening metrics](../analysis/layer_b_audit/results/screening_metrics_final_test.csv).

Within the same historical target, performance falls materially in several more comparable-looking strata: funding-stage proxy 1 has AUC 0.898, company-history 1–3 years 0.843, 3–7 years 0.842, and 7+ years 0.830. These remain affected by label construction, but they reject a claim of uniform robustness. The full bootstrap cohort report is [forward_cohort_robustness.csv](../analysis/layer_b_audit/results/forward_cohort_robustness.csv); cells under 20 rows or with one class are flagged rather than interpreted.

## Stronger current-data redesign checks

`scripts/layer_b_fixed_horizon.py` creates a fixed, two-year-after-first-supplied-round landmark. Features are strictly before the landmark. A positive is a first supplied `$1B+` event within 2/3/5 years. A negative is accepted only if it has no supplied event in that horizon **and** a later supplied sub-$1B round at/after horizon end; all other potential controls are treated as unknown/censored.

The only viable late-period result is the 2-year horizon: 1,481 labelled snapshots total (194 positive, 1,287 proxy-negative), with a 2024–2026 final test of only 30 rows: ROC-AUC 0.752, PR-AUC 0.901, Brier 0.221. The 3- and 5-year final chronological splits lack class variation, so no performance is reported. This is a large performance decrease but it is closer to the desired question; its small test set and follow-up proxy mean it is still not production validation. See [fixed-horizon results](../analysis/layer_b_audit/results/fixed_horizon_evaluation.csv).

Filtering the old matched controls to require more history does **not** solve censoring and should not be treated as validation. It still yields AUC 0.945–0.979 while collapsing sample sizes; this is consistent with a changed, easier selected cohort rather than proof of genuine signal. The sensitivity table is [strict_negative_cohort_sensitivity.csv](../analysis/layer_b_audit/results/strict_negative_cohort_sensitivity.csv).

## Survival analysis

An exploratory regularized Cox model was implemented in `scripts/layer_b_survival.py`, using a two-year-after-first-round landmark, first `$1B+` event as event, and last supplied sub-$1B round as a censoring proxy. It uses 3,238 rows (528 events, 2,710 proxy-censored); on a 2024–2026 landmark test it obtains C-index 0.678 and a two-year time-dependent-AUC proxy of 0.617. See [survival metrics](../analysis/layer_b_audit/results/exploratory_survival_metrics.json).

This is exploratory only. Last observed financing is informative and is not a Capital IQ coverage end. Survival analysis becomes preferable only after complete observation and competing-exit data are exported; it is not defensible as a production result from these files.

## Reproducibility

Run, without modifying source data:

```bash
python3 scripts/layer_b_leakage_diagnostics.py
python3 scripts/layer_b_calibration.py
python3 scripts/layer_b_fixed_horizon.py
python3 scripts/layer_b_survival.py
python3 scripts/layer_b_cohort_evaluation.py
```

All generated CSV/JSON/figures are under `analysis/layer_b_audit/`. Random seed is 17 where stochastic fitting or bootstrap sampling is used.
