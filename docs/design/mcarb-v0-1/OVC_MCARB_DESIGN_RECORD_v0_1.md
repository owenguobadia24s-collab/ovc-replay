# OVC MCARB v0.1 — Design Court-Record Receipt

**Programme:** `OVC-MCARB-v0.1`  
**Design document:** `OVC-MCARB-DESIGN-SPEC-0.1`  
**Baseline:** `main@d90432957df146bf448287cedf4da73a8c861ebe`  
**Branch:** `design/mcarb-v0-1`  
**Status:** `GATE_READY` — operator review required  
**Authority effect:** `NONE`

## Bound external design artifact

The complete 34-page Design Specification v0.1 is stored outside Git and bound here by immutable digest.

- Drive file ID: `1CFnhQ5OlEQSwLbgoRfdCSWNfgIunRSDF`
- Drive URL: `https://docs.google.com/document/d/1CFnhQ5OlEQSwLbgoRfdCSWNfgIunRSDF/edit`
- DOCX SHA-256: `f07913a77842609f9b4d993c66113cee7d12441ae6049ffe9cf072a98d8effb2`
- Markdown source SHA-256: `7ceae68412b0dc710aea38763d9250f531015fa2e74a49189b8c3c7ddbbc723b`
- Local rendered QA: 34 pages, all pages visually inspected; no clipping, overlap or broken tables.

The external document contains sections 0–34 and Appendices A–J, including all eight required authority/data-flow diagrams, candidate AL/ET/VS catalogues, R0–R6 representation matrix, chronology rules, ablation/failure attribution, external research crosswalk, typed object catalogue, QA/capacity design, risks, deferred modules and consolidated design verdicts.

## Primary design decision

Establish MCARB as a separate, method-neutral auxiliary-representation research programme. It asks how much recurring market structure is representable from price geometry/current structural evidence alone and whether lawful contemporaneous auxiliary evidence explains residual distinctions reproducibly.

MCARB v0.1 does **not** add new C2 axes. It introduces a provisional **Auxiliary Evidence Plane (AEP)** containing three independently versioned benchmark domains:

1. `AL` — Activity / Liquidity evidence.
2. `ET` — Intrinsic / Event Time evidence.
3. `VS` — Volatility State evidence.

C2 remains the structural-price evidence authority. Canonical 15M/2H clocks remain unchanged. AEP may only supply explicit evidence references to OccurrenceContext and explicit RepresentationPacks through SRI. No AEP record may rewrite OPT-A/C1/C2/C2E, depend on future outcomes, or inherit downstream family/semantic authority.

## Scientific outcomes

Valid terminal evidence includes `MATERIAL_ADDITIONAL_INFORMATION`, `LIMITED_CONTEXTUAL_INFORMATION`, `REDUNDANT_WITH_PRICE_STRUCTURE`, `UNSTABLE_ACROSS_TIME`, `METHOD_DEPENDENT`, `NOT_REPRODUCIBLE`, `NOT_EVALUABLE`, `REJECT`, and `UNRESOLVED`. Null evidence is a valid success when reproducibly established.

## Source-semantics court-record findings

Confirmed from the current repository:

- OPT-A v2 observation bars structurally carry a nullable, quality-labelled `volume` object.
- The OPT-A volume contract states volume is provider-declared data, not universal spot-FX market volume.
- BID and ASK volume are retained separately by contract.
- Current provider source families are M1/H1 × BID/ASK.
- Discovery 2021–2023 and Development 2024 releases are remote-verified; Validation 2025 remains `LOCKED_UNCONSUMED`.

Not established by this design review and therefore still gated:

- exact active-payload provider volume field/unit/interpretation distribution — `REQUIRES_SOURCE_SEMANTICS_AUDIT`;
- quality-state distributions by year/side/source grain — `REQUIRES_SOURCE_SEMANTICS_AUDIT`;
- retained tick objects, tick/update counts, or synchronized historical tick spread — `REQUIRES_COURT_RECORD_VERIFICATION`;
- durable source-object reread path without a new provider request — `REQUIRES_COURT_RECORD_VERIFICATION`.

MCARB must never equate Dukascopy provider activity with centralized FX traded volume, infer buyer/seller intent from BID/ASK activity, or label coarse M1/H1 paired-bar differences as exact historical tick spread.

## Benchmark representations

- `R0`: price-structural baseline.
- `R1`: price + AL.
- `R2`: price + ET.
- `R3`: price + VS.
- `R4`: price + AL + VS.
- `R5`: price + ET + VS.
- `R6`: price + AL + ET + VS.

