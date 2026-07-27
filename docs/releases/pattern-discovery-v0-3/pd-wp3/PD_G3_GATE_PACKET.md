# PD-G3 — Fingerprint and Provisional Cluster Acceptance

## Gate identity

- Gate ID: `PD-G3`
- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Baseline: `ff9f8a9604d352bb37777e04282cd0641e5f38b8`
- Branch: `build/pd-wp3-fingerprint-clustering`
- Pull request: `#94`
- Prerequisite: `PD-G2 PASS`

## Proposed authority delta

Accept deterministic fingerprints, the frozen composite distance, hard partitioning, exact PAM and immutable provisional ClusterVersions as derived research inputs for the simple review UI.

This gate grants no family promotion, semantic naming, archetype authority, C2E/C3, active novelty ranking, evidence write, selector/release mutation, R2, Validation, probability, exposure, trading, execution or agent authority.

## Acceptance evidence

- identical inputs produce identical fingerprints and clusters;
- arrival order does not change medoids or membership;
- lower-k/cost/lexicographic tie-breaking is enforced;
- later better representatives may displace early medoids;
- mixed versions fail closed;
- small partitions return `UNASSIGNED_SMALL_SAMPLE`;
- partitions over 500 return `CLUSTER_BUILD_CAPACITY_BLOCK`;
- hard partitions never compete;
- prohibited outcome and semantic features are rejected;
- focused, retained and canonical suites pass.

## QA

- Dedicated PD-WP3 workflow `30264050530`: PASS.
- Generic canonical workflow `30264050496`: PASS.
- QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp3/PD_WP3_QA_PACKET.json`.
- Recommended decision: `PASS`.

## Gate classification

The authority delta is wholly derived, non-semantic, replaceable and inside the approved plan. It is eligible for delegated auto-ratification after the final candidate tip reruns successfully.

## Rollback

Revert the bounded packet or rebuild fingerprints, distances and clusters from accepted candidates. No canonical market, evidence, selector, release or R2 object changes.

## Next packet

`PD-WP4 — simple Queue, Candidate Detail and Clusters UI plus governed evidence-bridge candidate`.
