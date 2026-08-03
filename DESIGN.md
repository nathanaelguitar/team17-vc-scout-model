---
name: VC Scout — Miura-Fold Deployment
description: Sheet-white paper, ink, and foil-gold — a capstone framework that unfolds like a deployable Miura-ori sheet.
colors:
  sheet-white: "#F7F7F7"
  sheet-warm: "#F1EFE9"
  ink: "#0A0A0A"
  ink-faded: "#4B4B47"
  chart-ink: "#161511"
  foil-gold: "#D4AF37"
  text-gold: "#8A6D1C"
  deep-gold: "#B7952C"
  pale-gold: "#F5EFD9"
  on-gold-ink: "#3D3212"
  mountain-gray: "#B9B6AE"
  valley-blue: "#CFE0F2"
  gridline: "#E4E2DB"
  correction-red: "#B3372B"
typography:
  display:
    fontFamily: "Chakra Petch, sans-serif"
    fontSize: "clamp(64px, 9.2vw, 150px)"
    fontWeight: 700
    lineHeight: 0.92
  headline:
    fontFamily: "Chakra Petch, sans-serif"
    fontSize: "clamp(26px, 3.4vw, 44px)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "0.005em"
  strap:
    fontFamily: "Chakra Petch, sans-serif"
    fontSize: "clamp(18px, 1.9vw, 27px)"
    fontWeight: 500
  body:
    fontFamily: "B612 Mono, monospace"
    fontSize: "clamp(12px, 1.05vw, 14.5px)"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "B612 Mono, monospace"
    fontSize: "10.5px"
    fontWeight: 400
    letterSpacing: "0.1em"
rounded:
  none: "0px"
spacing:
  cell-gap: "6px"
  stack-gap: "12px"
  block-gap: "24px"
  column-gap: "44px"
  canvas-pad: "56px"
components:
  tag-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet-white}"
    padding: "4px 12px 3px"
    rounded: "{rounded.none}"
  tag-gold:
    backgroundColor: "{colors.foil-gold}"
    textColor: "{colors.ink}"
    padding: "4px 12px 3px"
    rounded: "{rounded.none}"
  tag-red:
    backgroundColor: "{colors.correction-red}"
    textColor: "{colors.sheet-white}"
    padding: "4px 12px 3px"
    rounded: "{rounded.none}"
  tag-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink-faded}"
    padding: "4px 12px 3px"
    rounded: "{rounded.none}"
  chip:
    backgroundColor: "{colors.sheet-white}"
    textColor: "{colors.ink-faded}"
    padding: "5px 10px 4px"
    rounded: "{rounded.none}"
  chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet-white}"
    padding: "5px 10px 4px"
    rounded: "{rounded.none}"
  rail-cell:
    backgroundColor: "{colors.sheet-white}"
    textColor: "{colors.ink-faded}"
    padding: "6px 10px 5px"
    rounded: "{rounded.none}"
  rail-cell-active:
    backgroundColor: "{colors.foil-gold}"
    textColor: "{colors.ink}"
    padding: "6px 10px 5px"
    rounded: "{rounded.none}"
  ledge:
    backgroundColor: "{colors.sheet-white}"
    textColor: "{colors.ink}"
    padding: "12px 14px"
    rounded: "{rounded.none}"
  ledge-gold:
    backgroundColor: "{colors.pale-gold}"
    textColor: "{colors.ink}"
    padding: "12px 14px"
    rounded: "{rounded.none}"
  packet:
    backgroundColor: "{colors.foil-gold}"
    textColor: "{colors.ink}"
    padding: "14px 16px 12px"
    rounded: "{rounded.none}"
  qa-cell:
    backgroundColor: "{colors.sheet-warm}"
    textColor: "{colors.ink-faded}"
    padding: "10px 14px"
    rounded: "{rounded.none}"
  stamp:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "3px 10px"
    rounded: "{rounded.none}"
---

# Design System: VC Scout — Miura-Fold Deployment

## Overview

**Creative North Star: "The Miura-Fold Deployment"**

