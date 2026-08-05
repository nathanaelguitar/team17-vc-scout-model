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

STAGE: Bars extend in a wave, 2021 in gold; era panel and p-value tags fold in. One press moves on.

MIA: Thanks, Kayvon. Before any modeling, look at what the market did on its own.
2021 produced 441 unicorns. For scale, 351 dated rows sit before 2021 and 607 after.
The median unicorn got cheaper every era. 2.3 billion, then 1.67, then 1.5. Funding fell harder: 505 million, 320, 231.
Those shifts are statistically real. Valuation, funding, and sector mix all move with p-values near zero.
But time-to-unicorn stayed near six years. Not significant.
Bottom line: 2021 changed the capital and valuation regime, not the speed. It's a market break, not proof that COVID caused it.
That's why every model tonight treats 2021 as its own era. Now, the machine we raced.
---

## M-06 · TOURNAMENT (model & tools) — Mia · about 2 min

STAGE: Strips race in, then the test diamonds drop. Let the race finish before naming the winner. One press moves on.

MIA: Seven models, one fair race. Same folds, same held-out test set, seed 17.
*(beat: strips race, diamonds drop)*
The baseline scores zero, like it should. The linear models bunch in the middle. Gradient boosting wins: 0.46 cross-validated, 0.51 on test.
And the race was clean. Nothing leaked across folds, the test set got touched exactly once, and we banned the one feature that contains the answer.
In dollars, that's a median miss of 37 percent versus 77 if you just guessed the average. Half the error, from public fields alone.
But that 0.51 was earned on a winners-only file. Wait till you see what the expanded data looked like.
---

## M-07 · AUDIT (challenges & mitigation) — Mia · about 2 min

STAGE: TWO BUILDS. First press: 950 cells flip red. Second press: the gold refold wave with a live counter. Rehearse the pause between presses.

MIA: It arrived broken. Provably broken.
1,058 unicorn rows had both a funding number and a valuation. Funding should never exceed valuation, so that gave us a test.
*(FIRST PRESS: cells flip red. Pause.)*
950 of 1,058 just failed it. Ninety percent, with funding recorded a thousand times too large. VAST Data showed 263 billion in funding against an 80 billion valuation. The real number is 263 million.
*(SECOND PRESS: gold wave. Let the counter finish.)*
The fix is boring on purpose. Divide by a thousand, keep the raw values, re-run the check. Zero failures left.
One more thing. In last quarter's SEC filings, 77 percent of the mega-raise dollars weren't even startups. We keep that as context, never as training data.
Audit before you believe. Now watch what it did to our favorite number.
---

## M-08 · REFOLD (the honest number) — Mia · about 1.5 min

STAGE: The 0.51 bar rises, then refolds down to 0.303; the stress bar lands tiny; the curve draws. Let the refold finish first. One press moves on.

MIA: *(beat: watch the bar fold down)*
Almost in half. The 0.51 becomes 0.303 on audited data. And that's the number we lead with, because it's the one that survives questioning.
Two quick things. Pull funding out of the model and R² collapses to 0.045. Funding is most of the signal.
And the curve: elasticity 0.494. Doubling a company's money buys about 41 percent more expected value. Not double.
No apology here. Honest signal from public data looks exactly like this.
Om, show them what the market was doing underneath.
---

## M-09 · TRAJECTORIES (variables & relationships II) — Om · about 1.5 min

STAGE: ONE BUILD. Gray strands draw first. Press the right arrow to light the ten stars, then hover one gray strand so the room sees the live tooltip.

OM: Every gray strand is one unicorn's valuation across four snapshots, 2022 to 2026.
*(PRESS: names light up)*
Three stories. OpenAI, 3 billion to 840. Stripe, 95 down to 70 and back to 159. Klarna, 46 down to 6.7, back to only 14.5.
And it's live.
*(hover a strand)*
Any strand shows its company. Recorded prices, not forecasts.
Here's the point. Raw valuations swing wildly in both directions, so a price tag alone tells you almost nothing. So what's the actual signal?
---

## M-10 · RESIDUALS (insights) — Om · about 1.5 min

STAGE: Bars extend both directions; thin samples render part-folded. Hovering a bar shows the full row. One press moves on.

OM: Subtract the benchmark. Actual minus expected, after controlling for funding, sector, geography, and era. The leftover is the signal.
Fintech beats it, plus 0.045 across 213 companies. Enterprise software too. Cybersecurity leads, but on eight companies, so the deck literally folds that row down.
And the 2026 surprise: AI and Data sits slightly below benchmark. All that hype, already priced in.
Countries. South Korea leads on twelve companies. That's a watchlist, not a ranking. The US sits right at benchmark across 561.
OpenAI? 90 times above its own benchmark.
These are watchlists for diligence, not rankings to invest by. And you can drive this thing.
---

## M-11 · EXPLORER (live demo) — Om · about 2 min

STAGE: FULLY LIVE. Demo: (1) drag the slider, (2) tap a sector chip, (3) hit KLARNA, (4) optionally OPENAI. State persists; just drag back. Alternate example if asked: Coro Cyber Security, ranking score 92.6%, $575M post-money, $100M current round, also insufficient follow-up.

