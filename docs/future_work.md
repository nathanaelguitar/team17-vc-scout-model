# Future Work

The current project answers two narrower questions well: how valuation varies
among observed unicorns, and which pre-index funding histories are associated
with later $1B valuations. Several improvements would make the results more
useful for investment screening.

## Data improvements

- Add more round-level observations for companies that never reached $1B.
- Add employee count, revenue or ARR bands, founder experience, and investor
  characteristics where licensing permits.
- Extend the current Capital IQ history with exits and later operating outcomes.
- Refresh the public control snapshots so controls are not concentrated in one
  historical vintage.

## Modeling improvements

- Calibrate probabilities on a larger, independently labeled holdout set.
- Test survival and time-to-event models instead of treating every company as
  having the same observation window.
- Compare the classifier with simpler scorecards and examine performance by
  industry, geography, and index year.
- Add confidence bands and an explicit right-censoring flag to screening output.

The present classifier should be interpreted as a historical screening model,
not a causal estimate or a guarantee of future valuation.
