# Layer B forward-looking model implementation plan

## Objective

Replace the current historical matched-pair classifier with a defensible, forward-looking ranked screening model. The model should estimate a clearly defined outcome within a fixed horizon for a clearly defined covered company population; it must not be presented as a universal probability that any startup will become a unicorn.

## Why the current design must change

The current training table compares 2,034 companies with a supplied `$1B+` private-placement outcome against one selected sub-$1B control per positive. It is useful as a historical diagnostic, but it has structural artifacts:

- A control is indexed at the matched positive company’s outcome date, not at the control’s own decision point.
- Controls are guaranteed to have observed pre-index round history; 61.3% of positives have no observed pre-round in the supplied low-valuation extract.
- A missingness/source-history-only model achieves ROC-AUC 0.816 and a single timing feature achieves ROC-AUC 0.904 on the current historical target.
- “No recorded `$1B+` round” is not a verified negative because coverage dates, status, exits, and complete valuation history are absent.
- The 1:1 matching scheme forces a 50% outcome prevalence, so current precision, calibration, and top-k lift cannot be used for a real screening population.

Do not optimize the current target for a higher AUC. A lower out-of-time score under a valid target is the desired outcome.

## Primary model design

### Population

All globally covered private companies that reach a defined funding landmark and have an eligible observation window. Include active, acquired, IPO, inactive, bankrupt, and delisted entities so that censoring and competing outcomes are observable.

### Unit of observation

One row per `company_id × landmark_date`. Begin with separate models or stratified cohorts for:

1. First institutional financing
2. Seed financing
3. Series A
4. Series B
5. Two years after first recorded financing

Do not mix milestones into a single dataset without retaining milestone as an explicit, deployment-available variable and validating the combined population separately.

### Prediction timestamp and feature cutoff

The prediction timestamp is the company’s own landmark date. Every feature must be available on or before that date. Each feature build should save:

- `prediction_date`
- `feature_as_of_date`
- maximum transaction, valuation, investor, operating-metric, and source-verification date used
- a boolean audit result proving each maximum date is `<= prediction_date`

Do not use current status, current valuation, later funding rounds, later investor exits, or data fields updated after the prediction date as features.

### Primary outcome: three-year fixed horizon

For a snapshot at date `t`:

- Positive: first verified company or post-money valuation `>= $1B` occurs in `(t, t + 3 years]`.
- Negative: the company is verifiably covered through `t + 3 years`, has no qualifying event, and has no unresolved lifecycle status.
- Censored/unknown: coverage ends before `t + 3 years`, status is unknown, or the company cannot be verified over the horizon. Exclude from binary labels rather than assigning a negative.
- Competing outcome: acquisition, IPO, closure, bankruptcy, or inactivity before horizon. Retain in a separate endpoint table and choose a documented treatment before fitting. Do not silently turn it into a negative.

Run two- and five-year versions as prespecified sensitivity analyses. Use the same label and observation rules.

### Intended output

Output a calibrated score only if final out-of-time calibration supports it. Otherwise output a ranking score and describe it as a prioritization signal for research review.

Valid claim after final validation: “Within the covered, eligible landmark population, the model ranks historical companies by observed three-year `$1B+` outcome risk.”

Invalid claims: “probability that any startup becomes a unicorn,” “probability of startup success,” or use outside the covered population, date range, and landmark.

## Required Capital IQ data

Request a history-complete global export with no `$1B` outcome filter. Preserve exact vendor field names and provide a data dictionary.

### Must-have files and fields

| File grain | Required fields | Uses |
| --- | --- | --- |
| Company master | Immutable Capital IQ company/entity ID; legal name; aliases; parent/ultimate-parent IDs; founding date; geography; industry/subindustry; business description; ownership status | Entity resolution, group splitting, population definition, age/industry/geography features |
| Company coverage and lifecycle history | Coverage start/end; record created/updated dates; last verified activity; dated operating status; closure, bankruptcy, acquisition, IPO, and inactive dates | Negative-label validity, censoring, competing risks, coverage diagnostics |
| Financing transactions | Company ID; `CIQ Transaction ID`; announced/closed dates; round type/stage; transaction status; amount; currency; pre-money/post-money valuation; source/verification date | Landmarks, pre-index funding features, dated outcomes |
| Valuation history | Company ID; valuation date/as-of date; value; currency; valuation basis/type; source/verification date | First `$1B+` outcome and down-round/valuation-history checks |
| Transaction-investor bridge | Transaction ID; investor ID; lead/co-lead flag; investor role/type; announced/closed dates | Investor count, lead quality, syndicate features |
| Investor master/history | Investor ID; dated portfolio investments; dated realized IPO/acquisition/unicorn outcomes where licensed | Pre-index investor-quality aggregates |
| Company fundamentals | Dated revenue, revenue growth, EBITDA/operating metrics, employee counts/growth, and available customer/traffic metrics | Legitimate pre-index traction features |
| Exit/competing-outcome history | Company ID; event type; announcement/close/effective dates; transaction IDs | Competing-risk labels and survival analysis |

### Export constraints

- Include full available history from at least 1995 through the extraction date.
- Include all relevant companies, not only companies with a `$1B+` valuation or a particular round value.
- Supply an `extract_as_of_date`, population filters, row counts, minimum/maximum date, data dictionary, and source/verification metadata.
- Join every file by immutable company ID; join investor participation through `CIQ Transaction ID` and investor ID.
- Retain historical rather than overwritten current values.

The detailed acquisition request is in [capital_iq_additional_data_request.md](capital_iq_additional_data_request.md).

## Data-pipeline changes

Create new isolated modules; do not overwrite `data/raw`, the existing Capital IQ ETL, or existing model artifacts.

Suggested structure:

