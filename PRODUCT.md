# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static self-contained HTML/CSS/JS (single file, no CDN, no framework) committed to the repo, plus a published Artifact copy for sharing. Confirmed by user ("Both" delivery). Vanilla JS + inline SVG/Canvas for charts; everything must run offline from a file:// open.

## Users

Primary: Cornell classmates, instructors, and industry coaches watching Team 17's live final capstone presentation — 35-minute slot: 20+ minutes of slides + ~15 minutes Q&A, scheduled Aug 5–7 2026. Graded on Coverage (10: required rubric items), Communication (25), Quality (10: clear titled slides/charts), Time (5). Industry coach: Andrew Horrocks (Managing Partner, HRX Capital Partners; ex-UBS/Credit Suisse/Moelis MD; Cornell MBA '92) — must be introduced. Every team member needs a meaningful presenting role. The five team members (Mia Murphy, Finn Kliewer, Kayvon Jafarzadeh, Nathanael Gill, Om Patel) drive the deck live — keyboard navigation, hover/interact while speaking. Secondary: graders revisiting the deck async afterward. Success = the audience *understands* the analysis through the slides (user's words: "we want people to understand through our slides") and remembers this deck over every other team's.

## Product Purpose

An interactive, animated presentation deck for VC Scout — Team 17's Cornell capstone (Project #32, Startup Growth and Investment). It replaces two static PPTX submissions with one completely new deck built from the finished repo's combined data. It must tell the full arc: unicorn dataset → model tournament → data audit → honest revised benchmark → residual scouting insights → Capital IQ round-level classifier → implementation framework.

## Positioning

The one capstone deck where the model is *demonstrated live*, not screenshotted: every number traces to `model_stats.json` / `vc_scout_source_of_truth_final.json`, and the charts move because they are real data rendered live, not PNG exports. The intellectual signature is honesty-as-strength: the team walked its own headline down from R² 0.51 to an audited 0.30 and treats a 0.997 AUC as a warning sign — no other team will present its audit as the hero.

## Operating Context

- Presented live from a browser (offline-safe); arrow-key/click slide navigation; print-to-PDF fallback for submission.
- Repo: team17-vc-scout-model (local clone in scratchpad). All deck numbers must come from committed artifacts: `model_stats.json`, `analysis/audit_trail/assets/vc_scout_source_of_truth_final.json` + CSVs, `models/capitaliq_classifier_metrics.json`, `data/expanded/build_summary.json`, `data/expanded/unicorn_valuation_panel.csv`.
- Existing dashboards (`dashboards/*.html`, ApexCharts + CountUp, indigo/violet/cyan light-dark theme) are prior art / evidence, not binding style authority.

## Capabilities and Constraints

- Slide budget ~12–16 slides for 10–15 minutes.
- Confirmed hero interactions (all four): (1) Live VC Scout explorer — sliders for funding/sector/geography driving expected valuation + outperformance live; (2) Valuation trajectory race 2022→2026 from the 1,672-company panel (OpenAI 3→840, Anthropic →965, Stripe 95→70→70→159, Klarna 46→6.7→14.5); (3) Audit reveal — 950 of 1,058 unicorn rows flagged/corrected animated; (4) Model tournament — 7 models racing, then the honest 0.51→0.30 drop.
- Capital IQ classifier is co-headliner with the valuation benchmark (two-layer framework story).
- Canonical numbers: 1,060 modeled unicorns; GB champion CV 0.46 / test 0.51 (initial); audited benchmark test R² 0.303, MAE_ln 0.480, elasticity 0.494, no-funding stress R² 0.045; 75,230-row expanded master (6 tiers); 1,829 rows with valuation; 2021 spike 441 unicorns; era medians $2.3B→$1.67B→$1.5B; residual leaders (Fintech +0.045 n=213, South Korea +0.348 n=12 small-n caveat, Transport & Logistics −0.234); OpenAI residual +4.52 (+9,043%); classifier ROC-AUC 0.997 CV / 0.986 forward, 4,068 paired rows.
- Never claim startup-success prediction: survivorship bias and non-causal framing are on the label per team charter. The 0.993–0.997 AUCs are presented with the source-artifact warning.
- Must respect prefers-reduced-motion; animations replayable per slide (presenter may revisit).

## Brand Commitments

Name: "VC Scout". Team identity: Team 17, Cornell (SC Johnson College of Business capstone). No other binding visual identity — the old decks' navy/neon look is explicitly replaceable (user wants "completely new").

## Evidence on Hand

All real, in-repo: model metrics JSONs, audit-trail CSVs (residuals by company/industry/country/continent, era regimes, tier summaries, hypothesis table H1–H5), 1,672-company valuation panel, Form D Q2-2026 raises (5,728 rows), forward predictions (1,072 rows), five chart PNGs, two briefing notes, two prior decks. No testimonials/pricing/customers exist and none may be invented.

## Product Principles

1. Understanding over spectacle: every animation must explain a state change, relationship, or magnitude — the audience should *get it* from the motion itself.
2. Honesty is the brand: caveats (survivorship bias, small-n, source artifacts) are staged as confident moments, never fine print.
3. Live data, not screenshots: charts render from embedded real data; numbers trace to the source-of-truth files.
4. Presenter-first: every slide works on a projector at distance, advances on keys, and no interaction is required to follow the talk (interactions are bonuses, not dependencies).
5. Memorable is the metric: one signature moment per slide; the deck should be the one people describe afterward.
