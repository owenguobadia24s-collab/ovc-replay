# GRT-G8 — Genesis Repository Topology read-only presentation gate

Programme: `OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1`  
Gate: `GRT-G8`  
Class: **OPERATOR REQUIRED**  
Status: **GATE_READY / STOP**  
Authority requested: acceptance of the read-only derived topology presentation and release of post-presentation `GRT-WP9` / `GRT-WP10` work only.

## 1. Court-record posture

- Original GRT-WP0 baseline: `1070df70e04bef9541e36461e76e97dfbca6ea20`.
- GRT-G0 reconciled lawful main before effect: `6c034e8924a9cd134f8d05e7743ba2a5e3771b82`.
- GRT-WP7 implementation head: `5b64cc3e73cf46840ece6fea02347c511d95bf0c`.
- GRT-WP8 presentation head: `dcd883e877f2852dd7abff0ed9acec6b9cc48319`.
- Latest main observed during GRT-WP8 final assurance: `81942e5b7f4ed3d4c34e8cf9296470b5bc19cc82`.
- Programme Genesis remains the sole programme/dependency authority.
- PGN-G3 `DEFER_ALL`, the sixteen reviewed native candidates, admission-enforcement deferral and Control Plane route deferral are preserved.
- Validation remains locked/unconsumed.

## 2. Exact accepted GRT-WP7 topology snapshot

The deterministic GRT-WP7 repository snapshot was built twice from the same source inputs and produced the same logical identity:

`6fca224dbebabbc3ee754e825f6028013011e5bc08b6f82a21e051cfdddc8138`

Snapshot counts:

| Surface | Count |
|---|---:|
| Programmes visible from source evidence | 39 |
| Repository components | 3,689 |
| Component topology edges | 9,219 |
| Source-referenced programme dependencies | 8 |
| Topology anomalies | 1,032 |
| INFO | 603 |
| WARNING | 429 |
| BLOCKER | 0 |

Programme implementation coverage:

| Coverage | Programmes |
|---|---:|
| COMPLETE | 6 |
| PARTIAL | 11 |
| NO_IMPLEMENTATION | 22 |

These are derived coverage states only. They do not adopt, reject or reclassify programmes.

## 3. Component population

| Component type | Count |
|---|---:|
| APP | 23 |
| CONTRACT | 186 |
| DECISION_RECORD | 306 |
| DOCUMENT | 576 |
| EVIDENCE_RECORD | 401 |
| FIXTURE | 120 |
| LEGACY_COMPONENT | 327 |
| MANIFEST | 46 |
| PROGRAMME_STATE | 20 |
| PYTHON_MODULE | 287 |
| PYTHON_PACKAGE | 23 |
| REGISTRY | 472 |
| SCHEMA | 271 |
| SCRIPT | 100 |
| TEST | 394 |
| TOOL | 10 |
| WORKFLOW | 127 |

## 4. Dependency and evidence population

Component edges by type:

- `DEPENDS_ON`: 550
- `EXECUTED_BY`: 66
- `GOVERNED_BY`: 1
- `OWNED_BY`: 2,667
- `REFERENCES`: 4,669
- `TESTED_BY`: 1,266

Evidence classes:

- `SOURCE_EXPLICIT`: 1,293
- `PATH_AND_CONTENT_CORROBORATED`: 6,110
- `TEST_CORROBORATED`: 1,266
- `IMPORT_CORROBORATED`: 550
- `INFERRED`: 0 in the accepted GRT-WP7 edge population

No `INFERRED_HARD_DEPENDENCY` blocker was produced. Import/path/test corroboration remains implementation evidence only and cannot satisfy a hard Genesis prerequisite.

## 5. Unresolved ownership and crosswalk population

The topology deliberately preserves unknown or competing ownership rather than guessing:

- `IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER`: 398
- `CONFLICTING_PROGRAMME_OWNERSHIP`: 37
- `DUPLICATE_COMPONENT_OWNERSHIP`: 46
- `IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK`: 22
- `PROGRAMME_WITHOUT_IMPLEMENTATION`: 22
- `MISSING_AUTHORITY_RECORD`: 2

These are review findings, not programme-state mutations.

## 6. Orphan and missing-support population

Orphan supporting components:

- `ORPHAN_CONTRACT`: 3
- `ORPHAN_SCHEMA`: 7
- `ORPHAN_REGISTRY`: 39
- `ORPHAN_FIXTURE`: 2
- `ORPHAN_TEST`: 37
- `ORPHAN_WORKFLOW`: 27

Missing support on programmes with implementation:

- `MISSING_CONTRACT`: 5
- `MISSING_SCHEMA`: 6
- `MISSING_FIXTURE`: 5
- `MISSING_TEST`: 4

