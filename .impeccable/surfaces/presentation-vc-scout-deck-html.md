---
version: 1
slug: "presentation-vc-scout-deck-html"
primary_target: "presentation/vc-scout-deck.html"
related_targets: []
---

# Surface brief: presentation/vc-scout-deck.html

**Scope & mode:** Persuade. Live 10–15 min capstone presentation deck, 13 slides + folded Q&A cells; presented by Team 17 to Cornell faculty; also revisited async and printed to PDF.

**Audience/job:** Faculty judges must understand the full VC Scout arc (data → tournament → audit → honest revision → residual scouting → Capital IQ classifier → framework) and remember this deck over every other team's.

**Direction (locked):** Miura-Fold Deployment world (seed 2aeaa1a3, user-chosen). Palette sheet-white #F7F7F7 / ink #0A0A0A / foil gold #D4AF37 (surfaces only; text-gold is #8a6d1c for contrast) / mountain-gray #B9B6AE / valley-blue #CFE0F2. Display: Chakra Petch (self-hosted). Spec mono: B612 Mono (Airbus cockpit face, self-hosted). Components are parallelograms sheared to the 60° crease grid. NO kickers/eyebrows above headings.

**Approved composition (user pick 2026-08-03): HYBRID of comp-b + comp-c** (`comp-b-unfolding-stage.png` + `comp-c-split-board.png`, both approved:true; comp-a supplies in-cell data styling).
- Title slide + four hero moments + act breaks: comp-b's dimensional 3/4 deployment — CSS-3D Miura sheet visibly unfolds, titles ride crease seams, then facets settle flat for reading.
- Data slides: comp-c's split board — left folded spine (gold packet header, M-01…M-13 fold-map agenda, active cell gold, spec block at foot), right large flat chart canvas framed by a scored crease border. Spine collapses to a thin rail during hero slides.
- Transition between modes must read as ONE sheet folding/settling, never as two decks.

**Memorable moment:** the audit reveal — 950 of 1,058 cells misfolded, one pull refolds them corrected — and the final zoom-out showing the whole deck as one deployed sheet.

**Ingredient inventory (medium gate):**
| Ingredient (from comps) | Medium |
|---|---|
| Fold-cut display type | Chakra Petch webfont, embedded woff2 (HTML/CSS) |
| Spec mono annotations | B612 Mono webfont, embedded woff2 |
| Gold foil packet + gold surfaces | generated raster foil texture tile (data URI) over CSS gold, ink text on top |
| Sheet paper grain | SVG feTurbulence filter (code) |
| 3D Miura deployment (title/heroes/act breaks) | CSS 3D transforms + JS choreography (the form's web leverage — built, not imitated) |
| Fold-map spine/rail (M-01…M-13) | HTML/SVG parallelogram cells, clickable navigation |
| All charts (tournament, era ridges, importance, elasticity, residual ledgers) | SVG drawn from embedded data, animated on slide entry |
| Audit grid (1,058 cells, 950 refold) + trajectory field (1,313 lines) | canvas (60fps), SVG/HTML overlay for labels + hover |
| Live explorer controls | HTML parallelogram tabs/sliders + SVG gauge (OLS companion coefficients embedded) |
| Icons | none — controls are text parallelogram tabs per world grammar; no emoji/unicode glyphs |

**Compositional commitments (from approved comps):** progress rail of 13 parallelogram cells (bottom on hero slides, left spine on data slides); headline levels: fold-cut display ≤6rem for slide titles, spec mono for data labels; signature geometry: 60° shear, scored crease borders, mountain-gray/valley-blue crease lines; annotation tags are parallelograms (e.g. "0.51 → 0.303"); gold packet appears on title, spine header, and close.

**Data honesty:** every number from repo source-of-truth files (embedded, traceable); comps' invented chart content (ARR metrics, unicorn-density chart) is explicitly NOT literalized. Small-n confidence flags rendered as partially-unfolded cells. No success-probability claims.

**States:** slide enter (deploy), replay (R), reduced-motion (instant flat), print (one slide per page, flat), hover (trajectories, ledger rows), explorer input states, Q&A cells folded until opened.

**Unresolved:** none blocking build.
