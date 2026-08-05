# VC Scout — Presenter Script (Slide-by-Slide, Color-Coded)

<!--
HOW THIS FILE WORKS
This file is the source of truth for the presenter script. On every push to main
that touches presentation/script/, a GitHub Action rewrites the Notion page from
this file. Do NOT edit the Notion page directly; your edits will be overwritten.

FORMAT RULES (keep them, the sync depends on them):
- "## " lines are slide headers. If a speaker name appears after an em/long dash
  or the word "—", the header gets that speaker's color in Notion.
- A paragraph starting with "STAGE:" becomes a gray stage-direction callout. Never read gray out loud.
- A paragraph starting with "KEY:" or "NOTE:" also becomes a gray callout (used at the top).
- A paragraph starting with a speaker name + colon (KAYVON: MIA: FINN: NATHANAEL: OM:)
  becomes that speaker's colored callout. Everything until the next blank line belongs to it.
- "---" becomes a divider. **bold** works inside any block.
-->

KEY: **WHO READS WHAT — COLOR KEY**
KAYVON — blue · MIA — purple · FINN — green · NATHANAEL — orange · OM — yellow
Gray boxes = stage directions and deck interactions (builds, presses, hovers, clicks). Never read gray out loud.
Total runtime is about 20.5 minutes before Q&A. Start the timer with T on the title slide. It turns amber at 17:00 and red at 20:00.

