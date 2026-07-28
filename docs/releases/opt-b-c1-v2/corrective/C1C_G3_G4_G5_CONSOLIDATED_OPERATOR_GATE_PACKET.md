# C1C-G3 / C1C-G4 / C1C-G5 Consolidated Operator Gate Packet

## Decision requested

Approve or decline the remaining operator-reserved authority required to finish `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1` and resume `RO3-WP3_RETEST_AFTER_C1_CORRECTIVE_PROGRAMME`.

Allowed decisions for each gate: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

**Recommended decision:** `PASS` for C1C-G3, C1C-G4 and C1C-G5 as one ordered programme, subject to the sequencing and stop conditions below.

## Programme and baseline

- Programme: `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`
- Plan version: `0.1`
- Original RO3 plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.3-C1-FACT-ASSURANCE-IMPLEMENTATION-PLAN-0.2`
- Corrective baseline: `6c0aa91a6c51a86d39994ef363f8e29bb924764b`
- C1C-WP1 merge: `1142abd2010b92b33e56bccc23e05ccd8bed1320`
- C1C-WP2 tested head: `f30efb0ef8b72cb2e43ccb242c479932a6ee8387`
- Frozen formula registry: `C1.FORMULAS.v0.1`
- Corrective implementation: `C1.IMPLEMENTATION.v0.2`

## Completed packets

### C1C-WP1 / C1C-G1 — COMPLETED / PASS

- Centralized `upper_wick_share - lower_wick_share` under one implementation.
- Bound fixture, replay and prospective-compute paths to the same helper.
- Added exact corpus audit tooling and authority guards.
- Focused tests, canonical suite and frozen-authority checks passed.
- Squash-merged into main at `1142abd2010b92b33e56bccc23e05ccd8bed1320`.

### C1C-WP2 / C1C-G2 — PASS, local-only

- Downloaded exact approved OPT-A, active C1 and active-parent C2 artifacts.
- Audited all 212,764 active C1 records in 192 shards.
- Ran two complete corrected Discovery and Development replays.
- Proved every corrected record shard byte-identical to active v1.
- Froze new local-only v2 candidate identities.
- Re-ran independent RO3 formula assurance with the invariant canon unchanged.
- Bound exact C2 identity and Pilot Discovery remediation surfaces.

## Material finding

The active C1 releases were not byte-defective. The defect existed only in the reusable C1 library path.

- Active C1 records affected: **0**
- Active C1 files affected: **0**
- Nonzero records that would diverge under the defective helper: **208,185**
- Zero-balance records: **4,576**
- Null zero-range records: **3**

The v2 candidates therefore preserve all active C1 record bytes and introduce only a corrected implementation identity plus new immutable release descriptors and manifests.

## Candidate identities

### Discovery

- Release: `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2`
- Manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1`
- Manifest SHA-256: `c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf`
- Records: 159,892
- Record shards: 144
- Workflow artifact: `8692836156`
- Artifact digest: `sha256:9cec2ff4391576334149cb4a3542131b2692530829d9794c4038354a4a299bf7`

### Development

