# Transaction-observed screening ranker

## What is available now

`scripts/layer_b_transaction_observed_ranker.py` builds a working ranking model from the Capital IQ transaction reports already in `data/raw`.

It scores a company at its **second observed financing** using only the first and second financing records and asks whether Capital IQ subsequently records a `$1B+` post-money valuation or private-placement event within three years.

This is a research-prioritization ranker. It is not a probability that a startup will become a unicorn and it is not a verified-negative classifier.

## Current run

The current artifact was trained through 2019, selected on 2020, and tested once on the untouched 2021–2022 period.

| Measure | Result |
| --- | ---: |
| Final rows / observed positives | 113 / 34 |
| ROC-AUC | 0.804 (bootstrap 95% interval: 0.710–0.879) |
| PR-AUC | 0.642 (bootstrap 95% interval: 0.475–0.790) |
| Top-decile observed-event precision | 75.0% |
| Top-decile lift over observed base rate | 2.49x |

These estimates apply only to the transaction-observed cohort, not to the global startup population. The final sample is modest, so the intervals—not just the point estimates—must accompany any discussion of performance.

## What drives the ranking

Validation ablations are saved in `validation_feature_ablations.csv`. Timing-only features perform at chance level (ROC-AUC 0.492), which rules out the earlier date-matching artifact. Funding signals drive most of the ranker: the current round amount alone reaches validation ROC-AUC 0.840, while all permitted financing-history features reach 0.852 and improve validation PR-AUC from 0.738 to 0.767. This is a useful and intuitive screening signal, but it also means the tool should be used to prioritize unusually strong financing events—not as a broad measure of startup quality.

## Outputs

- `data/layer_b_v2/transaction_observed/second_financing_snapshots.csv`: all snapshots and explicit label states.
- `data/layer_b_v2/transaction_observed/final_2021_2022_ranked_predictions.csv`: untouched temporal test predictions.
- `data/layer_b_v2/transaction_observed/current_candidates_ranked.csv`: latest three years of currently rankable, not-known-unicorn, not-tickered candidates.
- `data/layer_b_v2/transaction_observed/current_candidate_suppression_audit.csv`: the full candidate set, including current-state suppression reasons.
- `data/layer_b_v2/transaction_observed/model_card.json`: reproducible metrics, split sizes, and release gate.
- `models/capitaliq_transaction_observed_ranker.joblib`: fitted ranking artifact.

## Label policy

- `observed_positive`: a first `$1B+` event appears strictly after the snapshot and within three years.
- `observed_no_future_outcome`: no qualifying event is seen, but the same company has a later Capital IQ transaction at or after the horizon. This is follow-up evidence only, not proof of a true negative.
- `insufficient_followup`: no label; it is used for current candidate scoring only when the snapshot falls in the latest three observed years.
- `already_unicorn`: excluded because the qualifying event was observed at or before the snapshot.

All feature transactions are at or before the prediction date; the `$1B+` valuation and later follow-up evidence never enter the feature contract.

## Certified model upgrade

The coverage-aware fixed-horizon pipeline remains at `layer_b_v2_pipeline.py`. It will train only after history-complete `companies.csv`, `transactions.csv`, `valuations.csv`, and `lifecycle.csv` exports are provided under `data/layer_b_v2/raw`. That model can create verified negatives and calibrated probabilities only after its coverage, lifecycle, and temporal release gates pass.
