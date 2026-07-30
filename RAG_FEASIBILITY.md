# Why We Can't Do RAG Yet — and How to Fix It

## What RAG would look like here

A retrieval-augmented generation pipeline for VC Scout would work roughly like this: embed each company's profile into a vector space, then at query time retrieve the most similar companies to a given startup and use those as context for a valuation or investment recommendation. The appeal is real — instead of a model that only sees six engineered features, a RAG system could surface nuanced analogues ("this is similar to Stripe at Series B" or "the last three logistics unicorns from Southeast Asia took 7–9 years").

## Why we can't do it yet

### 1. Not enough rows

Our eligible regression dataset tops out at roughly **1,050–1,100 unicorn companies** after cleaning. A retrieval system needs a large enough index that the *k* nearest neighbors it returns are actually semantically meaningful, not just "all the fintech companies" because there are only 80 of them. At this size, you're not retrieving analogues — you're retrieving the only options that exist.

A rough rule of thumb: RAG retrieval becomes useful when the index has **at least 10,000 semantically distinct documents** in the domain. We're an order of magnitude short.

### 2. Not enough text

Our data is almost entirely structured (numbers and category labels). RAG is most powerful over rich, unstructured text — pitch decks, investor memos, news coverage, founder bios, product descriptions. Right now the only text field we have is `investors`, which is just a comma-separated name list. There's nothing for an embedding model to sink its teeth into.

Vector similarity on one-hot-encoded category strings is just a slow version of exact matching. That's not RAG — that's a lookup table.

### 3. The sparse coverage problem

Of our 75,000 rows in the master dataset, only ~1,830 have valuations. The other 73,000+ are control companies with no valuation signal. A retrieval system that returns control companies as nearest neighbors is actively harmful: it gives the LLM context that has no ground truth to reason from.

### 4. Survivorship bias compounds at retrieval time

Our dataset is entirely composed of companies that *became* unicorns. A RAG system built on this would retrieve only success stories, making every recommendation look like a good investment. Without a balanced set of companies that tried and failed, retrieved context will be systematically misleading.

---

## What the team could do to make RAG viable

### High-impact data additions

| Addition | What it unlocks | Approx. rows gained |
|---|---|---|
| **Crunchbase / PitchBook full export** | Funding history, founding team size, HQ, description text, all rounds | +50K–200K companies |
| **CB Insights company profiles** (scraped or API) | Analyst write-ups, market maps, momentum scores | Rich text per unicorn |
| **SEC Form D filings** (EDGAR full-text) | Actual raise amounts, investor names, deal timing | +500K filings/year |
| **LinkedIn company pages** (via partner API) | Headcount growth, hiring patterns, leadership tenure | Growth signals |
| **Crunchbase news/press** | Product launches, pivots, executive changes | Text corpus |
| **Wikipedia company articles** | Standardized narrative, founding story, business model | ~3K–5K companies |

### Structural changes to the dataset

**Add failed companies.** The single biggest gap is the absence of startups that raised $10M–$100M and *didn't* become unicorns. Without them, no retrieval system can distinguish "this looks like Stripe" from "this looks like every funded fintech startup." The Crunchbase 2015 export in our `control_funded` tier is a start, but it needs description text and outcome labels.

**Add time-series snapshots.** We already have a valuation panel (2022/2024/2025/2026) for some companies. Expanding this to funding rounds (amount, date, lead investor, valuation at round) turns each company into a trajectory rather than a point, which makes embedding much richer.

**Add founder-level data.** Prior exits, school, previous companies, and years of experience are among the strongest predictors of unicorn outcomes in the academic literature. This also gives the text embedder something meaningful to encode.

**Scrape pitch deck summaries or CrunchBase descriptions.** Even 2–4 sentence descriptions per company would be enough to make semantic search meaningful. Right now we have nothing.

### Minimum viable RAG threshold

Before the team revisits a RAG pipeline, aim for:

- [ ] **≥ 10,000 companies** with valuation or outcome label
- [ ] **≥ 1 paragraph of text** per company (description, founder bio, or news summary)
- [ ] **≥ 30% non-unicorn coverage** so retrieval doesn't only return success stories
- [ ] **≥ 3 time-point snapshots** per company where possible (early, mid, late stage)

Once those boxes are checked, a practical first step would be embedding company descriptions with `text-embedding-3-small`, storing in a lightweight vector DB (ChromaDB or pgvector), and retrieving 5–10 analogues at inference time to give the LLM grounding context alongside the structured model output.

---

*Written 2026-07-21. Dataset state: ~1,830 unicorn rows, ~1,050 eligible for valuation regression after cleaning.*
