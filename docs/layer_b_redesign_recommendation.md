# Layer B recommended model design

## Recommendation

Do not deploy or present the current matched-pair random forest as a unicorn-probability model. Present it only as a historical-data audit result. Its 0.966 historical forward AUC is primarily a classifier of an outcome-screened versus sub-threshold-source construction, not a clean forecast.

### Primary design: fixed-horizon ranked screening model

Adopt a 3-year fixed-horizon model once the additional Capital IQ export in [the acquisition request](capital_iq_additional_data_request.md) is available. Three years is the recommended primary horizon because it is long enough for an investment screening decision and avoids treating young companies with insufficient follow-up as failures. Report 2- and 5-year horizons as sensitivity analyses, not interchangeable outcomes.

| Design element | Recommendation |
| --- | --- |
| Population | Global private companies with a verified company record and an eligible defined landmark; retain all statuses and exits. |
| Unit | One company × landmark snapshot. Start with first institutional round and Series A as separate cohorts; do not mix milestones without an explicit milestone feature/stratification. |
| Prediction timestamp | The announced/closed date available at the selected round landmark; choose one date convention before model fitting and retain its provenance. |
| Outcome | First verified `$1B+` valuation in `(t, t+3 years]`. Use complete dated valuation history, not an outcome-screened file. |
| Negative | Verified coverage through `t+3 years`, no `$1B+` event, and no unresolved status. Exclude or separately model competing exits. |
| Censoring | Unknown if coverage ends before horizon. Never coerce unknown/censored cases to negative. |
| Feature cutoff | Every feature’s source/observation date must be `<= t`; retain an audit column with the maximum source date per feature family. |
| Feature set | Round amount/stage, capital-to-date, investor/syndicate aggregates, company age, industry/geography, and dated fundamental/traction features. Aggregate investor histories strictly before `t`. Keep coverage/missingness fields for QA, not as predictive shortcuts. |
| Validation | Entity-/parent-grouped chronological splits: training, hyperparameter validation, calibration, then untouched final period. No random split as headline result. Purge related company/investor relationships where an investor network feature could cross a split. |
| Metrics | PR-AUC and top-k precision/recall/lift at operational screening budgets as primary; ROC-AUC secondary; Brier/log loss/reliability/calibration slope for probabilities. Bootstrap CIs by company group. |
| Calibration | Fit Platt and isotonic only on the dedicated calibration period. Select using calibration-period Brier/log loss; report unchanged final test. Do not call a score a probability unless reliability is satisfactory by cohort. |
| Intended use | Rank a defined investment-screening population for human research, with a documented coverage cohort and horizon. |

Claims we can make after successful validation: “Among the covered companies eligible at this landmark, the model ranks historical 3-year `$1B+` outcomes with measured out-of-time precision/lift.”

Claims we cannot make: “This is the probability that any startup will become a unicorn,” “a company scored low will fail,” or “the score applies outside the covered population/landmark/time period.”

### Fallback design: competing-risk survival ranking

If stakeholders need a continuously updating time-to-event ranking rather than a single 3-year decision, fit cause-specific or competing-risk survival models using complete coverage, valuation, IPO/acquisition, closure, and inactive-status histories. A Cox model is a transparent baseline; a survival forest or boosted survival model can be evaluated only after that baseline. Report concordance and calibrated 2/3/5-year event risk by cohort.

Survival is more statistically natural when entry dates, observation windows, and competing outcomes are complete. It is **not** more defensible on the currently supplied extracts: the last financing round is an informative observation event, not an independent censoring date. The exploratory current-file Cox result (C-index 0.678, two-year proxy AUC 0.617) must not be used for product claims.

## Before versus after

| Topic | Current design | Recommended design |
| --- | --- | --- |
| Target | Event-export positives vs selected sub-$1B controls | Explicit first `$1B+` event within a fixed horizon |
| Negative meaning | No recorded event in supplied extract | Verified full-horizon non-event; otherwise censored |
| Prediction time | Positive outcome date; control matched positive’s outcome date | Company’s own decision landmark |
| Observation window | Asymmetric source history | Same dated pre-landmark feature policy for every company |
| Population prevalence | Forced 50% by 1:1 matching | Actual eligible-cohort prevalence; report top-k lift |
| Evaluation | Grouped pairs plus chronological index date | Entity/parent-grouped time split with train/validation/calibration/final periods |
| Probability claim | Unsupported; current calibration is construction-specific | Conditional, calibrated horizon probability only if final reliability holds |

## Current evidence and decision gate

The strongest present-day forward-looking proxy is the two-year-after-first-supplied-round snapshot: AUC 0.752 on 30 late-period snapshots, with observed-follow-up proxy negatives. Its sample is too small and its coverage rule too weak for deployment; 3- and 5-year final splits do not have enough class variation. Treat this as evidence that the current 0.966 should not be carried into the presentation as model performance.

Proceed to model selection only after the requested data pass these gates:

1. At least one full final 3-year horizon has adequate covered positives and negatives in a chronologically later period.
2. Feature timestamps, valuation event dates, coverage, and lifecycle dates pass automated leakage and label tests.
3. Results remain useful after removing coverage/missingness proxy fields and after comparing against simple recent-funding and regularized-logistic baselines.
4. Calibration and top-k lift are stable with confidence intervals across newest, youngest, lower-funded, and less-complete eligible cohorts.
