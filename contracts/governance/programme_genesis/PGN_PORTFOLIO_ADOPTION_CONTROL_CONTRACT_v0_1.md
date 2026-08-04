# PGN Portfolio Adoption Control Contract v0.1

## Status and authority

`FROZEN_CANDIDATE` under `PGN-WP1 / PGN-G1`. This contract defines deterministic governance controls only. It grants no native-adoption, dependency-edge, warning-closure, route, corpus or admission-enforcement authority.

## 1. Native adoption bundle

Every candidate must contain an exact programme identity, candidate class, purpose, included/excluded scope, governing-source list, authority envelope, lifecycle projection, source dossier, current or retrospective scope audit, migration crosswalk and unresolved-field ledger. `UNKNOWN_CLASS`, missing authoritative source, unresolved authority conflict or fabricated historical intent blocks native adoption. Candidate status is `CANDIDATE_UNAPPROVED` and `authority_effect=NONE` until `PGN-G3` records a per-programme operator decision.

## 2. Census stop

`PGN-WP2` may discover and classify the portfolio but may not construct native candidates. `PGN-G2A` operator acknowledgement or adjusted-scope decision is a hard prerequisite for `PGN-WP3`. Surprise discoveries, exclusions, PCCR classification and proposed review groups must be explicit.

## 3. Progressive PGN-G3 review

Candidates are grouped by programme class or authority domain. A review group contains one to three candidates. The next group may not be disclosed until the operator records an acknowledgement receipt for the current group. A group acknowledgement is not adoption and has `authority_effect=NONE`. Final adoption remains per programme at `PGN-G3`.

## 4. Edge challenge protocol

Every cross-programme edge candidate records proposer, affected programme owners, edge type, direction, hardness, source kind and exact evidence. Hard `REQUIRES`, `GOVERNED_BY`, `BLOCKED_BY` and hard `CONSUMES` edges require source-explicit evidence. Owners receive a 48-hour challenge window unless every notified owner explicitly waives the remaining time. A challenge immediately changes the effective classification to `ADAPTER_INFERRED`, effective hardness to `SOFT` or `INFORMATIONAL`, and prerequisite satisfaction to false. Only accepted source-explicit evidence may restore the original hard classification. Challenges and resolutions are append-only.

## 5. Migration warning closure

Warnings close individually through evidence. `MIGRATION_UNCERTAINTY` requires accepted native adoption plus a complete migration crosswalk. Hash mismatch blocks. Missing coverage remains unresolved unless an authoritative source establishes `NOT_APPLICABLE`. Duplicate authority sources require an accepted precedence or supersession decision. Source records are never edited to fit projections. Every closure records before and after health hashes. Bulk suppression is prohibited.

## 6. Read-only Control Plane

The build may expose disabled candidate surfaces for overview, programme detail, dependency graph, health, impact and admission preview. No POST, PUT, PATCH, DELETE or equivalent write path may exist. No repository credentials, approval, merge, publication or enforcement action may be exposed. Registration and listening remain denied until `PGN-G8`.

## 7. Admission preview advisory status

Every admission-preview invocation must display and log acknowledgement of this exact statement:

> This evaluation is non-binding advisory evidence only. It does not satisfy any gate requirement and does not prevent operator review of proposals that fail preview criteria. PGN-G10 enforcement, if activated, may produce different results.

Every preview record has `authority_effect=NONE`. Preview output cannot satisfy a gate or block operator review.

## 8. Independent shadow corpus

The corpus is versioned and hash-bound. It requires independent operator acceptance at `PGN-G9A` before scoring. Negative cases must originate from at least two distinct programme sources. At least one adversarial case set must attempt scope gaming, missing-authority bypass or maintenance-ceiling evasion. The enforcement implementation team cannot be the sole curator. Any accepted-corpus mutation creates a new version and invalidates prior metrics.

## 9. Read-model performance

A full rebuild for the current eight-programme baseline has a soft target of 60 seconds on a recorded reference environment. Exceeding the target emits `REBUILD_LATENCY_WARNING` and may not skip validation. Partition order is programme class, then constitutional parent, followed by deterministic cross-partition reconciliation. Performance evidence is advisory and never grants authority.

## 10. Permanent denials

Graph position, tests, QA, merged PRs, acknowledgements, route availability and advisory preview results never grant authority. Selector activation, ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT, ACTIVE_VALIDATION, semantic/model/family/candidate/theory promotion, canonical or R2 publication, provider intake, release freeze, retirement, agent write, probability, risk, exposure, trading and execution remain outside this contract.

## Rollback

Supersede this contract non-destructively, disable derived candidates and surfaces, and preserve every source, warning, challenge, decision, PR, commit and receipt.