OM: This is not a screenshot.
*(drag the slider)*
That's total funding, and the expected valuation recomputes as I drag. Notice it rises slower than the money does. Diminishing returns, live.
*(tap a sector chip)*
Sectors shift the estimate, and the output says when a profile clears the billion-dollar line.
*(hit KLARNA)*
Real company. Klarna's expected value comes out around 10 billion. Its actual peak was 46. That's 4.6 times above benchmark, computed in front of you.
*(optional: OPENAI)*
And there's the crowd-pleaser.
The gold panel is the ranker's pick of a near-unicorn. Neo Financial, last valued at 779 million, raised 144 million before this 263 million round. The ranker scores it 79.5 percent. That's a ranking signal, not a probability. Follow-up is still open.
Nathanael, layer two. Not how big. Who gets there.
---

## M-12 · CLASSIFIER (Layer B) — Nathanael · about 2 min

STAGE: The 0.804 and its interval land big; the smoking-gun chart second. Slow down on "a perfect 1.0." One press moves on.

NATHANAEL: Layer two uses only a company's first two financings and asks one question. Does a recorded billion-dollar event follow within three years?
Our first version scored 0.997. We didn't believe it, and here's the proof we were right. Feed the old setup nothing but its own matching bookkeeping, and it scores a perfect 1.0. The model was reading how we built the data, not startup quality. So we tore it down.
The rebuild: trained through 2019, tested cold on 2021 and '22. ROC-AUC 0.804, interval 0.71 to 0.88, because the final sample is small. 113 companies, 34 hits.
For a scout, the useful part: in the top decile, three of four flagged companies actually hit a billion-dollar event. Two and a half times better than chance.
What drives it is funding, not timing. Round size alone gets most of the way; timing features score at a coin flip.
These are rankings, not probabilities. It orders 1,015 live candidates by where to look first. It doesn't pick winners.
And we promised you verdicts. The scoreboard.
---

## M-13 · HYPOTHESES (learnings) — Nathanael · about 1 min

STAGE: Stamps slam in staggered. Fast slide. Let the red DISPROVEN stamp do the work. One press moves on.

NATHANAEL: Five hypotheses, committed in advance. The verdicts.
*(beat: stamps land)*
2021 is its own regime: supported. Funding has diminishing returns: supported. Sector and geography add signal: partial.
Now the red one. We built a 75,000-row universe hoping it would fix survivorship bias, and it didn't. We're saying that in ink, in front of the graders, because a claim you can't falsify is marketing.
Investor count alone: not proven. It carries nothing, which tells us exactly what to build next.
Finn, the playbook.
---

## M-14 · PLAYBOOK (recommendations) — Finn · about 1 min

STAGE: Rows fold in, run column then refuse column. Don't soften the refuse column. One press moves on.

FINN: Four to run, three to refuse.
Run: rank by benchmark residuals, never raw valuation. Treat 2021 as its own era. Put a confidence flag on every ranking. And build investor-network features next.
Refuse: don't sell success probabilities. Don't train on Form D noise, since 77 percent of those dollars aren't startups. And don't reward raw capital raised. The market doesn't.
A fund could run this Monday morning. Let's zoom out once.
---

## M-15 · FRAMEWORK (deployment & next steps) — Finn · about 1 min

STAGE: The flow BENCHMARK → RESIDUALS → SCORING → DECISION cascades in. Read the label slowly, on purpose. One press moves on.

FINN: Everything tonight is one system. Benchmark, residuals, scoring, decision.
The roadmap has four steps. Richer deal-level data through Cornell's PitchBook access. Investor network features. Ranges instead of single numbers. And tracking companies from day one, the only real fix for survivorship bias.
Now the label, slowly. Conditional on unicorn status. Associations, not causes. Small samples flagged. Scouting signals, not investment advice.
Before we close, what this project taught us.
---

## M-16 · CARRY (insights & takeaways) — Finn · about 1 min

STAGE: Takeaway cards fold in left, the prediction card lands right. One press moves on.

FINN: Three lessons and one call.
One. When a model looks perfect, suspect the data. Ours scored 0.99 and so did a much simpler one, so we threw it out and rebuilt it at an honest 0.80.
Two. Money still moves valuations, with diminishing returns. Double the funding, get about 40 percent more value.
Three. The direction is specific, but it isn't one profile. South Korea is the strongest watchlist. Fintech and enterprise software beat the benchmark. AI and Data doesn't.
The call, on the gold card: capital-efficient fintech and enterprise software, with South Korea on watch. Not a prediction of who wins.
And two honest No's. No team-size claim, we don't have the data. No speed claim either. Six years to unicorn, every era.
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
"Why did R² drop from 0.51 to 0.30?" → WHY 0.51 → 0.30. The model didn't change; the data got honest. We keep 0.303 because it survives scrutiny.
"Isn't 0.99 AUC too good to be true?" → IS THE MODEL TOO GOOD? Yes. A simpler model nearly matched it, so we rebuilt: the honest ranker scores 0.804, tested cold on 2021 and '22, interval 0.71 to 0.88. Rankings, not probabilities.
"Why is 2021 special?" → WHY IS 2021 SPECIAL? 441 unicorns, five times normal, cheaper and less funded, same six-year speed.
"Does more money mean more value?" → DOES MONEY = VALUE? Partly. Doubling funding buys about 41 percent more valuation. Remove funding and the model barely works.
"Where do the next unicorns come from?" → WHERE NEXT UNICORNS? Fintech and enterprise software beat the benchmark; AI and Data doesn't; South Korea is the strongest small-sample watchlist. No team-size or speed claims.
