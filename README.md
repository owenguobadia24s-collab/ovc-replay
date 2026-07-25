# OVC Replay

OVC Replay is being reset into an evidence-first v2 research foundation.

The active repository now contains only:

- immutable repository history and historical release records;
- the tested `ovc_evidence_store` infrastructure;
- clean namespaces for OPT-A v2, OPT-B.C1 v2 and OPT-B.C2 v2;
- repository authority and implementation registries;
- synthetic-fixture and contract locations that will be populated in later bounded work packets.

## Current authority

| Component | State | Active market authority |
|---|---|---:|
| Evidence store | `ACTIVE_INFRASTRUCTURE` | No |
| OPT-A v1 | `HISTORICAL_SUPERSEDED` | No |
| OPT-A v2 | `DESIGN_AND_FIXTURES_ONLY` | No |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | No |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | No |
| C2E, C2.5 and C3 | `DEFERRED` | No |
| OPT-C and OPT-D | `HISTORICAL_QUARANTINED` | No |

No selector is active. No provider intake, market replay, probability, exposure or execution authority is granted by this foundation.

## Repository boundaries

- Git stores code, contracts, schemas, registries, compact manifests, fixtures, tests and decisions.
- Full market data, generated streams and large evidence remain outside Git.
- Immutable canonical evidence is published only through the separately governed R2 evidence-store workflow.
- The historical ABCD implementation is retained under `legacy/quarantine/abcd-engine-v1-c0ad7ba/` and is prohibited as a runtime import, release parent, selector fallback, rollback target, parameter source or discovery seed.

## Active package layout

```text
src/
├── ovc/
│   ├── opt_a/
│   └── opt_b/
│       ├── c1/
│       └── c2/
└── ovc_evidence_store/
```

The `ovc` namespaces are foundation-only. Their contracts, fixtures and engines are built through the ratified OPT-A, C1 and C2 implementation plans after completion of R0.

## Development

Python 3.11 or newer is required.

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m unittest discover -s tests -v
```

Historical v1 repository state is pinned at `archive/ovc-replay-v1-c0ad7ba-20260725` and commit `c0ad7ba22618babdde731e2a338f68f688d4210c`.
