# C2P2 Identity-Anchor Evidence Contract v0.1

Programme: `OVC-C2P2-IDENTITY-ANCHOR-DISCRIMINATION-v0.1`  
Packet: `C2P2-IAD-WP1`  
Status: `FROZEN_RESEARCH_CONTRACT / PRE_REAL_SOURCE`  
Authority effect: `NONE`

## Purpose

This contract defines candidate-independent empirical labels for testing persistent-object candidates after `C2P2-SD-GSEL=DEFER`. It does not define, select, promote or activate an ObjectPack.

## Label domain

Every identity edge is labelled exactly one of:

- `POSITIVE_SAME` — affirmative evidence from an independently governed owner layer establishes that the two observations refer to the same owner-defined structural object across the edge.
- `POSITIVE_DIFFERENT` — affirmative owner-layer evidence establishes that identity cannot persist across the edge.
- `AMBIGUOUS` — admissible evidence supports more than one lawful identity interpretation or contains an unresolved owner-level conflict.
- `NOT_EVALUABLE` — the available cutoff-safe evidence does not establish either positive class and does not establish an admissible conflict.

`POSITIVE_SAME` and `POSITIVE_DIFFERENT` are scientific ground-truth anchors for this programme only when every admissibility rule below is satisfied.

## Candidate independence

A/B/C ObjectPack outputs, tracklets, ObjectAssertions, object counts, compression, runtime, candidate geometry-compatibility decisions and candidate relation-continuity decisions may not create, filter, rank, revise or resolve an anchor label. Candidate outputs are joined only after the anchor ledger has been frozen.

No C2P-created durable identity may be used as owner ground truth for judging another C2P candidate. The frozen C2P identity hierarchy remains downstream of C2 observations.

## Positive SAME admissibility

`POSITIVE_SAME` requires an owner contract that explicitly grants persistent identity meaning to an owner field or lineage relation and evidence that the exact governed identity/continuation relation holds at both sides of the edge as of the evaluation cutoff.

The following are never sufficient by themselves:

- absence of invalidation, terminal break or source gap;
- equal price, equal geometry, equal bounds or equal relation topology;
- equal structural role or geometry kind;
- temporal adjacency, proximity or elapsed-time continuity;
- shared episode, family, context, horizon, parameter pack or observation segment;
- a C2P candidate's `SAME` disposition;
- heuristic similarity, nearest-neighbour choice or retrospective outcome.

## Positive DIFFERENT admissibility

`POSITIVE_DIFFERENT` requires an owner contract that explicitly declares the observed fact identity-breaking for the relevant owner object. Candidate-independent eligible classes are:

- `EXPLICIT_UPSTREAM_INVALIDATION`;
- `DECLARED_STRUCTURAL_ROLE_IDENTITY_CHANGE` when the owner contract declares role identity constitutive;
- `DECLARED_GEOMETRY_KIND_IDENTITY_CHANGE` when the owner contract declares geometry identity constitutive;
- `SPLIT_PARENT_DISPOSITION` under an owner genealogy contract;
- `MERGE_PARENT_DISPOSITION` under an owner genealogy contract;
- `REQUIRED_SOURCE_DISCONTINUITY` when the owner contract declares the discontinuity identity-breaking;
- `OWNER_OBJECT_IDENTITY_CHANGE` when both owner identities are first-valid, immutable and governed as distinct objects.

A changed record ID is not automatically `POSITIVE_DIFFERENT`: the owner contract must establish that the ID is object identity rather than snapshot, observation, version or content identity.

## Owner authority requirement

An anchor source is admissible only when its exact owner contract is present, frozen/current for the studied materialisation, and explicitly specifies the identity semantics used by the anchor extractor. Prose inference, implementation behaviour, test behaviour and downstream convention do not substitute for an owner contract.

If the existing owner contracts do not supply the required persistent identity semantics, this programme must stop at `C2P2-IAD-GOWNER`. Adding or materially changing such semantics is operator-reserved and is not authorised by WP1.

## Time and leakage firewall

All evidence must be first-valid no later than the edge evaluation cutoff. Future observations, outcomes, future price, Validation, downstream semantic labels and post-cutoff lifecycle events are prohibited. Anchor construction must occur before candidate dispositions are joined.

## Falsification taxonomy

- `FALSE_FRAGMENTATION`: candidate disposition is not `SAME` on a frozen `POSITIVE_SAME` edge.
- `FALSE_CONTINUITY`: candidate disposition is `SAME` on a frozen `POSITIVE_DIFFERENT` edge.
- `HARD_IDENTITY_CONTRADICTION`: candidate asserts `SAME` across a positive owner identity-break whose owner contract makes persistence impossible.
- `ANCHOR_UNCOMPUTABLE`: required owner evidence is absent, late, ambiguous, censored or contract-inadmissible.
- `ANCHOR_CONTRACT_CONFLICT`: two admissible owner sources conflict and neither has declared precedence.

`AMBIGUOUS` and `NOT_EVALUABLE` never enter false-fragmentation or false-continuity denominators.

## Reproducibility

Every anchor must bind the prior/current source record IDs, owner contract ID/path/hash, owner evidence identities, first-valid times, evaluation cutoff, admissibility rule ID, label and deterministic content hash. Exact replay of identical inputs must reproduce byte-identical anchor identity and label.

## Authority and rollback

This contract authorises no real-source execution, owner-contract modification, semantic promotion, ObjectPack selection, C2P activation, Validation, publication, EC1 candidate-defining use, probability, risk, exposure, trading, execution or agent write. Rollback is forward supersession while preserving this contract and all predecessor evidence.