Release/evidence lineage warnings:

- `RELEASE_WITHOUT_PROGRAMME_LINEAGE`: 29
- `MISSING_RELEASE_LINEAGE`: 29

## 7. Historical / supersession reachability

- `LEGACY_COMPONENT`: 327 tracked components.
- `SUPERSEDED_COMPONENT_STILL_REFERENCED`: 7 findings.
- `IMPLEMENTATION_STATE_MISMATCH`: 34 findings.
- `LEGACY_RUNTIME_IMPORT`: 0 blockers in the accepted snapshot.

Historical reachability is visible by design and is not automatically repaired.

## 8. State and authority warnings

- `STALE_PROGRAMME_STATE`: 1. This includes the previously identified disabled Control Plane adapter label that still says `PENDING_PG_G6` although accepted PG-G6 already decided route/enforcement `DEFER`; disabled booleans remain unchanged.
- `STALE_DOCUMENTATION`: 1.
- `SHADOW_ACTIVE_MISMATCH`: 6 advisory findings.
- `GENESIS_TOPOLOGY_CONFLICT`: 1 warning. It is preserved for source-level adjudication at repository-wide conformance audit; GRT does not suppress or resolve it automatically. The current implementation corpus includes GRT documents that intentionally name the conflict vocabulary, so a self-reference/classifier explanation remains possible but is **not** accepted as resolution here.
- `AUTHORITY_MISMATCH`: 0 in the accepted snapshot.

## 9. Performance and rebuild evidence

Two clean GRT-WP7 rebuilds:

- first rebuild: `12.571980s`;
- second rebuild: `12.432859s`;
- first peak traced memory: `56,054,317` bytes;
- second peak traced memory: `55,784,931` bytes;
- serialized read model: `10,459,681` bytes;
- tracked scan entries: `3,689`;
- logical identity match: **PASS**.

Logical identity excludes timestamps, hostname, absolute local path, worker/process identity and runtime diagnostics.

## 10. GRT-WP8 read-only operator surface

The existing Research Console System workspace is extended rather than creating a competing topology platform or new primary workspace.

The surface is local/read-only and fails closed if the topology file is absent, invalid, schema-mismatched or authority-bearing. It provides progressive-disclosure views for:

1. Portfolio;
2. Programme;
3. Component;
4. Dependency;
5. Authority;
6. Implementation-State;
7. Release/Evidence;
8. Anomaly / Health;
9. Historical / Supersession;
10. Commit-to-commit Diff.

The first nine consume only the derived topology read model. The tenth is an explicit `DEFERRED_PENDING_GRT_WP10` placeholder because the governing sequence places commit-to-commit diff implementation after this GRT-G8 operator gate. The UI does not pretend that diff authority or implementation already exists.

No UI interaction can write, edit, accept a programme, promote an edge, repair an anomaly, mutate Genesis state, register the Control Plane network route or activate admission enforcement.

## 11. Exact-head GRT-WP8 assurance

Presentation head `dcd883e877f2852dd7abff0ed9acec6b9cc48319`:

- repository tests run `31306436393`: **SUCCESS**, 777 tests;
- OVC tiered selection shadow run `31306436363`: **SUCCESS**;
- unresolved PR review threads: `0`;
- submitted PR reviews: `0`;
- read-only surface tests: missing model fails closed; authority-neutral model accepted; authority-bearing payload rejected.

## 12. Authority boundary at this gate

A GRT-G8 acceptance may release only `GRT-WP9` repository-wide conformance audit and `GRT-WP10` incremental/diff implementation under the existing derived/read-only authority envelope.

It does **not** grant:

- programme admission or automatic native adoption;
- programme reclassification;
- hard dependency adoption or edge promotion;
- Genesis or programme-state mutation;
- Control Plane network-route activation;
- admission enforcement;
- automatic remediation;
- selector, semantic, threshold, release or publication authority;
- Validation consumption;
- probability, risk, exposure, trading, execution or agent-write authority.

## 13. GRT-G8 disposition recommendation

Recommended: **PASS_WITH_WARNINGS**.

Rationale: deterministic rebuild and read-only presentation assurance pass with zero BLOCKER anomalies, while the large unresolved ownership/orphan/lineage population, one preserved conflict warning, stale-state evidence and intentionally deferred WP10 diff implementation should remain explicit rather than being cosmetically converted to a clean PASS.

Suggested operator command:

`OVC APPROVE GRT-G8 PASS_WITH_WARNINGS`

This command should be interpreted only as acceptance of the read-only presentation and authority to continue to the post-presentation GRT audit/diff packets. All warnings remain unresolved source-linked evidence.
