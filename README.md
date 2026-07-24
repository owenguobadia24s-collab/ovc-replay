# OVC Replay

Deterministic GBP/USD market-structure research from sealed source data through
descriptive cohort validation.

This repository contains the canonical implementation, contracts, tests, and
compact release evidence for the completed OPT-A → OPT-D research pipeline.
It does **not** establish trading edge or authorize paper/live execution.

## Current authority

| Layer | Current version | Status |
| --- | --- | --- |
| OPT-A | `OPT-A.GBPUSD.2026H1.v1` and `OPT-A.GBPUSD.2025.v1` | Sealed research-data authority |
| OPT-B | `B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH` | Ratified descriptive state |
| OPT-C | `OPT-C-MEASURE-0.1.1` | Neutral forward-path measurement |
| OPT-D | `OPT-D-VALIDATE-0.1` + robustness review | Holdout validation complete |
| Paper gate | `PAPER-PLAYBOOK-GATE-0.1` | Closed: 0 pass, 0 defer, 202 block |

The 2025 holdout is now consumed evidence. The next valid research build is
`OPT-D-REFINE-0.2`; it must define new hypotheses before another untouched
validation period is selected.

## Repository map

```text
src/ovc_opt_b/        Deterministic A-D engine modules
src/ovc_evidence_store/ Deterministic release manifests and remote verification
scripts/              Build, replay, audit, validate, and gate entry points
tests/                Dependency-free unit and contract tests
contracts/            Ratified and historical semantic contracts
docs/architecture/    Full development summary and operating language
docs/history/         Compact release reports, manifests, registries, and history
docs/decisions/       Operator decisions and handover records
artifacts/             External artifact storage policy
data/                  External dependency declarations; no market records
```

## Run the tests

Python 3.11 or newer is required. The reference implementation has no runtime
dependencies outside the standard library.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The imported canonical tree currently passes 107 tests.

## Research pipeline

- OPT-A seals provider data, enforces UTC and complete-bucket rules, and forbids
  synthetic filling or cross-resolution fabrication.
- OPT-B creates deterministic levels and structural language, then resolves
  acceptance as frontier advances rather than a dominant persistent state.
- OPT-C measures neutral 1h, 2h, 4h, 8h, and 12h forward paths with explicit
  coverage and censoring; 24h is coverage-only and 48h remains blocked.
- OPT-D forms overlap-aware cohorts, balanced contrasts, story evidence,
  frozen hypotheses, untouched 2025 validation, and robustness reviews.
- The paper-playbook gate blocks all 202 candidates under the frozen rules.

See [Current status](docs/CURRENT_STATUS.md), [Development history](docs/history/README.md),
[import provenance](docs/IMPORT_PROVENANCE.md), and the
[complete development summary](docs/architecture/OVC_ABCD_COMPLETE_DEVELOPMENT_SUMMARY_2026-07-19.md).
For immutable evidence publication and Windows PowerShell commands, see the
[evidence-store guide](docs/EVIDENCE_STORE.md).

## Data and large artifacts

No raw or derived OHLCV dataset is stored in this repository. Provider files,
canonical bar tables, reconciliation tables, state/outcome streams, and replay
evidence remain external dependencies. Their names, hashes, roles, and saved
locations remain discoverable through [the dependency declarations](data/EXTERNAL_DEPENDENCIES.md),
[historical manifests](docs/history/README.md), and the
[external artifact policy](artifacts/README.md).

Committed historical artifacts are limited to documentation, contracts,
manifests, validation summaries, compact semantic registries, and decision
records.

## Safety boundary

All outputs are structural or descriptive research evidence. No file in this
repository grants outcome, risk, production, paper-execution, or live-execution
authority unless a later explicit ratification record says so.