```text
data/layer_b_v2/raw/                 # immutable received exports
data/layer_b_v2/intermediate/        # normalized entities, rounds, valuations, lifecycle
data/layer_b_v2/snapshots/           # company × landmark tables
data/layer_b_v2/results/             # generated scores, metrics, cohort results
src/layer_b_v2/                      # ingestion, labels, features, splits, models
tests/layer_b_v2/                    # date, entity, label, split, calibration tests
configs/layer_b_v2/                  # versioned population/landmark/feature settings
```

### Core pipeline stages

1. Normalize company, transaction, valuation, investor, and lifecycle IDs/dates.
2. Build an entity-resolution table with parent/alias links and ambiguity flags.
3. Build complete dated company timelines.
4. Generate landmark snapshots at each approved milestone.
5. Construct 2-, 3-, and 5-year labels with explicit positive, negative, censored, and competing-outcome states.
6. Compute features strictly as of each snapshot date.
7. Produce data-quality and label-eligibility logs at every stage.
8. Freeze an immutable final-test period before model tuning.

### Feature policy

Eligible feature families:

- Company age, geography, industry/subindustry, ownership status
- Prior financing count, stage, amount, cumulative capital, round cadence, pre-money/post-money valuations
- Investor count, investor type, lead-investor indicators, pre-date investor outcome aggregates, syndicate composition
- Dated revenue, employee, and other operating/traction measures
- Calendar period and market-regime variables available at prediction time

Excluded or QA-only fields:

- Outcome valuation, outcome date, target-construction fields, matching IDs/methods, future status, and future transaction dates
- Coverage start/end, master-match status, missingness/source-export flags, unless separately justified as deployment-available QA controls
- Raw current values without a dated as-of/source timestamp

## Validation design

### Temporal separation

Use four periods, with exact cut years selected only after examining coverage:

1. Training period: fits candidate models.
2. Validation period: selects feature set and hyperparameters.
3. Calibration period: fits Platt or isotonic calibration only.
4. Final untouched period: used once for reported results.

No random split is a headline result. Group all rows from the same company, aliases, and linked parent entities in one split. If investor network features are used, assess whether investor relationships create additional cross-period leakage and document the chosen purge/grouping rule.

### Baselines and diagnostics

For every landmark and horizon, report:

- Prevalence-only baseline
- Recent-funding rule baseline
- Single-strongest-feature model
- Logistic regression and regularized logistic regression
- Shallow decision tree
- Random forest or gradient-boosted tree only after simpler baselines
- All features, feature-family ablations, missingness-only features, and matching/design-variable-only diagnostic
- Label permutation negative control

Metrics: ROC-AUC, PR-AUC, precision, recall, specificity, F1, Brier score, log loss, calibration intercept, calibration slope, and confidence intervals where sample size permits.

### Decision metrics

For the final test population, report at top 1%, 5%, 10%, and 20% of scores:

- Companies screened
- Positives found
- Precision
- Recall captured
- Lift over actual eligible-population base rate
- Number needed to screen

Report these by year, founding cohort, industry, geography, landmark/stage, company age, prior-round count, capital-to-date, data completeness, and economic period. Flag small cohorts instead of interpreting them.

## Calibration policy

Fit calibrators only on the dedicated calibration period. Compare uncalibrated, Platt, and isotonic predictions on the untouched final period with:

- Reliability diagrams
- Brier score and log loss
- Calibration intercept and slope
- Probability distributions by class and cohort

Do not call outputs probabilities if calibration is poor, unstable, or materially different across important cohorts.

## Survival-analysis fallback

Implement survival analysis only after coverage and competing-outcome dates are present. Use a Cox proportional-hazards model as a transparent baseline, then compare a survival forest or boosted survival method if justified. Report concordance, fixed-horizon time-dependent AUC, and horizon calibration.

The survival censoring time must be an actual coverage/status endpoint, not the date of a company’s last recorded financing. The current exploratory survival result must not be used for product or presentation claims.

## Automated tests and release gates

Add tests that fail on:

1. Any feature source date after its prediction date.
2. A positive event on/before the prediction date.
3. A negative without verified coverage through its horizon.
4. Entity, parent, alias, or linked-company overlap across data splits.
5. Reuse of a company across train, validation, calibration, and final test.
6. Any target, matching, outcome, or post-outcome field in the feature contract.
7. Invalid first-event selection when multiple valuations or rounds exist.
8. Calibration fitted using final-test data.
9. Missing stage/coverage/valuation-date audit logs.

Do not release a model claim until all gates pass and final-test results are generated from a frozen configuration and immutable input manifest.

## Deliverables

1. Normalized data dictionary and ingestion manifest.
2. Snapshot and label tables for each landmark/horizon, including censoring and competing-outcome reasons.
3. Versioned feature contract and source-date audit outputs.
4. Temporal split configuration and entity-separation audit.
5. Baseline, ablation, calibration, cohort, and screening results in CSV/JSON.
6. Publication-quality balance, reliability, discrimination, and decision-curve figures.
7. A model card stating population, horizon, labels, exclusions, calibration, metrics, intended use, and prohibited claims.
8. An updated concise presentation summary that reports only final validated results.

## Sequencing

1. Acquire and validate the history-complete Capital IQ exports.
2. Build normalized entity and lifecycle timelines.
3. Build fixed-horizon labels with coverage and competing-outcome handling.
4. Establish temporal splits and freeze the final period.
5. Implement date-safe features and automated leakage tests.
6. Run baselines, ablations, and diagnostics before tuning complex models.
7. Select a model on validation data, calibrate on the calibration period, and score the final period once.
8. Decide whether the resulting model is suitable as a ranked screening tool. If validation remains weak or unstable, report that result rather than reverting to the current matched-pair target.