NOTE: **HOW THIS WAS WRITTEN (so it doesn't sound AI)**
Short sentences mixed with long ones. Contractions everywhere. No filler transitions, no "delve", "leverage", "navigate", "cutting-edge", no em dashes, no stacked "X, Y, and Z" lists in spoken lines. Every claim carries a specific number instead of a generality.
Before rehearsal: read your block out loud once. If a line doesn't sound like something you'd actually say, swap the wording but keep the number exactly as printed. Numbers are non-negotiable; phrasing is yours.

---

## M-01 · PACKET (title) — Kayvon · about 1 min

STAGE: On load the folded sheet deploys from the gold packet over about 2 seconds. Press T to start the timer NOW. Press R to replay the unfold if you enter late. Let the sheet settle before speaking.

KAYVON: We audited the unicorn market. We created this, and we call it the VC Scout.
We're not going to tell you we can predict which startups will succeed. Nobody can do that from public data. But what we can do is give you our best guess on where these unicorns are heading, and which industries are about to pop. All from the data we were given.

---

## M-02 · TEAM — Kayvon · about 1.5 min

STAGE: Rows and the coach card fold in on their own. No internal builds. One press moves on.

KAYVON: Quick intros before we get into it. On our team today we've got me, Mia Murphy, Finn Kliewer, Nathanael Gill, and Om Patel. You'll hear from all of us tonight.
And on the gold card is our coach, Andrew Horrocks of HRX Capital Partners.
Here's what we're going to walk you through: the question we asked, the data we pulled together, the models we built on top of it, and what we actually found.
So let's start with the question.

---

## M-03 · QUESTION — Kayvon · about 1.5 min

STAGE: Boxes and sub-question rows fold in on their own. One press moves on.

KAYVON: Here's the setting. 2021 minted a record cohort of unicorns, then the market repriced it. Gut-feel benchmarks broke. Scouts are drowning in deal flow, and private valuations are still opaque. The practical pain is triage: too many companies, no fair yardstick.
So we asked a deliberately narrow question. Given only public fields, meaning funding, sector, geography, and timing: what is a fair expected valuation for a unicorn-scale company? And which segments beat that benchmark?
Notice what the question doesn't say. It doesn't say "who will succeed." It says fair expected valuation, conditional on unicorn scale. That's the version an investment committee could actually use. Fair benchmarks first. Then residual watchlists. Then diligence priorities.
The plain-English version is simpler: this is a ranked recommendation system for venture capital. It turns public signals into an expected valuation or a screening score, then ranks companies and segments against a fair benchmark. It helps a scout decide what deserves a closer look. It is not a crystal ball.
We committed to six sub-questions up front, H1 through H5 plus a classifier question, and every one of them gets a verdict stamp before we're done. One of those stamps says disproven. We'll show you that one too, because we lost it fair and square.
First, the data. An honest answer needs more than a winners-only file.

---

## M-04 · UNIVERSE (datasets) — Kayvon, hand off to Mia · about 1.5 min

STAGE: Tier cells fold in; the red coverage tag lands last and is meant to feel uncomfortable. Point at it when it lands. One press moves on.

KAYVON: The original dataset is the Kaggle unicorn file. 1,074 companies, and every single one already won. You cannot learn what normal looks like from a file with no normal companies in it. That's survivorship bias, and it's structural.
So we built a bigger universe. 75,230 companies across six tiers. 64,150 funded controls from the Crunchbase December 2015 open export. 8,342 accelerator companies from YC, Techstars, and 500 Global. 1,400 current unicorns. 908 soonicorn proxies with $100 million or more in funding. 223 delisted. 207 exited through IPO or M&A. Every tier has its source and its license printed on the label.
Now the red tag, because it's the most important thing on this slide. Only 1,829 of those rows carry a valuation at all. That's 2.4 percent. Private valuations simply are not public anywhere. Hold onto that number. It comes back when we talk about survivorship bias, and it doesn't come back kindly.
Mia, take them to 2021.

---

## M-05 · REGIME (variables & relationships I) — Mia · about 2 min

STAGE: Bars extend in a staggered wave, the 2021 bar in gold; era panel and p-value tags fold in. One press moves on.

MIA: Thanks, Kayvon. Before we model anything, look at what the market did on its own.
Each bar is unicorn births per year. The gold one is 2021: 441 companies. For scale, 351 dated rows sit before 2021, and 607 came after.
Now the right panel. Median valuation walks down across eras. $2.3 billion pre-2021. $1.67 billion in 2021. $1.5 billion after. Median funding does the same slide: $505 million, then $320, then $231.
Are those differences real? Kruskal-Wallis says yes. p equals 5.1e-12 on valuation. 3.5e-19 on funding. The sector mix shifts too, chi-square p of 1.0e-20.
But here's the twist we didn't expect. Years-to-unicorn didn't move. The median stayed around six years, p equals 0.267. Not significant. So 2021 changed how much capital and valuation a unicorn carries. It did not change how fast companies got there. It's a capital regime, not a speed regime.
One caution before anyone writes it down: the data flags the discontinuity. It does not prove COVID caused it. That would take external rate and funding data we don't have.
What it means downstream is simple. Every benchmark you're about to see carries an era feature, and 2021 gets reported separately, so a hot-year cohort can't distort a comparison.
Those are the variables. Finn has the machine we raced on top of them.

---

## M-06 · TOURNAMENT (model & tools) — Finn · about 2 min

STAGE: Strips race in sequentially, then the test diamonds drop. Pause and let the race finish before naming the winner. One press moves on.

FINN: Seven models, one fair race. Same folds for everyone, same held-out test set, 99 hyperparameter combinations searched, all of it on seed 17. The tools are on the slide: Python, pandas ETL in a bronze-silver-gold structure, scikit-learn pipelines, GridSearchCV, and a bootstrap with 2,000 resamples.
*(beat: let the strips race in and the diamonds drop)*
The baseline scores zero, which is exactly what a baseline should do. The linear models cluster in the mid-forties. And gradient boosting takes it: 0.46 cross-validated, 0.51 on the test set.
Three things about that race for the technical folks in the room. Every transform was fit inside the training folds, so nothing leaked. The test set got touched exactly once. And we banned funding efficiency as a feature, because it contains the target. Using it would've been cheating.
Also look at the champion's shape. 200 trees, learning rate 0.03, depth 2, subsample 0.8. It's a third the size of the random forest, with no gap between CV and test. Regularization beat horsepower.
In dollars: a median miss of 37 percent of valuation, versus 77 percent if you just guessed the average. Half the error, from public fields alone. The bootstrap interval runs 0.39 to 0.61.
So, 0.51. Nice number. Don't fall in love with it. It was earned on the winners-only file. Nathanael, tell them what the expanded data looked like when it showed up.

---

## M-07 · AUDIT (challenges & mitigation) — Nathanael · about 2 min

STAGE: TWO BUILDS on this slide. First press: 950 cells flip red with corruption strikes. Second press: the gold refold wave sweeps through with a live counter to 950/950. Rehearse the pause between presses. This is the deck's signature moment.

NATHANAEL: The expanded data arrived broken. Not subtly broken. Broken in a way you can prove.
Here's how we caught it. 1,058 unicorn rows carried both a funding number and a valuation. That made a sanity check possible, because a company's total funding should not exceed its own valuation.
*(FIRST PRESS: cells flip red. Pause. Let them look.)*
Every red cell just failed that check. 950 out of 1,058. Ninety percent of the checkable rows had funding recorded one thousand times too large. Unit corruption. My favorite example is VAST Data: $263 billion of recorded funding against an $80 billion valuation. The real number is $263 million.
*(SECOND PRESS: gold refold wave. Let the counter run to 950/950 before speaking.)*
The fix is deliberately boring. Divide the suspect values by a thousand. Keep every raw value in the master, so the correction is reversible. Re-run the check. After correction: zero rows where funding exceeds valuation. 950 out of 950, refolded.
One more piece of context. We pulled SEC Form D filings for Q2 2026. 238 mega-raises of $100 million or more. 156 of them are likely non-startup vehicles, and they hold 77 percent of the mega-raise dollars. We keep that as market context. It never touches training data.
The point here isn't that upstream sources are bad. The point is process. Audit before you believe.
Finn, show them what the audit did to our favorite number.

---

## M-08 · REFOLD (the honest number) — Finn · about 1.5 min

STAGE: The 0.51 bar rises first, then visibly refolds down to 0.303; the stress bar lands tiny; the curve draws. Let the refold finish before the first line. One press moves on.

FINN: *(beat: watch the bar fold down with the room)*
It cut it almost in half. The 0.51 you liked two slides ago becomes 0.303 once we rebuild on audited funding across the unicorn-history tiers. Cross-validated 0.397. Mean absolute error, 0.48 log units. Median error, 40 percent of valuation.
And we lead with the smaller number on purpose. The 0.51 was real, but it was earned on a winners-only file with corrupted units. The 0.303 survives diligence. We know which one our coach would put on a slide.
Two more things here. The stress test: pull funding out of the model entirely and R² collapses to 0.045. Public fields beyond funding carry very little. That's the humility check.
And the curve in the middle is the elasticity: 0.494 on a log-log fit. In plain English, doubling a company's capital buys about 41 percent more expected valuation. Not double. Diminishing returns, measured.
We're not apologizing for any of this. Honest signal from public fields looks exactly like this.
Mia, show them what the market was doing underneath the benchmark.

---

## M-09 · TRAJECTORIES (variables & relationships II) — Mia · about 1.5 min

STAGE: ONE BUILD. The field of gray strands draws first. Press the right arrow to light the ten star companies and labels. Then physically hover one gray strand with the mouse so the room sees the live tooltip.

MIA: Every gray strand on the right is one unicorn's valuation across four snapshots: 2022, 2024, 2025, and 2026. 838 companies carry all four points, and 1,313 strands have at least two.
*(PRESS the right arrow: the ten names light up)*
Three stories, and then I'll leave the chart alone. OpenAI: $3 billion to $840 billion across four snapshots. That's 280 times, while Anthropic reached $965 billion. Stripe is the honest middle story: $95 billion down to $70, back up to $159. Dip and recovery. And Klarna: $46 billion down to $6.7, recovering only to $14.5.
This chart is live, by the way.
*(hover any gray strand: tooltip shows its company and values)*
Any strand I hover shows you its company. These are recorded snapshots, not forecasts, so we're not going to editorialize about anyone's future.
But this is exactly why the project exists. Raw valuations swing by orders of magnitude in both directions. A raw price tag tells you almost nothing.
Om, so what's the actual signal?

---

## M-10 · RESIDUALS (insights) — Om · about 1.5 min

STAGE: Bars extend from the axis in both directions; low-confidence rows render part-folded and faded. Hovering any bar shows the full row. One press moves on.

OM: Subtract the benchmark. Actual minus expected log valuation, after controlling for funding, sector, geography, and era. That residual is the scouting signal. Positive means a segment beats a fair benchmark.
Industries first. Fintech sits at plus 0.045 across 213 companies. That one's robust. Enterprise software, plus 0.022 on 300. Cybersecurity leads at plus 0.082, but that's eight companies, so the deck literally renders the row part-folded. The caveat is built into the picture. You can't miss it.
Here's the one that lands in 2026: AI and Data is slightly negative. Minus 0.018 across 263 companies, despite all the hype.
Countries. South Korea leads the world at plus 0.348, on twelve companies. That's a watchlist entry, not a ranking. The US sits at plus 0.013 across 561. China, minus 0.103 across 166.
And the gold tag: OpenAI sits 90 times above its own benchmark. Residual plus 4.52 in log terms.
These are watchlists for diligence. They are not rankings to invest by.
And because a benchmark should be usable, we made it something you can drive.

---

## M-11 · EXPLORER (live demo) — Om · about 2 min

STAGE: FULLY LIVE HTML instrument. Rehearsed 30-second demo: (1) drag the funding slider, (2) tap a sector chip, (3) hit the KLARNA preset, (4) optionally hit OPENAI for the crowd-pleaser. R resets nothing; state persists, just drag the slider back.

OM: This is not a screenshot.
*(drag the funding slider and let the output move)*
The slider is total disclosed funding, $10 million to $50 billion on a log scale, and the expected valuation is recomputing as I drag. Notice it moves sub-linearly. That's the diminishing returns doing its job.
*(tap a sector chip)*
Every sector changes the estimate, and the output tells you when a profile clears the billion-dollar line.
*(hit the KLARNA preset)*
Now a real company. Klarna. Expected valuation comes out around $10.1 billion. Its actual peak snapshot was $46 billion. That's 4.6 times above benchmark, computed in front of you.
Here's the classifier version of the same idea. Changing Environments Inc. is a non-unicorn control in the forward test: hardware and industrials, North America, with $2.5 million in pre-round funding and an $8.77 million last recorded post-money value. The model gave it a 94.2 percent screening score, the highest-ranked non-unicorn control out of 536. That is a diligence lead, not a claim that the company will become a unicorn. The controls are defined by the absence of a recorded billion-dollar round.
*(optional: hit OPENAI, give the room a second)*
And if you want the crowd-pleaser, there's OpenAI.
One caution, and the subtitle says it too: this is a scouting instrument, not a valuation tool for investing.
Nathanael, layer two asks a harder question. Not how big. Who gets there.

---

## M-12 · CLASSIFIER (Layer B) — Nathanael · about 2 min

STAGE: Importance bars extend; both AUC numbers fold in large. One press moves on. Slow down on the warning card. Say the quiet part before any professor does.

NATHANAEL: Layer B runs on round-level data. Capital IQ private placements, 2010 through mid-2026. It's licensed, so it stays out of the public repo. 2,034 companies that eventually hit a billion dollars, each paired with one matched control. 4,068 rows.
Construction is the whole game here. Every feature is built strictly before each company's first observed billion-dollar round. Matching metadata and outcome fields are excluded. And cross-validation is pair-grouped, so a company and its control can never split across folds.
Results. The random forest hits 0.997 ROC-AUC on cross-validation. Hold that thought, because I know exactly what you're thinking.
We also ran a chronological forward test. Train through 2023 on 2,996 rows, then score 2024 through '26 cold, on 1,072. That comes out at 0.9865. Precision 0.874, recall 0.972.
Top feature: days since the last pre-round, at 43 percent of importance. Momentum is real signal. It's also the feature most exposed to matching artifacts, and we flag that on the slide itself.
Now the warning card, and this is the part I want you to remember. A plain logistic regression already reaches 0.974. A mixed-source diagnostic hits 0.993. When separation is that easy, you suspect the data before you celebrate the model.
So we report this as historical screening. Never as a probability of success. Controls are defined by the absence of a recorded billion-dollar round, and right-censoring is real.
Om, we promised verdicts. The scoreboard.

---

## M-13 · HYPOTHESES (learnings) — Om · about 1 min

STAGE: Stamps slam in staggered with a slight rotation. Fast slide. Let the red DISPROVEN stamp do the work. One press moves on.

OM: We committed to five hypotheses in advance. Here come the verdicts.
*(beat: stamps land)*
Supported: 2021 is its own regime. Supported: funding predicts valuation with diminishing returns. R² 0.30, stress test 0.05, elasticity about 0.49. Partial: sector and geography add real but secondary signal.
Disproven. Look at the red ink. We built a 75,230-row universe hoping it would solve survivorship bias, and it didn't. Sources mix across time, and valuation coverage is 2.4 percent. We're saying that in ink, on a slide, in front of the graders, because a finding you can't falsify is marketing.
Not proven: investor count alone carries roughly zero importance. Which, conveniently, tells us what to build next.
So what should a scout actually do with all this? The playbook.

---

## M-14 · PLAYBOOK (recommendations) — Om · about 1 min

STAGE: Rows fold in, run-column then refuse-column. Don't soften the refuse column. Its bluntness is the persuasion. One press moves on.

OM: Four things to run. Three things to refuse.
Run this. Rank segments by benchmark residuals, never by raw valuation. Treat 2021 as its own regime. Attach a confidence flag to every ranking, every time. South Korea at twelve companies stays a watchlist entry. And add investor-network features next, because a raw count did nothing.
Now refuse this, and the refusals matter just as much. Don't sell success probabilities. Don't train on Form D noise; 77 percent of those mega-raise dollars aren't startups. And don't reward raw capital raised. Elasticity 0.49 says the market doesn't either.
A fund could adopt this Monday morning.
Finn, zoom out once.

---

## M-15 · FRAMEWORK (deployment & next steps) — Finn · about 1 min

STAGE: The flow BENCHMARK → RESIDUALS → SCORING → DECISION cascades in. Read the on-the-label disclaimers slowly, on purpose. One press moves on.

FINN: Everything you've seen tonight is one connected system. Benchmark, residuals, scoring, decision.
And the roadmap is specific, not hand-wavy. First, richer deal-level data through PitchBook via Cornell's subscription. Second, investor network features: top-fund flags and co-investor clusters, replacing a count that carried nothing. Third, predicting ranges instead of single numbers. Fourth, tracking companies from day one instead of only studying winners. That last one is the only real attack on survivorship bias.
And read the label with me, once, slowly. Conditional on unicorn status. Associations, never causal claims. Small samples carry visible flags. Scouting signals, not investment advice.
Before we close: what this project taught us.

---

## M-16 · CARRY (insights & takeaways) — Finn or Om · about 1 min

STAGE: Takeaway cards fold in on the left, the prediction card lands on the right. One press moves on.

FINN: Three things this project taught us, and one call.
One. When a model looks too good, suspect the data, not a breakthrough. Our headline classifier scored 0.99, and so did a much simpler model. That's a warning, not a win.
Two. Money still moves valuations, but with diminishing returns. Doubling a company's funding buys about 40 percent more value. Efficiency beats raw check size.
Three. The direction is specific, but not a single “next unicorn” profile. By count, North America still leads the audited set with 584 rows, followed by Asia with 303 and Europe with 136. On the funding-adjusted residual, South Korea is the strongest watchlist at plus 0.348 across twelve companies, while the United States is close to benchmark at plus 0.013 across 561. By industry, Enterprise Software has 300 rows, AI and Data has 263, and Fintech has 213; Fintech and Enterprise Software beat benchmark, while AI and Data is slightly below it at minus 0.018.
And two answers are deliberately negative. We don't have reliable team-size coverage, so we won't invent a company-size trend. And age did not move: the median time to unicorn stayed around six years before 2021, in 2021, and after 2021, with p equals 0.267. The defensible call is capital-efficient fintech and enterprise software, with South Korea as a watchlist, not a prediction of who wins.

---

## M-17 · CLOSE — Kayvon · about 30 sec

STAGE: Roster and the five folded Q&A cells fold in. After inviting questions, do NOT fill the silence. Let the folded cells do the work.

KAYVON: Every number in this deck is one script away. The repo is on screen. Run the pipeline on seed 17 and every chart and every stat regenerates, deterministically.
So that's the thesis in one sentence: an audited benchmark, plus a residual scouting lens, plus a screened classifier, with the limitations printed on the label.
Thank you to our coach, Andrew Horrocks. We'll take your questions.

---

## Q&A · Using the folded receipt cells (15 min)

STAGE: The final slide has five folded cells: WHY 0.51 → 0.30, DOES MONEY = VALUE?, WHY IS 2021 SPECIAL?, IS THE MODEL TOO GOOD?, WHERE NEXT UNICORNS? When a hard question lands, CLICK the matching cell so a plain-English receipt panel slides in from the right, then answer from the artifact instead of from memory. Esc closes it.

NOTE: **Which cell for which question:**
"Why did R² drop from 0.51 to 0.30?" → WHY 0.51 → 0.30. The model didn't change; the data got honest. We prefer 0.303 because it's defensible.
"Isn't 0.997 AUC too good to be true?" → IS THE MODEL TOO GOOD? Yes, nearly. A simple model scores almost as high; suspect the data first. Forward test: 0.9865.
"Why is 2021 special?" → WHY IS 2021 SPECIAL? 441 unicorns, five times normal, at lower valuations and funding, with unchanged time-to-unicorn.
"Does more money mean more value?" → DOES MONEY = VALUE? Only partly. Doubling funding buys about 41 percent more valuation. Remove funding and the model barely works.
"Where do the next unicorns come from?" → WHERE NEXT UNICORNS? North America still dominates by count; South Korea is the strongest small-sample watchlist; Fintech and Enterprise Software beat the funding-adjusted benchmark; AI and Data does not. We cannot support a team-size trend, and median time-to-unicorn remains about six years.
