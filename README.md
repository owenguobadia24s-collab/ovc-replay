# OVC Replay

OVC Replay is an evidence-first, human-governed market-translation research system. Repository state is the court record; historical releases and decisions remain preserved even when their current runtime authority is superseded.

## Current authority

The governing current-stack pointer is:

`registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json`

The active structural evidence spine is:

```text
OPT-A -> OPT-B.C1 v2 -> OPT-B.C2 vNext core -> OPT-B.C2E v0.2
```

| Component | Current classification | Scope |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE` | Evidence infrastructure; no market authority |
| OPT-A v2 | `ACTIVE` | Existing governed GBPUSD Discovery/Development source; Validation locked |
| OPT-B.C1 v2 | `ACTIVE` | Discovery + Development atomic facts |
| pre-redesign OPT-B.C2 v2 | `LEGACY_INACTIVE` | Historical lineage/exact replay only; denied as new-evidence parent |
| OPT-B.C2 vNext core | `ACTIVE` | Exact frozen nine-component structural-description core |
| OPT-B.C2E v0.2 | `ACTIVE` | Current operator-selected boundary pack over governed active-C2-vNext inputs inside the market envelope |
| OccurrenceContext v0.1 | `ACTIVE_FOUNDATION` | Non-structural enrichment; representation input denied by default |
| Research Operations | `ACTIVE_FOUNDATION` | Existing read-only and bounded append-only research evidence authority |
| SRI/SFC, FDI/C2G, SRFD, MCARB, experimental Market Grammar | `SHADOW` | Deterministic research evidence only; no canonical scientific promotion |
| C2P v0.2, revised C2.5, revised C3, new OPT-C, new OPT-D | `NON_EVALUABLE` | Forward implementation/evidence surface not yet operational |
| Validation 2025 for the current stack | `LOCKED` | `LOCKED_UNCONSUMED` |

C2 vNext activation covers only Observation, Horizon, Level, Container, Relation, Formula, Transition, Parent Context and Computability. Functional Discovery and Candidate Dispositions remain shadow research.

C2E is no longer activated by one exact June population/run/date identity. It remains bound to the current operator-selected boundary pack and to the existing market envelope: GBPUSD, BID/ASK, `15M` and `2H_A_L`, Discovery/Development. Pack replacement, semantic/threshold changes, new instrument/side/clock, Validation access and provider intake requiring approval remain operator-reserved.

No probability, risk, exposure, trading, execution or agent-write authority is granted. No new canonical/R2 publication or immutable release identity is implied by active-stack classification.

## Historical authority records

Earlier records such as `registries/authority/ACTIVE_AUTHORITY.yaml`, the old C2 selector transaction and the C2E AG3 terminal state are preserved as historical court-record snapshots. They are not deleted or rewritten to erase prior authority. Where they conflict with current classification, the current-stack pointer and its explicit supersession overlays govern new evidence.

The historical ABCD implementation is retained under `legacy/quarantine/abcd-engine-v1-c0ad7ba/` and is not eligible as a current runtime import, release parent, selector fallback or discovery seed.

## Repository boundaries

- Git stores code, contracts, schemas, registries, compact manifests, fixtures, tests, QA and decisions.
- Full market data, generated streams and large external evidence remain outside Git.
- Immutable canonical evidence is published only through separately governed publication authority.
- Missing market records are not manufactured or silently bridged.
- Shadow outputs do not become active/canonical truth without the required operator decision.

## Development

Python 3.11 or newer is required. Pytest is the target unified Python test runner and all existing `unittest.TestCase` tests remain supported through pytest's unittest compatibility layer.

```powershell
python -m pip install -e ".[test]"
python -m pytest -v
```

During the bounded runner-parity migration, CI also preserves and executes the previous standalone command and checks that pytest collects every legacy unittest case:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m unittest discover -s tests -v
python tools/ci/check_pytest_unittest_parity.py
```

The standalone unittest CI command may be removed only after a merged-main parity PASS is materialised under `registries/implementation/python_test_runner/`; the unittest tests themselves are not removed by that cutover.

Historical v1 repository state is pinned at `archive/ovc-replay-v1-c0ad7ba-20260725` and commit `c0ad7ba22618babdde731e2a338f68f688d4210c`.
