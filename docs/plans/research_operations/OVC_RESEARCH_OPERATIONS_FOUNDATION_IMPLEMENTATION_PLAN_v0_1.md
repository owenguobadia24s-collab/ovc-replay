# OVC Research Operations Foundation v0.1 — Implementation Control Record

## Status

`RATIFIED_FOR_RO_G0_AND_RO_WP1`

## Source document

- Source filename: `OVC_Research_Operations_Foundation_v0_1_Implementation_Plan.docx`
- SHA-256: `4f0de710ab0157041f57ab781c9411a68aaf211b3b4a41f249978f07b0d580a0`
- Size: `193991` bytes
- Recorded approval: operator instruction to execute `RO-G0 — Foundation preflight`
- Ratification date: `2026-07-26`

This Markdown record is the repository control copy for the implementation programme. The source DOCX remains bound by the exact SHA-256 above. Any replacement document requires a new version and a new decision record.

## Executive decision

Build Research Operations as a permanent operating and evidence layer inside `ovc-replay`, not as another Option and not as a second repository.

The programme order is fixed:

1. `RO-WP1 — Evidence envelope and record schemas`
2. `RO-WP2 — Research CLI and artifact catalogue`
3. `RO-WP3 — QA runner, read model and console integration`

Evidence identity, admissible cutoff, freeze, missingness and lineage precede operator tooling. Governed services precede the console. Read surfaces precede write surfaces.

## Programme authority

RO-G0 permits repository design and bounded RO-WP1 implementation only.

It does not authorise:

- provider access, aggregation or market-release construction;
- mutation of OPT-A or OPT-B records;
- R2 publication or selector changes;
- validation-payload access;
- C1, C2, C2E, C2.5 or C3 classification changes;
- probability, setup, exposure, risk or execution objects;
- agent tools or autonomous mutation;
- direct writes to `main`.

## Exact execution baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Branch: `main`
- Commit: `3940f64a635f547a6bef6045bd3a8a27e386dcdd`
- Upstream state: OPT-A v2 A2-G5 selector set active; Validation `LOCKED_UNCONSUMED`
- Parallel model state: OPT-B.C1 v2 WP1 passed; WP2 design work authorised
- Historical engine: quarantined and prohibited as active authority

The source plan's provisional baseline clause is resolved by this RO-G0 record. The exact commit above is the sole baseline for RO-WP1.

## Canonical namespace

Research Operations implementation is reserved beneath the existing `ovc` package:

```text
src/ovc/research_operations/
```

Logical services such as records, CLI, catalogue, QA and read model are subpackages of `ovc.research_operations`; they are not new top-level Python packages.

Reserved repository roots:

```text
contracts/research_operations/
schemas/research_operations/
registries/research_operations/
fixtures/research_operations/
tests/research_operations/
docs/research-operations/
docs/releases/research-operations-foundation/
records/research_operations/
apps/research_console/
var/research_operations/
```

`var/research_operations/` is derived, disposable and Git-ignored. Durable compact records remain under governed record paths or checksum-addressed external storage.

## Dependency direction

```text
approved OPT-A metadata and sealed releases
    -> optional approved C1/C2 references
    -> Research Operations evidence records
    -> QA assertions and gate packets
    -> deterministic read model
    -> local console
```

Research Operations may reference and evaluate upstream objects. It may not rewrite them. Validation identity and metadata may be catalogued, but the locked payload cannot be resolved.

## Gates

| Gate | Pass condition | Authority delta |
|---|---|---|
| RO-G0 | Baseline, plan, namespace, dependency and path boundaries frozen | Permits RO-WP1 |
| RO-G1 | Valid record chain reconstructs; leakage, mutation and hash violations reject | Permits RO-WP2 |
| RO-G2 | CLI and catalogue support repeatable append-only operation | Permits RO-WP3 |
| RO-G3 | Deterministic read model and governed local console pass | Creates `ACTIVE_RESEARCH` authority only |

## Workstream branches

- RO-WP1: `build/research-operations-evidence-kernel`
- RO-WP2: `build/research-operations-cli-catalogue`
- RO-WP3: `build/research-operations-read-model-console`

Each workstream begins only from the merged predecessor gate and ends in a reviewable pull request. Main is never force-pushed.