Auxiliary-only packs are diagnostic/ablation surfaces and cannot masquerade as production structural models. Every RepresentationPack must bind exact parents, fields, normalization, time basis, first-valid rule, missingness, comparability domain, lookback, scale, side handling, aggregation and prohibited downstream uses. No hidden defaults are allowed.

## Evaluation and attribution

MCARB is descriptive, not predictive. Results are multi-dimensional across discrimination, recurrence, residual reduction, chronological stability, cross-scale stability, boundary quality, contemporaneous counterexample separation, interpretability, robustness, redundancy, capacity and missingness tolerance. No opaque global score is permitted.

Mandatory controls include AL-only/ET-only/VS-only ablation, individual-measure ablation, matched-complexity controls, time-of-day matching, lawful shuffled/null controls, threshold/sensitivity analysis, normalization alternatives and explicit family-method attribution. Failure reasons include source-semantic invalidity, clock confounding, normalization/threshold/family-method dependence, dimensionality artifacts, temporal instability, missingness domination, side dependence, capacity exceeded and no additional information.

## Chronology and missingness

Every MCARB object resolves to source release, source IDs, admissible cutoff, start/end, `first_valid_time`, calculation version, parameter pack, missingness, lineage and comparability domain. Retrospective segmentation is labelled `RETROSPECTIVE_BENCHMARK`; it cannot be presented as causal online evidence. No centered window may be used causally without representing its confirmation delay.

Missingness is evidence. Required states include `AVAILABLE`, `PARTIAL`, `NOT_EVALUABLE`, `SOURCE_FIELD_ABSENT`, `SOURCE_INTERVAL_GAP`, `INSUFFICIENT_HISTORY`, `WARMUP_INCOMPLETE`, `SIDE_UNAVAILABLE`, `PARAMETER_NOT_APPLICABLE`, `RETROSPECTIVE_ONLY`, `STALE`, `CONFLICT`, and `QUARANTINED`. Activity/quote evidence is never interpolated merely to complete a vector.

## Architectural relationships

- **C2:** no redesign in v0.1; AL/ET/VS remain outside initially.
- **C2E:** MCARB may benchmark boundary evidence but cannot activate/replace canonical C2E boundary logic.
- **OccurrenceContext:** may reference lawful intrinsic-coordinate/activity/volatility records without changing structural identity.
- **SRI:** may consume auxiliary evidence only through explicit RepresentationPacks.
- **SRFD:** remains the method benchmark for representation/distance/family science; MCARB asks which lawful evidence channels may be consumed. The current SRFDI-G8 `REDESIGN` state and capacity constraints are preserved.
- **Validation:** denied/unconsumed in MCARB v0.1.

## Design verdicts

1. MCARB separate from SRFD — `ACCEPT_DESIGN`.
2. Provisional AEP — `ACCEPT_WITH_CONDITIONS`.
3. AL outside C2 initially — `ACCEPT_DESIGN`.
4. ET parallel to canonical time — `ACCEPT_DESIGN`.
5. VS distinct from MOTION — `ACCEPT_DESIGN`.
6. Current inputs available — `ACCEPT_WITH_CONDITIONS`: M1/H1 BID/ASK + governed nullable volume confirmed; semantics/ticks unresolved.
7. Availability claims requiring audit — `ACCEPT_DESIGN`.
8. OccurrenceContext connection — `ACCEPT_WITH_CONDITIONS`: references only.
9. SRI connection — `ACCEPT_WITH_CONDITIONS`: explicit packs only.
10. Scientific utility/threshold/normalization/family effects — `DEFER`, `REQUIRES_EMPIRICAL_BENCHMARK`.
11. Before implementation plan — `ACCEPT_WITH_CONDITIONS`: operator design acceptance plus formal source-semantics/court-record audit.
12. Next gate authority — `ACCEPT_WITH_CONDITIONS`: design acceptance only; no benchmark run authority.

## Deferred modules

`MCARB-2` CFTC Positioning, `MCARB-3` Scheduled Information/Economic Events, `MCARB-4` Vintage Fundamental State, `MCARB-5` Cross-Market Context and `MCARB-6` Options/Richer Microstructure remain deferred and receive no authority.

## Gate boundary

`MCARB-D8` is `OPERATOR_REQUIRED`. Recommended decision: `PASS` with source-semantics/court-record audit conditions. PASS accepts the design and permits preparation of a **separate implementation plan only**. It does not authorise source reread, new provider intake, benchmark execution, selector/representation/family/event promotion, C2/C2E changes, publication, Development/Validation use, probability, risk, exposure or execution.

Allowed operator decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

**Capability is not authority.**