The system treats every surface as one sheet of engineered paper: a deployable Miura-ori sheet that unfolds from a hand-sized gold packet into a full framework. Content arrives by unfolding — elements hinge in from a fold (`rotateX(-76deg)` → flat), slides leave by folding away, and one authored 3D deployment moment (the title rig) establishes the metaphor that everything else quotes quietly. The world is bright, papery, and precise: sheet-white ground under near-black ink, with foil gold reserved for the packet, the champion, and the active position. It explicitly refuses the category default — the dark stat-tile analytics keynote — and it is recognizable with all content removed: the paper grain, the faint crease lattice, and the sheared parallelogram silhouette carry the identity alone.

Two typefaces split the voice. Chakra Petch's angular, fold-cut letterforms carry titles, big numbers, and verdicts; B612 Mono — an aerospace cockpit face — carries everything else, so annotations read like spec labels printed on the sheet's selvage. Density is editorial, not dashboard: one headline per screen, generous column gaps, hairline crease borders instead of boxes, and confidence caveats staged as visible geometry (thin samples literally render part-folded).

This file documents the system as built in `presentation/vc-scout-deck.html` (currently the repo's only Impeccable-designed surface). The grammar — tokens, shear, fold-in motion, chart conventions — is reusable for future surfaces such as reworking `dashboards/`.

**Key Characteristics:**
- Sheet-white paper ground with SVG-noise grain and a faint mountain/valley crease lattice
- Foil gold as surface material (packet, champion, active cell) — never as body text
- Every control is a sheared parallelogram; every card has cut corners; radius is always 0
- Chakra Petch display + B612 Mono spec labels; charts speak entirely in mono
- Fold-in motion grammar with one authored 3D deployment moment; full reduced-motion/static/print contract
- Honesty rendered visually: low-n data part-folded, corrections in red→gold, verdict stamps

## Colors

A paper-and-ink neutral field where gold is material, blue and gray are crease shadows, and red is reserved for corruption and refusal.

### Primary
- **Foil Gold** (`#D4AF37`, token `foil-gold`): the material of importance — the TEAM 17 packet, the active rail cell, the champion bar in every chart, the 2021 spike, the slider thumb, refolded audit cells, text selection. Applied as a surface, usually with the foil-texture tile (`background-blend-mode: multiply`) on packets. Never used as a text color on light ground.
- **Text Gold** (`#8A6D1C`, token `text-gold`): the only gold permitted as text (`.gold-t`), used for audited/positive callouts, low-confidence value labels, the 17-minute timer warning, and the `:focus-visible` outline. Exists solely because `#D4AF37` fails contrast as text on sheet-white.
- **Deep Gold** (`#B7952C`, token `deep-gold`): gold's edge — borders and strokes on gold surfaces (active rail cell border, champion bar stroke, slider-thumb border, visited-cell border).
- **Pale Gold** (`#F5EFD9`, token `pale-gold`): a whisper of gold for emphasized panels — the coach ledge, the champion table row, "why we say it carefully" — always paired with a deep-gold border.
- **On-Gold Ink** (`#3D3212`, token `on-gold-ink`): dark olive ink for small text sitting on gold surfaces (packet subline, gold chips, active fold-map cells).

### Secondary
- **Valley Blue** (`#CFE0F2`, token `valley-blue`): the valley crease — the second lattice direction, funding bars beside ink valuation bars, cell borders in the title rig. Cool, recessive, structural; never decorative.
- **Correction Red** (`#B3372B`, token `correction-red`): corruption and refusal — flagged audit cells (alpha-ramped fills with a diagonal slash), DISPROVEN stamps, "REFUSE THIS" headings, falling-company trajectories, the no-funding stress bar, the 20-minute timer alarm. `.red-t` is its text form.

### Neutral
- **Sheet White** (`#F7F7F7`, token `sheet-white`): the page ground and default component fill. Carries a fixed feTurbulence paper-grain overlay at 0.5 opacity.
- **Warm Sheet** (`#F1EFE9`, token `sheet-warm`): the folded layer — spine background, Q&A cells, key caps, table headers, resting audit cells. Reads as paper one fold below the surface.
- **Ink** (`#0A0A0A`, token `ink`): primary text, filled tags, hard borders (help card, Q&A panel top rule, output panel).
- **Chart Ink** (`#161511`, token `chart-ink`): the slightly warm near-black used for every non-champion chart mark (bars, strands, importance rows). Distinct from text ink so marks sit into the paper rather than on it.
- **Faded Ink** (`#4B4B47`, token `ink-faded`): secondary text — subheads, spec labels, all chart annotations and axis labels.
- **Mountain Gray** (`#B9B6AE`, token `mountain-gray`, CSS `--crease`): the mountain crease — every hairline border, axis stroke, divider, and the denser lattice direction.
- **Gridline** (`#E4E2DB`, token `gridline`): chart gridlines only; one step fainter than a crease.

### Named Rules
**The Foil Rule.** Gold is a surface, never body text. Text sitting *on* gold is ink or on-gold ink (`#3D3212`); gold-colored text on light ground is always text-gold (`#8A6D1C`), never `#D4AF37`.

**The One Champion Rule.** In any chart, exactly one element wears foil gold — the champion, the anomaly, the active cell. Everything else is chart ink. Red appears only when something is wrong on purpose.

## Typography

**Display Font:** Chakra Petch (self-hosted woff2, weights 500 + 700; sans-serif fallback)
**Body Font:** B612 Mono (self-hosted woff2, weights 400 + 700; monospace fallback) — also the `<body>` default at 16px
**Label/Mono Font:** B612 Mono (same face; labels are a size/tracking role, not a third family)

**Character:** Fold-cut technical display over an aerospace cockpit mono. Chakra Petch's chamfered corners echo the crease geometry; B612 Mono (designed for Airbus flight displays) makes every annotation read as a printed spec. There is no humanist serif or UI sans anywhere.

### Hierarchy
- **Display** (700, `clamp(64px, 9.2vw, 150px)`, lh 0.92): the title slide wordmark only ("VC SCOUT").
- **Headline** (700, `clamp(26px, 3.4vw, 44px)`, lh 1.02, `text-wrap: balance`): one h2 per slide; hero slides scale up to `clamp(30px, 3.8vw, 52px)`.
- **Strap** (500, `clamp(18px, 1.9vw, 27px)`): the single subtitle line under the wordmark.
- **Value** (Chakra Petch 700, 17–72px): big numbers — ledge values (24px), classifier AUC (52px), explorer output (72px), bar-top labels. Numbers of consequence are always display-weight.
- **Body** (`.sub`; mono 400, `clamp(12px, 1.05vw, 14.5px)`, lh 1.55, max-width 66ch, faded ink): one explanatory paragraph per slide.
- **Label** (`.spec`; mono, 10.5px, letter-spacing 0.1em, faded ink, UPPERCASE with `<b>` runs in ink 700): spec blocks, sources, footnotes, chart captions (9–10px inside SVG/canvas).

### Named Rules
**The No-Kicker Rule.** No eyebrows or kicker labels above headings, ever. Headings open the slide; identification lives in the rail, HUD, and spec blocks below.

**The Two-Voice Rule.** Chakra Petch states; B612 Mono annotates. If a number is a verdict it is display-weight; if it is evidence it is mono. All text inside charts is mono (`svg text { font-family: var(--mono) }`).

## Layout

Two slide modes share one fixed-viewport engine (`overflow: hidden`, slides absolutely stacked), and the transition between them must read as one sheet refolding, never as two decks:

- **Board mode** (data slides): a two-column grid — a fixed 248px folded spine on the left, a flat reading canvas on the right (`padding: 56px 64px 56px 56px`). The canvas carries a `.canvas-frame`: a 1px mountain-gray border inset 26px/30px with 14px cut corners, framing the sheet like a scored panel. The spine holds the gold packet header ("VC SCOUT / TEAM 17 · CORNELL CAPSTONE Nº32"), the fold-map (M-01…M-17 parallelogram cells), and a corner-cut spec foot listing the source-of-truth files.
- **Stage mode** (title, heroes, act breaks): full bleed. The spine slides off-canvas (`translateX(-100%)`, 0.45s settle ease) and a bottom rail of 30×15px sheared cells appears, centered 18px from the bottom. Stage slides carry a faint resting crease lattice (`::after`, opacity 0.55): repeating hairlines at 76° in mountain-gray (~148px period) crossed with −38° in valley-blue (~122px period) — the sheet never disappears. A HUD sits bottom-right (slide ID, position, optional timer).

Within the canvas, slides compose as asymmetric two-column grids (`1.25fr 1fr`, `1.1fr 1fr`, `1.5fr 1fr`…) with 40–48px column gaps; vertical rhythm runs on 22–26px blocks. Hero slides pin a `.hero-head` (headline + sub + specs, max-width 34–46%) top-left and a 300px `.hero-side` ledge stack top-right, with the chart canvas absolutely placed between them.

**Responsive:** below 760px wide the spine is hidden, grids stack to single column, canvases become in-flow, and the bottom rail persists as sole navigation. Below 840px tall, hero heads compact so charts clear them.

**Print:** every slide renders sequentially (`page-break-after: always`, 7.4in tall, crease rule between slides), spine/rail/HUD/grain hidden, all folds flattened; a `beforeprint` hook force-enters every slide in reduced mode so charts exist on paper.

## Elevation & Depth

Flat by conviction: the sheet is one material, so surfaces do not float. Depth is conveyed three ways instead of shadow stacks — (1) paper grain (a fixed feTurbulence SVG noise tile over the whole body at 0.5 opacity), (2) crease lines (mountain-gray and valley-blue hairlines, and the stage lattice), and (3) actual 3D fold transforms (perspective rotations during entrances, exits, and the title deployment). Ledges overlaying charts use a translucent sheet fill (`rgba(247,247,247,0.93)`) rather than elevation.

### Shadow Vocabulary
The only shadows in the system belong to foil — gold is the one material thick enough to cast:
- **Foil packet** (`box-shadow: 0 2px 8px rgba(10,10,10,.18)`): the spine packet.
- **Foil packet, 3D** (`box-shadow: 0 6px 18px rgba(10,10,10,.25)`): the title-rig packet at the hinge of the deployment.
- **Foil thumb** (`box-shadow: 0 1px 4px rgba(10,10,10,.3)`): the explorer slider thumb.

### Named Rules
**The Foil-Casts-Shadow Rule.** If it isn't gold, it doesn't cast a shadow. Paper is flat; only the foil packet and foil controls lift off the sheet.

## Shapes

The form language is the crease grid. There is no border-radius anywhere (`rounded.none: 0`); curvature does not exist on a folded sheet. Two moves define every silhouette:

1. **The shear.** Interactive and annotative elements are parallelograms: `transform: skewX(-14deg)` (token `--shear`) on the container, with an inner `<span>` counter-skewed (`skewX(14deg)`) so text stays upright. Applied to tags, chips, rail cells, fold-map cells, Q&A cells, deployment-map cells, and the slider thumb. In SVG and canvas the same shear appears as a horizontal offset (4–16px) on bar ends — every bar in every chart is a parallelogram, and the audit grid's 1,058 cells are individually sheared.
2. **The cut corner.** Containers (packet, ledges, canvas frame, explorer output, spine foot) clip opposing corners with 45° cuts via `clip-path: polygon(...)` — 8–16px cuts, always top-left + bottom-right — reading as snipped fold corners rather than rounding.

Supporting geometry: diamonds (rotated squares) mark test-set points in charts; verdict stamps rotate −3° like hand-inked impressions; the title rig's cells carry ±4° `skewY` facet shading. Decorative crease angles are 76° (mountain) and −38° (valley) in the stage lattice.

**The Counter-Skew Rule.** Any text inside a sheared container must be wrapped and counter-skewed. Letterforms are never italicized by the shear.

## Components

The component set is text-and-geometry only — the system uses **no icons, no emoji, no glyph fonts**; controls are labeled parallelograms.

### Tags (annotation parallelograms)
- **Shape:** sheared parallelogram (skewX −14deg), 11px mono, letter-spacing 0.06em, padding 4px 12px 3px.
- **Variants:** `tag-ink` (ink fill, sheet text — default statements); `tag-gold` (gold fill, ink text — the headline finding); `tag-red` (red fill, sheet text — warnings like "ONLY 1,829 ROWS CARRY A VALUATION"); `tag-line` (transparent, 1px crease border, faded ink — statistical footnotes). Often chained with `▸` separators in crease color to form pipelines (BENCHMARK ▸ RESIDUALS ▸ SCORING ▸ DECISION).

### Chips (filter/preset toggles)
- **Style:** sheared parallelogram, 1px crease border on sheet-white, faded-ink text at 10.5px, padding 5px 10px 4px.
- **States:** selected = solid ink with sheet text; hover = border darkens to ink. Used for explorer sector/continent/era selectors and real-company presets. Selection is binary ink — gold is not spent on chips.

### Rail Cells (fold-map navigation)
- **Spine form:** full-width sheared cells listing `M-01…M-17` (10.5px mono; the ID in 700 ink), 1px crease border, 5px gaps.
- **Stage form:** anonymous 30×15px sheared cells in the bottom rail.
- **States:** active = gold fill with deep-gold border (ID in on-gold ink); visited = warm-sheet/gold-tinted gradient with deep-gold border; hover = ink border. The rail is the deck's fold map — position is always shown as which cell is currently gold.

### Ledges (annotation cards)
- **Corner style:** cut corners (10px), 1px crease border, translucent sheet fill so charts read through.
- **Structure:** `.k` spec label (9.5px, 0.12em tracking) → `.v` display value (Chakra Petch 700, 24px) → `.n` mono note (10px). 
- **Gold variant:** pale-gold fill + deep-gold border for the coach card and cautionary panels.

### Packet (signature identity block)
- Foil-gold surface with a raster foil-texture tile multiplied over it, cut corners, foil shadow, Chakra Petch 700 title with a mono subline in on-gold ink. Appears exactly three times: spine header, title-rig hinge, and close slide — opening, carrying, and sealing the deck.

### Stamps (hypothesis verdicts)
- Chakra Petch 700 at 13px, 0.1em tracking, 2.5px solid border, rotated −3°, uppercase. Semantic borders/text: SUPPORTED = text-gold; PARTIAL / NOT PROVEN = faded ink; DISPROVEN = correction red. Stamps sit in a 150px column beside their hypothesis row (crease-ruled `hyp-row` grid).

### Inputs / Fields
- **Slider:** 3px mountain-gray track; thumb is a 26×17px sheared gold parallelogram with deep-gold border and foil shadow (`cursor: ew-resize`). Value echoes live into a text-gold mono label.
- **Focus:** every focusable element gets `outline: 2px solid var(--gold-ink); outline-offset: 2px`.
- **Output panel:** `#xp-out` — 1px ink border, 16px cut corners, 72px display value, with the live OLS formula printed beneath a crease rule in 9.5px mono.

### Q&A Cells + Panel
- **Cells:** warm-sheet sheared parallelogram buttons (10.5px mono) that sit "folded" on the close slide; hover inks the border and text.
- **Panel:** a bottom sheet (max-height 62vh) with a 2px ink top rule, sliding up on the 0.45s settle ease; contains display h3 + mono tables (`table.mini`: crease borders, warm header row, right-aligned numerals, champion row in pale gold).

### Charts (signature convention)
All charts are hand-drawn SVG (or canvas above ~800 elements) from embedded real data — never a chart library, never an image.
- **Marks:** bars are sheared parallelograms in chart ink; the single champion/anomaly is foil gold with a deep-gold stroke; diamonds mark test-set values against CV strips; line charts draw via dash-offset.
- **Scaffolding:** gridlines in `gridline`, axes in mountain-gray, all labels 9–10.5px mono in faded ink, captions UPPERCASE (e.g. "STRIP = CV R² · DIAMOND = TEST R² · N = 1,060"). Big numbers on bars in Chakra Petch 700.
- **The Part-Folded Rule (LOW N).** Segments with n < 30 render part-folded: fills drop to ~45% alpha (gold) / ~35% (ink), labels to 62% opacity, values carry a "LOW N"/"LOW CONFIDENCE" suffix in text-gold, and tooltips repeat the flag. Low confidence is geometry, not a footnote.
- **Canvas fields:** the audit grid (1,058 sheared cells: resting warm-sheet → corruption red alpha-ramp with diagonal slash → refolded gold) and the trajectory field (strand color `rgba(75,75,71,.055)` at 0.8px; hover 2px near-black with an ink tooltip; highlighted companies 2.4px — deep gold rising, correction red falling, chart ink neutral — with leader-line labels collision-resolved at the right edge).

### Motion Grammar (signature behavior)
- **Fold-in entrance:** every content block is tagged `[data-fold]`; on slide enter, `choreograph()` starts them at `perspective(1200px) rotateX(-76deg)`, opacity 0, then releases them to flat over 0.55s on the settle ease `cubic-bezier(.16,1,.3,1)` with a 70ms per-element stagger, top of slide first.
- **Slide exit:** `.leaving` folds the outgoing slide away — `rotateX(9deg) translateY(-2.5%)` + fade, 0.28s on `cubic-bezier(.55,0,.8,.4)`.
- **The One-Deployment Rule.** The full 3D deployment (nine chained strips unfolding rotateY ±78°→±6° over 2.1s from the gold packet, camera settling from rotateX 24° to 10°) is authored once, on the title. Every other slide only quotes it via the fold-in entrance.
- **Chart draws:** rAF tweens with cubic ease-out and per-item stagger; `draw0(fn, 200–350ms)` delays chart drawing until the fold-in has landed. Charts with narrative builds advance on → as steps (audit: flag → refold; trajectories: light the names) before the deck moves on; R replays the current slide's build.
- **Reduced/static contract:** `prefers-reduced-motion` or `?static=1` sets `body.reduced` — all transitions/animations null, folds pre-flattened, `tween()` jumps to its end state, `draw0` runs immediately, and boot pre-enters every slide so charts exist for instant navigation and print. Every animation has a correct final frame with no motion.

## Do's and Don'ts

### Do:
- **Do** keep gold scarce and material: one gold element per chart, gold surfaces only via `foil-gold` (+ texture on packets), gold text only via `text-gold` (#8A6D1C).
- **Do** shear every control −14° and counter-skew its label; draw every bar as a parallelogram with a 4–16px sheared end.
- **Do** cut corners (45°, 8–16px, opposing corners) on containers instead of rounding; `border-radius` stays 0 everywhere.
- **Do** set all chart annotations in B612 Mono at 9–10.5px uppercase faded ink, and all verdict numbers in Chakra Petch 700.
- **Do** render n < 30 segments part-folded (reduced alpha + "LOW N" suffix in text-gold) wherever thin data appears.
- **Do** give every animation a fold semantics (something unfolds, refolds, or deploys) and a correct instant end-state under `body.reduced`, `?static=1`, and print.
- **Do** keep the sheet present on full-bleed surfaces: paper grain plus the 76°/−38° crease lattice at ~0.55 opacity.

### Don't:
- **Don't** use `#D4AF37` as text on light ground, or spend gold on selection states that ink can carry (chips select in ink).
- **Don't** add kickers or eyebrow labels above headings — the No-Kicker Rule is a world invariant.
- **Don't** introduce icons, emoji, or glyph fonts; controls are text parallelograms.
- **Don't** cast shadows from paper — shadows belong to foil-gold surfaces only.
- **Don't** rebuild the dark stat-tile analytics look this world refuses: no dark ground, no rounded stat cards, no chart-library defaults; charts are hand-drawn SVG/canvas from embedded data.
- **Don't** re-run the full 3D deployment outside an authored hero moment; ambient motion is limited to the fold-in entrance and chart draws.
