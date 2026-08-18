# OVC C2P2 Identity-Anchor Discrimination Plan v0.1

**Plan ID:** `OVC-C2P2-IDENTITY-ANCHOR-DISCRIMINATION-PLAN-v0.1`
**Programme ID:** `OVC-C2P2-IDENTITY-ANCHOR-DISCRIMINATION-v0.1`
**Short ID:** `C2P2-IAD`
**Status:** RATIFIED
**Operator instruction:** `I want to authorize a successor identity-anchor discrimination plan.`

## Purpose

Resolve the scientific deficiency exposed by `C2P2-SD`: A/B/C disagree strongly about persistent identity, but the prior blind review produced 72/72 `NOT_EVALUABLE` cases because the available candidate-independent evidence contained no positive identity anchors. This successor programme is therefore not another candidate-comparison run. Its purpose is to construct, qualify and use candidate-independent positive identity anchors capable of lawfully establishing `SAME` or `DIFFERENT` across an observation boundary.

The programme may recommend a candidate only after independent anchor evidence makes false-fragmentation and false-continuity errors estimable. It may never infer ground truth from A/B/C outputs, object counts, compression, runtime, family membership, similarity, or absence of a hard break.

## Frozen predecessor

The programme binds to the completed predecessor `C2P2-SD-GSEL` DEFER court record on branch `run/c2p2-sd-greal-20260818`, decision commit `71f459e0a2be90959b97d25ab36e24a8aba96305`, with selection state `COMPARATIVE_SET_ONLY_NO_WINNER_DEFERRED`, active ObjectPack `null`, C2P activation `NONE`, prior GREAL consumed with no replay remaining, 72 labels frozen `NOT_EVALUABLE`, Validation `LOCKED_UNCONSUMED`, and EC1 candidate-defining use `FORBIDDEN`.

Candidate generation remains frozen as `C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3`. No candidate, semantic threshold, structural role, clock, instrument, market, provider, side, or source identity is changed by this plan.

## Identity-anchor contract

Every anchor must be cutoff-safe and independent of A/B/C candidate outputs.

Allowed anchor classes:

- `POSITIVE_SAME`: affirmative owner-layer evidence that the two observations are the same independently defined structural object across the boundary. Absence of invalidation or absence of a hard break is not sufficient.
- `POSITIVE_DIFFERENT`: affirmative owner-layer evidence that identity cannot persist across the boundary, including an explicit upstream invalidation, governed role or geometry identity change, governed split/merge disposition, or required source discontinuity when the owner contract makes that identity-breaking.
- `AMBIGUOUS`: independent evidence supports more than one lawful identity interpretation.
- `NOT_EVALUABLE`: evidence cannot lawfully establish an identity label.

Candidate dispositions are predictions only. They may be compared against anchors after the anchor set is frozen, but may never define, filter, rank or revise the anchors.

A positive anchor is admissible only when its evidence source has a frozen owner contract that explicitly grants the relevant identity meaning. Repository proximity, shared episode membership, shared lineage, geometric similarity, price proximity, temporal adjacency, or persistence-by-default cannot establish `POSITIVE_SAME`.

If existing owner contracts cannot support positive anchors without adding or materially changing identity semantics, execution must stop at `C2P2-IAD-GOWNER`; this plan does not self-authorise a frozen-contract change.

## Statistical discrimination contract

For each candidate and each lawful evaluable anchor:

- false split = candidate does not assert `SAME` on a `POSITIVE_SAME` anchor;
- false join = candidate asserts `SAME` on a `POSITIVE_DIFFERENT` anchor;
- candidate abstention/ambiguity is reported separately.

WP6 must report exact counts and two-sided 95% Wilson intervals. A candidate recommendation is permitted only when both positive classes have non-zero denominators in every decision-relevant stratum claimed by the recommendation; BID and ASK and each discovery year 2021, 2022 and 2023 are represented; no unresolved anchor-admissibility warning or hard falsification applies; and for every competitor the recommended candidate's 95% upper confidence bound is no greater than that competitor's 95% lower confidence bound on both false-split and false-join rates, with strict separation on at least one metric. Any C-specific episode-enrichment claim is excluded unless a separately governed non-empty episode-relative role registry is lawfully in force before the real-source gate. Otherwise WP6 must recommend `DEFER`.

## Packet sequence

