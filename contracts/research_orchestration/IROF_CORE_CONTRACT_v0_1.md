# OVC IROF Core Contract v0.1

Status: inactive infrastructure contract under approved `OVC-IROF-v0.1` engineering authority.

## 1. Constitutional role

IROF is a cross-cutting orchestration and evidence framework. It knows **how** a declared stage is planned, authorised, executed, resumed, reused and evidenced. It does not decide what a stage's market output means and does not grant scientific or market authority.

A research run is constituted by `PopulationSpec + PipelineProfile + versioned packs/configuration + existing AuthorityBinding -> ResearchRunSpec -> IntegratedRunManifest -> typed stage execution -> receipts/artifacts/QA/evidence`.

## 2. Identity separation

IROF maintains three distinct concepts:

1. semantic run identity;
2. physical execution attempt identity;
3. physical artifact location.

Semantic identity MUST NOT depend on hostname, absolute filesystem path, physical artifact relocation, worker count, scheduling order or restart count unless an owning frozen stage contract explicitly declares one of those facts semantic. IROF v0.1 declares none of them semantic by default.

Semantic identity MUST bind all relevant meaning-bearing inputs, including population identity, profile identity, participating stage identities, declared packs/configuration, chronology/comparability/context-role identities and code identity where required by an owning reproducibility contract.

## 3. PopulationSpec

Permitted v0.1 population modes are:

- `SYNTHETIC_FIXTURE`
- `SYNTHETIC_GENERATED`
- `SEALED_REAL_REPLAY`
- `TIME_GATED_REPLAY`
- `LIVE_PROSPECTIVE`

`LIVE_PROSPECTIVE` is vocabulary only and carries no executable authority. Real replay modes require exact source-release and source-manifest identities. Synthetic fixture/generated modes require their fixture/generator identity. Downstream orchestration semantics are shared across provenance modes.

Capacity tiers `MICRO`, `SMALL`, `MEDIUM`, `LARGE`, `LONG_HORIZON` are execution-governance labels, never scientific quality ranks.

## 4. PipelineProfile

A PipelineProfile is a versioned, hashable subgraph declaration. Profiles may include or omit stages but MUST NOT redefine a stage's semantics. Duplicate profile IDs fail closed. Profile stage IDs must resolve to registered StageSpecs before a run can be constituted.

## 5. StageSpec and dependencies

Every StageSpec binds its stage/version/kind, implementation/contract/schema identities, typed inputs/outputs, dependencies, authority requirements, pack requirements, deterministic mode, backend, checkpoint/cache capabilities, resource-estimator identity, artifact policy, QA requirements and adapter identity.

Dependencies are one of `REQUIRED`, `OPTIONAL`, `FORBIDDEN`. Duplicate dependency stage IDs fail closed.

`wrapper_mutation_policy` is fixed to `NO_SCIENTIFIC_MUTATION` for v0.1. A wrapper may translate a declared transport envelope only under an explicit crosswalk; it may not repair, impute, reinterpret, select a winner, alter denominators, manufacture fields or change chronology.

## 6. AuthorityBinding

AuthorityBinding is an immutable reference to authority granted or denied by an owning programme/gate. IROF may record an interpreted decision of `ALLOW`, `NOT_AUTHORISED` or `DEFERRED_BY_OPERATOR`; creating the object itself has no authority effect.

A consumed, superseded, expired or invalidated token cannot be renewed by cache/restart mechanics. Partial authority from different owner programmes may not be composed into a broader grant.

## 7. Run identity and manifests

ResearchRunSpec's semantic run identity includes population/profile/stage semantic identities, declared authority-binding IDs and meaning-bearing pack/policy bindings. It excludes workers, scheduling policy and physical output root.

IntegratedRunManifest deterministically binds the exact StageInvocations and authority bindings for one semantic run.

## 8. Artifacts and cache identity

IROF artifact lifecycle states are `STAGING`, `COMPLETE`, `QUARANTINED`, `SUPERSEDED`. Physical locations are not semantic identity. Artifact availability in Research Operations remains a distinct axis.

SemanticCacheKey binds exact stage/version, parent semantic hashes, contract/schema/implementation identities, pack bindings and all declared population/chronology/comparability/context/code identities. Cache admission/reuse policy is implemented in later packets; the WP1 key object cannot by itself authorise reuse.

## 9. Execution receipts and scientific results

Execution states are exactly:

`READY`, `RUNNING`, `REUSED`, `COMPLETE`, `CAPACITY_EXCEEDED`, `FAILED`, `QUARANTINED`, `DEFERRED_BY_OPERATOR`, `NOT_AUTHORISED`.

Scientific/domain statuses such as `NOT_EVALUABLE`, `NOT_COMPARABLE`, `AMBIGUOUS`, `RESIDUAL`, `NO_STABLE_FAMILY` are **not** execution states and MUST NOT be normalised into them. Successful computation does not imply scientific PASS; a lawful scientific null does not imply execution failure.

CapacityReceipt must preserve `scientific_effect=NONE`.

## 10. Failure taxonomy

RunFailure has an orthogonal failure class: `EXECUTION`, `AUTHORITY`, or `DEPENDENCY`. It may identify blocked descendants, reusable ancestors and owning programme/gate. Domain/scientific nulls are excluded from this failure taxonomy.

## 11. Authority firewall

Nothing in this contract grants provider intake, selector mutation, ACTIVE_DISCOVERY/ACTIVE_DEVELOPMENT/ACTIVE_VALIDATION, Validation consumption, representation/normalization/distance/family/semantic promotion, C2E/C2P/C2.5/C3 activation, canonical/R2 publication, probability, risk, exposure, trading, execution or agent-write authority.

## 12. Storage boundary

Compact contracts, schemas, registries, manifests, hashes, receipts, fixtures, QA, programme state and decisions belong in Git. Large state streams, representation populations, pair/distance surfaces, caches, family payloads and raw telemetry remain under governed external artifact roots. Physical location never defines scientific identity.

## 13. Compatibility doctrine

WP1 contracts are inactive infrastructure. Later packets must generalise SRFD/SFC primitives with equivalence tests and use Research Operations directly where existing contracts fit. Frozen stage semantics remain owned by their original programme.
