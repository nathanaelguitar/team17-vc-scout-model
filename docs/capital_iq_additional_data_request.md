# Capital IQ additional data request — Layer B redesign

## Purpose and scope

Please provide a history-complete, company-keyed extract to build a forward-looking fixed-horizon startup screening cohort. The current files are useful transaction extracts, but they do not establish observation windows or non-event outcomes. Do **not** apply a `$1B` valuation filter to the population export: that filter is the main source of target ambiguity in the current model.

The supplied transaction export already contains these exact column names and should be retained in the refresh:

- `CIQ Transaction ID`
- `Target/Issuer`
- `All Transactions Announced Date`
- `All Transactions Closed Date`
- `Transaction Types`, `Transaction Status`
- `Total Transaction Value ($USDmm, Historical rate)`
- `Post-Money Valuation ($USDmm, Historical rate)`
- `Buyers/Investors`, `Sellers`, `Exchange:Ticker`

## Population, history, and file grain

| Request element | Specification |
| --- | --- |
| Population | All companies with a private financing, private placement, venture round, growth-equity round, or recorded private valuation from 1995 through extraction date. Include entities with no financing but a valid company record if feasible, in a separate company master. Include active, acquired, IPO, bankrupt, inactive, and delisted entities. |
| Geography / industries | Global, no country/industry restriction. Preserve Capital IQ industry taxonomy and geographic hierarchy. |
| History | Full available history through extraction date, with a clearly supplied `extract_as_of_date`. Do not truncate early rounds or select only latest/current valuations. |
| Company identity | Export the immutable Capital IQ company/entity identifier (commonly presented as a CIQ company ID) on every file. Also include legal name, aliases/former names, parent/ultimate-parent CIQ ID, and primary security/ticker where applicable. The ID field name should be documented if the interface uses a different label. |
| Round grain | One row per transaction/round with `CIQ Transaction ID`, company ID, announced date, closed date, record-last-updated date if available, and all round fields below. Separate participants to a transaction–investor bridge if necessary. |
| Valuation grain | One row per company valuation observation: company ID, valuation date/as-of date, valuation value/currency, valuation basis/type, and source/verification status. Include values above and below $1B. |
| Company/lifecycle grain | One row per company with history table for dated status changes and dated operating metrics. |
| Exit grain | One row per exit event (IPO, acquisition, liquidation/bankruptcy, inactive), keyed to company ID and dated. |

## Required fields and use

| Field or export concept | Required dates / keys | Primary use | Priority |
| --- | --- | --- | --- |
| Immutable Capital IQ company ID; aliases; parent and ultimate-parent IDs | Company ID on every record | Entity resolution, deduplication, group splitting, related-entity exclusion | Must have |
| Company name, founding/incorporation date, headquarters city/state/country, industry and subindustry, business description, ownership status | Company ID; effective/as-of date when historical | Population definition, landmark eligibility, matching, valid pre-index features | Must have |
| Operating status plus dated status history | active/inactive/closed/bankrupt/acquired/IPO; status-effective date, last-verified date | Censoring, competing outcomes, negative-label validity | Must have |
| Capital IQ coverage start date, coverage end date, last verified/updated date, record creation date | Company ID, source/system dates | Determine whether a company is actually observed for the full 2/3/5-year horizon | Must have |
| Complete valuation history | Company ID, valuation date/as-of date, value, currency, valuation type/basis/source | Outcome: first dated post-money/company valuation `>= $1B`; detect down rounds and distinguish missing valuation from sub-threshold valuation | Must have |
| Complete financing/transaction history | Company ID, `CIQ Transaction ID`, announced and closed dates, type, status, round amount, pre/post-money value, currency | Pre-index funding features and event timing; avoid future-round leakage | Must have |
| Round type/stage, financing status, amount, pre-money/post-money valuation | Transaction ID and company ID; announcement/close dates | Landmark definition and funding-stage matching; legitimate features | Must have |
| Transaction–investor bridge including investor CIQ ID, lead/co-lead flag, investor role/type, announced/close dates | Transaction ID, investor ID | Investor count/type, lead quality, syndicate composition, network leakage controls | High |
| Investor master and historical outcomes | Investor ID; dated portfolio investments, realized IPO/acquisition/unicorn events where licensed | Pre-index investor-quality features; all aggregates must be computed only through snapshot date | High |
| Revenue, revenue growth, EBITDA/operating metrics, employee count and dated changes | Company ID, fiscal period end/as-of date, source/verification date | Legitimate fundamental/traction features; only observations available at snapshot | High |
| Website traffic, customer/user metrics, product launch dates | Company ID, metric period/as-of/source date | Optional pre-index traction features and coverage diagnostics | Medium |
| IPO, acquisition, bankruptcy/liquidation, inactive, distressed financing, and down-round events | Company ID, event/announcement/close date, transaction ID where relevant | Competing-risk labels and survival endpoints | Must have |
| Source/provenance, confidence/verification status, record update date for each value | Company/transaction/valuation ID and timestamps | Missingness audit and as-of leakage control | High |

## Explicit label and cohort rules to support

For each snapshot date `t` and horizon `h` in {2, 3, 5} years:

- Positive: first verified company/round post-money valuation `>= $1B` occurs in `(t, t+h]`.
- Negative: coverage is continuous or explicitly verified through `t+h`; no qualifying `$1B+` valuation occurs by `t+h`; company has not had a competing terminal outcome before `t+h` (or is handled as a competing risk).
- Censored: coverage ends before `t+h`, status is unknown, or entity is otherwise not observable through the horizon. Never silently label it negative.
- Competing outcome: acquisition, IPO, closure/bankruptcy, or inactivity before `t+h`. Supply enough dates to report this separately and choose a documented treatment.

Use prediction landmarks that have a clear real-world decision point: first institutional round, Seed, Series A, Series B, and fixed anniversaries after first recorded financing/founding. All matching variables (founding cohort, industry, geography, stage, age, calendar period, capital to date) should be retained in a separate study-design table and excluded from the predictive feature contract unless their deployment availability and intended use are explicit.

## Acceptance checks on delivery

1. Every transaction, valuation, lifecycle, and exit row joins by immutable company ID; transaction participants also join by `CIQ Transaction ID`.
2. Extract manifest states population filters, record counts, maximum/minimum dates, as-of date, field definitions, and whether deleted/inactive entities are retained.
3. A random sample of companies has reconciled company history, valuation history, and lifecycle dates.
4. The export includes companies that never cross `$1B`, rather than a `$1B+` outcome screen plus an unrelated sub-threshold control screen.
5. Dates identify when information was known/verified, not solely an updated current value. This is required to prevent indirect post-outcome leakage.

## Current-data gap

The current files contain only transaction-level fields listed at the top. They do not currently contain immutable company IDs, coverage dates, founding date, lifecycle/exit status, full valuation histories, reliable round-stage taxonomy, or fundamentals. The requested field labels above are descriptive where exact Capital IQ UI labels cannot be identified from the files; please preserve the vendor’s exact exported labels and include a data dictionary rather than substituting values.
