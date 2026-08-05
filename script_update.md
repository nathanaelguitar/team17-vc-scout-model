# Script and deck update log

Last updated: 2026-08-05. This file tracks presenter-facing content decisions so
the deck (`presentation/vc-scout-deck.html`), the script
(`presentation/script/presenter-script.md`), and the Notion page stay aligned.
Notion syncs automatically from the Markdown script on every push to main.

## Current state

### Slide 5 / M-05 (regime)
Concise version. Fixed facts: 441 unicorns in 2021; 351 dated rows before, 607
after; median valuation $2.3B → $1.67B → $1.5B; median funding $505M → $320M →
$231M; p-values: valuation 5.1e-12, funding 3.5e-19, sector mix 1.0e-20;
time-to-unicorn ~6 years, p=0.267, not significant. Framing: a market break in
the capital/valuation regime, not proof that COVID caused it.

### Slide 11 / M-11 (explorer)
Example is Neo Financial Technologies: last recorded post-money $779.09M, prior
disclosed funding $144.13M, current round $262.98M, screening score 79.5%,
label state insufficient follow-up. Labeled a ranking signal, not a
probability. No revenue claims (the repository has no revenue data).
Alternate example: Coro Cyber Security ($575M post-money, $100M current round,
92.6%, also insufficient follow-up). Source:
`data/layer_b_v2/transaction_observed/second_financing_snapshots.csv` and
`current_candidates_ranked.csv`.

### Slide 12 / M-12 (screening ranker)
Replaced the old 0.997/0.9865 classifier claims. Current numbers, from
`data/layer_b_v2/transaction_observed/model_card.json` and
`docs/transaction_observed_ranker.md`:
- Temporal holdout 2021–2022: ROC-AUC 0.804 (bootstrap 95% interval
  0.710–0.879), PR-AUC 0.642, top-decile precision 75%, lift 2.49x.
- Final holdout size disclosed: 113 companies, 34 observed positives.
- Uses only the first two observed financings; ranks the chance of a recorded
  $1B+ event within three years; never presented as a unicorn probability.
- Tear-down evidence shown on-slide as a native chart drawn from
  `analysis/layer_b_audit/results/leakage_ablation_baseline_metrics.csv`
  (matching bookkeeping alone: AUC 1.000; all real features 0.966; one timing
  feature 0.904; missingness flags 0.816; company traits 0.569). The matplotlib
  original is `analysis/layer_b_audit/figures/forward_ablation_roc_auc.png`.

### Benchmark distinction (slides 6 and 8)
0.51 R² is the original 1,060-row winners-only benchmark. 0.303 R² is the
audited 1,057-row rebuild after correcting 950 funding-unit errors. Audited CV
R² is 0.397.

### Presenter order and speakers
M-01 title → M-02 team → M-03 question → M-04 universe → M-05 regime → M-06
tournament → M-07 audit → M-08 refold → M-09 trajectories → M-10 residuals →
M-11 explorer → M-12 ranker → M-13 hypotheses → M-14 playbook → M-15 framework
→ M-16 carry → M-17 close. Contiguous speaker runs: Kayvon 1–4, Mia 5–8, Om
9–11, Nathanael 12–13, Finn 14–16, Kayvon 17.

## Editing rules
- Edit `presentation/script/presenter-script.md`, never the Notion page; the
  sync overwrites Notion on every push.
- Numbers must trace to a committed file. Phrasing is free; numbers are not.
- No em dashes in spoken lines, no AI-tell stock words, sentences short enough
  to say in one breath.