- Release: `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2`
- Manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1`
- Manifest SHA-256: `e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f`
- Records: 52,872
- Record shards: 48
- Workflow artifact: `8692837001`
- Artifact digest: `sha256:fa5e02c23a834b0d6c1c9496635b6a5fcda8fbf3b9354fe3cc8ab363ea6937d1`

## QA and assurance

Workflow `30370847916`, job `90313984452`: PASS.

- Exact parent artifact resolution: PASS
- Full-corpus active impact audit: PASS
- Two complete replay byte comparison: PASS
- Candidate versus active-v1 record-shard comparison: PASS
- Candidate cardinality and manifest construction: PASS
- Frozen invariant registry: unchanged from RO3-G0
- Metamorphic assertions: 79 / 79 PASS
- Independent golden assertions: 18 / 18 PASS
- Deterministic rerun: PASS
- Canonical input reorder: PASS
- Corrupted-engine negative control: detected
- Failed assurance assertions: 0
- Canonical repository suite: PASS
- Validation: `LOCKED_UNCONSUMED`

Evidence artifact `8692834967`, digest `sha256:961e816e18b64cfe48a643dedf7a3f3ad64deecb53ffbe3e10a33dfe3ac0dc30`.

## Current authority

- C1 Discovery selector: ACTIVE on `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1`
- C1 Development selector: ACTIVE on `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1`
- C1 Validation selector: NONE / `LOCKED_UNCONSUMED`
- C2 Discovery selector: ACTIVE_DISCOVERY on `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`
- C2 Development: remote-verified reference only
- Pattern Discovery canonical append: none affected
- Probability, risk, exposure, trading and execution authority: NONE

## Gate C1C-G3 — R2 publication

### Proposed authority delta

Publish the exact C1 v2 Discovery and Development candidates under their new immutable identities and perform full remote-byte verification. Publication does not activate a selector.

### Acceptance conditions

- Candidate workflow artifact digests and manifest hashes match this packet.
- Exact canonical keys pass collision preflight.
- Payload objects upload before manifest objects.
- Existing v1 objects are untouched.
- Full remote size and SHA-256 verification passes for every object.
- Git publication receipts bind source commit, candidate artifact, manifest hash and remote verification run.

### Rollback

Before manifest publication, leave any partial payload non-authoritative and quarantine it by receipt; do not delete or overwrite. After manifest publication, preserve immutable bytes and leave selectors on v1 until C1C-G4.

### Recommendation

`PASS`.

## Gate C1C-G4 — C1 selector replacement

### Proposed authority delta

Replace active Discovery and Development C1 selectors from v1 to the remotely verified v2 identities. Validation remains NONE and locked.

### Acceptance conditions

- C1C-G3 remote verification is PASS.
- Selector transaction is atomic and pins exact v2 manifest hashes.
- Existing v1 releases remain immutable and become rollback targets.
- No C2 selector points to lineage inconsistent with the active C1 selector set at transaction completion.
- No formula, threshold, schema or semantic change is introduced.

### Rollback

Atomically return both C1 role selectors to the exact v1 release and manifest hashes. Never rewrite or delete v2.

### Recommendation

`PASS`, executed only as part of the coordinated C1/C2 transaction authorised by C1C-G5.

## Gate C1C-G5 — Downstream remediation

### Proposed authority delta

Permit deterministic downstream identity remediation only:

1. Replay C2 Discovery and Development against exact C1 v2 parents under new immutable C2 v2 identities.
2. Require semantic and state-value equivalence with current C2 v1; any semantic divergence blocks.
3. Publish and remotely verify C2 v2 under new immutable identities.
4. Atomically replace the C1 selector set and C2 Discovery selector so lineage is never left inconsistent.
5. Keep C2 Development as remote-verified reference only unless separately approved.
6. Supersede, never delete, the noncanonical Pilot Discovery namespace `PD.PILOT.GBPUSD.20260622_20260625.v1`.
7. Rerun prospective C1/C2 computation and the pilot review workflow from the exact source binding after corrected selectors are active.
8. Preserve all current selector, release, R2, Validation, novelty, semantic, probability and exposure prohibitions except the exact identity replacements named here.

### Exact affected surface

- C2 state records requiring identity replay if C1 v2 is selected: 404,434
- C2 transition records requiring identity replay: 323,910
- Total identity-bearing records: 728,344
- Total state/transition files: 24
- C2 semantic correction caused by active C1 bytes: NONE
- Canonical Pattern Discovery affected: NO
- Noncanonical pilot namespace affected: entire namespace
- Pilot run: `PD.PILOT.RUN.0cc5a59ca751583f3e50091c`
- Source compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`

### Acceptance conditions

- C2 output values and transition semantics are identical to current v1 after excluding identity and parent-release fields.
- New C2 identities and manifests bind exact C1 v2 parents.
- Full C2 QA and remote verification pass.
- Atomic selector transaction preserves a valid C1-to-C2 lineage at completion.
- Pilot supersession is append-only and preserves all prior evidence.
- Pilot rerun remains `PILOT_ONLY`, `TIME_GATED_REPLAY` and `NON_PROMOTABLE` unless a separate operator gate changes that authority.
- No C2 threshold, state rule, family, novelty, semantic, theory or candidate promotion occurs.

### Rollback

Return C1 and C2 selectors atomically to the exact v1 selector set; retain all v2 bytes as inactive immutable releases. Keep the old pilot superseded and rerun only from an approved exact binding. Never reactivate legacy B-state authority.

### Recommendation

`PASS`.

## Warnings and unresolved operational prerequisites

- R2 publication requires the operator-authorised environment-only remote configuration; credentials must not enter Git.
- A remote key collision, hash mismatch or non-reproducible artifact blocks the relevant gate.
- The C1 v2 record shards are byte-identical to v1. The reason for publication is implementation and lineage identity, not a market-fact correction.
- C2 v2 must be a pure identity-parent replay. Any state or transition value drift is a blocker, not a tuning opportunity.
- The Pilot Discovery rerun cannot become canonical or promotable under this approval.

## Exact work after approval

1. Materialise C1C-G3 publication approval records pinned to the v2 artifact digests and manifest hashes.
2. Run collision preflight, immutable upload and full remote verification for C1 v2.
3. Build C2 v2 from the remotely verified C1 v2 parents and prove semantic equivalence.
4. Prepare C2 v2 publication and coordinated selector transaction receipts.
5. Publish and remotely verify C2 v2.
6. Atomically replace C1 and C2 selectors; verify rollback targets and repository authority guards.
7. Supersede the old Pilot Discovery namespace and rerun exact prospective computation plus pilot workflow.
8. Re-run RO3-G3 from current main; if PASS, complete RO3-WP3 and continue to RO3-WP4 under the original plan.

## Requested operator response

`OVC APPROVE C1C-G3 C1C-G4 C1C-G5`

A narrower decision may name each gate separately with `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.
