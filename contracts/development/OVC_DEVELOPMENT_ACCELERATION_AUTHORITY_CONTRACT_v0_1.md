# OVC Development Acceleration Authority Contract v0.1

## Identity

- **contract_id:** `OVC-DEVELOPMENT-ACCELERATION-AUTHORITY-CONTRACT.v0.1`
- **programme_id:** `OVC-DEV-ACCEL-v0.1`
- **governing_plan:** `OVC-DEV-ACCEL-IMPLEMENTATION-PLAN-0.1`
- **operator_decision:** `DA-G0.OPERATOR.PASS.20260801T151200Z`
- **baseline_main:** `b9e763150858d02cc92d08efbcf2f6668b187a41`
- **status:** `RATIFIED_FOR_BOUNDED_IMPLEMENTATION`

## Purpose

Create shared development mechanics without importing or changing market semantics. Programme profiles own policy. Shared services may implement deterministic identity, canonical serialization, hashing, path safety, QA assertions, gate packets, decisions, rollback, preflight, test selection, closure records and compact evidence export.

## Permitted authority

| Class | Permitted effect |
|---|---|
| `READ_ONLY` | Inspect repository metadata, approved compact external metadata, manifests, CI, pull requests and court records. |
| `LOCAL_COMPUTE` | Build profiles, receipts, indexes, QA packets, test manifests, closure packets and export bundles without external or canonical writes. |
| `PROPOSAL_WRITE` | Create bounded packet branches, repository records and pull requests inside approved paths. |
| `MERGE_AUTOMATION` | Squash-merge only eligible auto-ratifiable pull requests under the governing continuous-execution rules. |

`REPOSITORY_BOT_WRITE` remains **DENIED** until a separate operator PASS at `DA-G4`. It may never imply direct writes to `main`.

## Bounded repository paths

The programme may create or modify only the following development-tooling paths unless a later approved packet explicitly narrows or extends them:

- `contracts/development/**`
- `schemas/development/**`
- `registries/development/**`
- `src/ovc/development/**`
- `scripts/development/**`
- `scripts/ovc.py`
- `scripts/ovc.ps1`
- `tests/development/**`
- `fixtures/development/**`
- `docs/development-acceleration/**`
- `docs/releases/development-acceleration-v0-1/**`
- `.github/workflows/ovc-*.yml`
- `.github/workflows/development-acceleration-*.yml`

Changes outside this allowlist require an explicit packet-level dependency justification and fail closed if ambiguous.

## Permanent denials

This contract grants no authority to:

- modify formulas, thresholds, labels, candidate selection or research semantics;
- perform provider intake or market replay content changes;
- publish releases, mutate selectors, write R2 or consume Validation;
- create probability, risk, exposure, trading or execution objects;
- delete accepted artifacts, quarantines or incidents;
- commit raw BI5, OHLC CSV, full C1/C2 JSONL, caches, credentials or private absolute paths;
- force-push, rewrite history, write directly to `main`, or silently mutate another packet branch;
- let a bot or agent self-approve, broaden its allowlist or activate deferred capability.

## Dependency direction

`programme profile -> development services -> generated compact court records`

The shared package must not import `ovc.opt_a`, `ovc.opt_b`, Pattern Discovery or Research Operations semantic implementations. Programme adapters may read compact profile-defined records and translate them into shared mechanical types. Reverse dependency from market packages into development tooling is prohibited unless a separate migration gate approves a narrow adapter.

## Fail-closed rules

Execution blocks when a profile is missing or ambiguous, an identity role cannot be reproduced, a path is unsafe, changed-file impact is unknown, required final-head or gate-replay evidence is absent, a destination collides, or an authority delta exceeds tooling administration.

Unknown test impact escalates to the broader profile; it is never skipped.

## Rollback

Revert only the bounded packet merge through a new non-destructive commit or disable the new capability in its profile. Preserve all prior court records, incidents, quarantines and accepted external artifacts. Bot capability, when later approved, must have an independent revocation path.
