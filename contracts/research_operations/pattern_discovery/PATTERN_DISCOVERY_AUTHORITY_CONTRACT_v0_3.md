# Pattern Discovery Authority Contract v0.3

## Identity

- Contract ID: `RO.C2.PATTERN_DISCOVERY.AUTHORITY.v0.3`
- Governing plan: `OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER.v0.3`
- Owner: `RESEARCH_OPERATIONS`
- Status before PD-G0: `CANDIDATE_DESIGN_FREEZE`

## Purpose

Transform the active canonical C2 Discovery stream into derived transition records, candidate windows, deterministic fingerprints, novelty assessments, provisional clusters and review-queue projections without creating new canonical market meaning.

## Allowed reads

- Exact active C2 Discovery release, manifest and selector identity.
- C2 level, container, relation, five-axis state, quality and transition records.
- Exact parent C1 and OPT-A identities needed for lineage and the price strip.
- Research Operations QA, operator and evidence registries.

## Allowed outputs

- `TransitionRecord`
- `TriggerEvent`
- `CandidateWindow`
- `PatternFingerprint`
- `NoveltyAssessment`
- `ClusterVersion`
- `ReviewQueueItem`
- `ReviewDecision`
- Non-evidentiary replay comparison packets
- Governed append requests to the existing C2 prospective-evidence service after PD-G4

All outputs before a governed human freeze are derived and replaceable.

## Prohibited reads and features

- Validation data or consumed holdouts.
- OPT-C or OPT-D outcomes.
- Returns, MFE, MAE, winning horizons or trade labels.
- C2E episodes, C2.5 labels or C3 meanings as selection features.
- Historical 202-story, 58-candidate or B-STATE material as prospective seed evidence.

## Prohibited authority

This layer cannot:

- rewrite C2, C1 or OPT-A;
- mutate selectors, releases, parameter packs or R2 objects;
- promote clusters to episodes, families or archetypes;
- activate novelty ranking without a separate gate;
- create probability, eligibility, risk, exposure, trading or execution authority;
- self-approve any gate;
- permit agent writes.

## Population separation

- `DISCOVERY_CANDIDATE_POPULATION`: every valid deterministically closed candidate, eligible suppressed candidate and eligible control; excludes invalid, quarantined, mixed-version and replay-only rows.
- `HUMAN_REVIEWED_POPULATION`: candidates with a recorded review, dismissal, control adjudication or assignment challenge.
- `CANONICAL_EVIDENCE_POPULATION`: only valid frozen C2 prospective-evidence records.

No count or status may be transferred between these populations implicitly.

## Processing modes

- `LIVE_PROSPECTIVE`: post-authority first-valid processing; may contribute to future prospective evidence after human freeze.
- `TIME_GATED_REPLAY`: historical processing with enforced admissible cutoff; does not increment prospective evidence.
- `NON_EVIDENTIARY_REPLAY`: workflow, training and R&D only.

## Fail-closed rule

Unknown vocabulary, missing immutable lineage, mixed versions, selector drift, future-data access, audit failure or prohibited dependency produces `BLOCK`, `QUARANTINE`, `INVALID` or an explicit `NOT_EVALUABLE` state. It never silently becomes neutral or valid.

## Gate boundary

`PD-G0` may approve this design contract and permit `PD-WP1` implementation. It may not activate prospective processing, novelty ranking, evidence append, C2E or any downstream authority.