### C2P2-IAD-WP0 — Currentness, lineage and authority firewall
Bind current lawful main, predecessor decision commit, candidate generation, source identity, runtime/evidence/source-order bindings, consumed prior authorities and all non-transitive denials. Produce machine-readable programme state. No real-source access.

### C2P2-IAD-WP1 — Anchor schema, admissibility registry and falsification taxonomy
Materialise `IdentityAnchorEvidence`, provenance, anchor-admissibility and review-card contracts. Enumerate allowed positive evidence classes and fail-closed rejection reasons. Candidate identities remain unavailable to anchor construction.

### C2P2-IAD-WP2 — Owner-evidence census and computability matrix
Read repository contracts and already-preserved immutable evidence only. Determine which existing owner layers can lawfully provide positive `SAME` and `DIFFERENT` anchors, by side/year/role/geometry/clock context. No new provider intake and no fresh real-source semantic execution. If positive anchors require a new or materially changed owner contract, materialise `C2P2-IAD-GOWNER` as `OPERATOR_REQUIRED` and stop.

### C2P2-IAD-WP3 — Deterministic anchor extractor and adversarial fixtures
Implement candidate-blind anchor extraction against admitted owner evidence. Add synthetic/adversarial tests for false positive SAME, false positive DIFFERENT, future leakage, candidate leakage, role/geometry ambiguity, split/merge, discontinuity and deterministic replay.

### C2P2-IAD-WP4 — Existing-evidence rehearsal and capacity qualification
Exercise the extractor on already-preserved eligible evidence and synthetic worst cases. Quantify anchor yield, rejection reasons, memory/storage/checkpoint bounds and blinded review volume. This packet is non-evidentiary with respect to candidate selection.

### C2P2-IAD-GREAL — Fresh real-source anchor-evidence authority
`OPERATOR_REQUIRED`. A PASS may authorise exactly one bounded full-population discovery-shadow anchor extraction/comparison using the already frozen source materialisation. The gate must bind source artifact, candidate generation, runtime, anchor extractor, capacity and a single-use token. No selection or activation authority is implied.

### C2P2-IAD-WP5 — Full-population anchor extraction and blind comparison packet
After GREAL PASS only: generate the full anchor ledger, freeze anchor identities before candidate comparison, then compute candidate dispositions against the frozen anchor set. Sampling and reduced precision are forbidden. If non-mechanical anchor cases require human judgment, materialise `C2P2-IAD-GADJ` and stop before candidate unblinding.

### C2P2-IAD-WP6 — Error, uncertainty, coverage and Pareto analysis
Compute false-split, false-join, abstention/ambiguity, Wilson intervals, stratum coverage, hard falsifications and uncertainty-aware Pareto evidence. Apply the preregistered recommendation rules exactly. No selection or activation occurs in WP6.

### C2P2-IAD-GSEL — Final scientific ObjectPack selection review
`OPERATOR_REQUIRED`. Allowed decisions: `PASS_SELECT_NAMED_CANDIDATE`, `DEFER`, `BLOCK`, `QUARANTINE`. A PASS may record only the named scientific ObjectPack selection. C2P activation remains a separate operator-reserved gate and is never automatic.

## Authority envelope

Ratification authorises WP0-WP4 automatically when prerequisites and tests pass, including contracts, schemas, registries, deterministic implementation, synthetic/adversarial fixtures, read-only repository/evidence census, tests and QA.

Ratification does not authorise new real-provider intake or fresh real-source execution; material owner-contract or semantic changes; a new structural role, instrument, market, clock or side; A/B/C selection or promotion; C2P activation; ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT or ACTIVE_VALIDATION; canonical/R2 publication; EC1 candidate-defining use; or probability, risk, exposure, trading, execution or agent-write authority.

The first mandatory execution stop is `C2P2-IAD-GOWNER` if an owner-contract extension is required; otherwise it is `C2P2-IAD-GREAL`.

## QA and failure behaviour

Every packet must run targeted tests and repository-wide regression. Correctable in-scope implementation defects are repaired and retested automatically. Missing positive anchor support is not repaired by weakening the contract: it must be reported as `BLOCKED` or at `GOWNER`. No test, threshold or admissibility rule may be weakened to manufacture evaluable anchors.

## Rollback

Forward-supersede only. Preserve all R4/R5, C2P2-SD GREAL, GADJ, WP6 and GSEL evidence, consumed authority records and this plan's decisions. A failed or deferred successor programme leaves ObjectPack selection `NONE` and C2P activation `NONE`.
