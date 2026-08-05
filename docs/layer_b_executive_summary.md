# Layer B executive summary for the presentation

The current Layer B model should not be presented as a 98–99% accurate unicorn forecaster. Its historical matched-pair forward AUC is 0.966 in the audited reproduction, but 0.816 AUC is achievable using source-history/missingness indicators alone and 0.904 using a single timing feature. That indicates the score is materially inflated by how positives and controls were constructed.

There is legitimate pre-outcome information in funding patterns, but the current data cannot distinguish it cleanly from data-coverage artifacts. A stricter two-year landmark prototype drops to AUC 0.752 on only 30 late-period observations; 3- and 5-year tests are not yet evaluable. This degradation is a necessary warning, not a failure.

Recommendation: position Layer B as an in-development ranked screening methodology, not as a universal probability of startup success. Rebuild it around company-owned landmarks and a verified 3-year `$1B+` horizon, label only companies observed through the full horizon, and calibrate on a separate time period. Request complete Capital IQ company IDs, lifecycle/coverage dates, valuation history, financing history, and exit data before making any model-performance claim.
