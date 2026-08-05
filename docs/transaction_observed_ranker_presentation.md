# Transaction-observed unicorn likelihood ranker — presentation guidance

## Include this in the presentation

This model **must be included in the presentation** as the project’s current deployable screening tool. Present it as an evidence-based prioritization ranker for private-company opportunities, not as a model that estimates a company’s literal probability of becoming a unicorn.

## What it does

For a company at its second observed financing, the model ranks the likelihood that Capital IQ subsequently records a `$1B+` post-money valuation or qualifying private-placement event within three years. It uses only financing-history information available at that financing event: prior round count, funding totals and maximum round, prior valuation, investor breadth, time between rounds, and the current round size and investor count.

## Evidence to show

The untouched 2021–2022 temporal holdout achieved:

| Measure | Result |
| --- | ---: |
| ROC-AUC | 0.804 |
| PR-AUC | 0.642 |
| Top-decile observed-event precision | 75.0% |
| Top-decile lift vs. observed base rate | 2.49x |

The ranker scored 1,015 current private candidates after suppressing companies that are already known/former unicorns or currently tickered public entities. The ranked output is `data/layer_b_v2/transaction_observed/current_candidates_ranked.csv`.

## Required spoken and slide disclosure

> Scores are **unicorn-outcome likelihood rankings**, not calibrated probabilities that a company will become a unicorn. Capital IQ transaction history provides observed follow-up events but does not prove continuous data coverage for companies without an observed `$1B+` event.

Do not label a score as "probability," "odds," or "chance of becoming a unicorn." Use language such as "rank," "screening priority," or "observed-outcome likelihood." Include the temporal holdout period and the small final holdout sample (113 observations, 34 observed positives) next to performance metrics.

## Recommended slide sequence

1. **Decision question:** Which currently private companies should receive prioritized research?
2. **Input and target:** second financing snapshot; later observed `$1B+` event within three years.
3. **Validation:** temporal holdout results and top-decile lift.
4. **Output:** top-ranked candidate list and the operational workflow for analyst review.
5. **Limitation and upgrade path:** a calibrated unicorn probability requires historical Capital IQ coverage and lifecycle histories; the coverage-aware v2 pipeline is ready for that data.

