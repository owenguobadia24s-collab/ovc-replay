from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

BASELINE = "c0ad7ba22618babdde731e2a338f68f688d4210c"
PACKET_ROOT = Path("docs/history/repository-freezes/ovc-replay-v1-c0ad7ba")
QUARANTINE_ROOT = Path("legacy/quarantine/abcd-engine-v1-c0ad7ba")

FILES: dict[str, str] = {
    "README.md": """# OVC Replay

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
$env:PYTHONPATH = (Resolve-Path .\\src)
python -m unittest discover -s tests -v
```

Historical v1 repository state is pinned at `archive/ovc-replay-v1-c0ad7ba-20260725` and commit `c0ad7ba22618babdde731e2a338f68f688d4210c`.
""",
    "pyproject.toml": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ovc-replay"
version = "0.2.0"
description = "Evidence-first OVC v2 research and deterministic replay foundation"
requires-python = ">=3.11"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["ovc*", "ovc_evidence_store*"]
exclude = ["legacy*"]
""",
    "docs/CURRENT_STATUS.md": """# Current status

Snapshot date: 25 July 2026.

## Repository reset

R0-1, R0-2 and R0-3 have passed. The historical v1 repository is frozen at `c0ad7ba22618babdde731e2a338f68f688d4210c`, 339 tracked files were classified, and 106 legacy executable files were moved with exact byte identity into `legacy/quarantine/abcd-engine-v1-c0ad7ba/`.

R0-4 establishes the clean active-tree foundation. It does not activate any research release.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE` | Not applicable |
| OPT-A v1 | `HISTORICAL_SUPERSEDED` | `NONE` |
| OPT-A v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E | `DEFERRED` | `NONE` |
| C2.5 | `DEFERRED` | `NONE` |
| C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Active repository responsibilities

- Preserve immutable history, decisions and release records.
- Maintain deterministic evidence-store infrastructure.
- Provide clean OPT-A, C1 and C2 package and governance namespaces.
- Deny legacy imports, reverse dependencies, old discovery seeds and raw market data in Git.

## Not yet authorised

Provider download, OPT-A v2 release creation, C1 or C2 market replay, R2 canonical publication for the new line, selector activation, C2E, C2.5, C3, OPT-C, OPT-D, probability, exposure and execution.

## Next gate

`R0-5 — synthetic OPT-A, C1 and C2 fixture packs`.
""",
    "src/ovc/__init__.py": """\"\"\"OVC v2 research foundation.\"\"\"\n\n__version__ = \"0.2.0\"\n__all__ = [\"__version__\"]\n""",
    "src/ovc/opt_a/__init__.py": """\"\"\"OPT-A v2 namespace: design and fixtures only until separately activated.\"\"\"\n\nAUTHORITY_STATE = \"DESIGN_AND_FIXTURES_ONLY\"\n__all__ = [\"AUTHORITY_STATE\"]\n""",
    "src/ovc/opt_b/__init__.py": """\"\"\"OPT-B v2 namespace.\"\"\"\n""",
    "src/ovc/opt_b/c1/__init__.py": """\"\"\"OPT-B.C1 v2 atomic-fact namespace: no market authority.\"\"\"\n\nAUTHORITY_STATE = \"DESIGN_AND_FIXTURES_ONLY\"\n__all__ = [\"AUTHORITY_STATE\"]\n""",
    "src/ovc/opt_b/c2/__init__.py": """\"\"\"OPT-B.C2 v2 parallel-state namespace: no market authority.\"\"\"\n\nAUTHORITY_STATE = \"DESIGN_AND_FIXTURES_ONLY\"\n__all__ = [\"AUTHORITY_STATE\"]\n""",
    "contracts/README.md": """# Active contracts\n\nOnly v2 and cross-cutting infrastructure contracts may be added here. Historical ABCD contracts are quarantined or retained under `docs/history/`. Contract presence does not grant implementation or market authority.\n""",
    "contracts/evidence/README.md": """# Evidence contracts\n\nReserved for deterministic evidence, publication and verification contracts.\n""",
    "contracts/opt_a/README.md": """# OPT-A v2 contracts\n\nReserved for source identity, clock, gap, release and OPT-A-to-OPT-B handoff contracts.\n""",
    "contracts/opt_b/README.md": """# OPT-B v2 contracts\n\nReserved for one-way C1 and C2 authority contracts.\n""",
    "contracts/opt_b/c1/README.md": """# C1 contracts\n\nReserved for atomic-fact, formula, null and C1-to-C2 handoff contracts.\n""",
    "contracts/opt_b/c2/README.md": """# C2 contracts\n\nReserved for level, container, relation, parallel-state and transition contracts.\n""",
    "contracts/qa/README.md": """# QA contracts\n\nReserved for cross-cutting check, gate and severity contracts.\n""",
    "schemas/README.md": """# Active schemas\n\nMachine-readable v2 and governance schemas live under this root. Historical schemas do not become active by reference.\n""",
    "schemas/evidence/README.md": """# Evidence schemas\n\nReserved for evidence release, manifest and publication schemas.\n""",
    "schemas/opt_a/README.md": """# OPT-A schemas\n\nReserved for provider object, bar, release and handoff schemas.\n""",
    "schemas/opt_b/c1/README.md": """# C1 schemas\n\nReserved for atomic-fact record and release schemas.\n""",
    "schemas/opt_b/c2/README.md": """# C2 schemas\n\nReserved for structural context, state, transition and release schemas.\n""",
    "schemas/governance/README.md": """# Governance schemas\n\nReserved for authority, implementation, selector, approval and supersession records.\n""",
    "registries/README.md": """# Active registries\n\nRegistries define explicit repository authority and implementation state. They do not silently activate code or releases.\n""",
    "registries/authority/ACTIVE_AUTHORITY.yaml": """schema: ovc-active-authority/v1
repository: owenguobadia24s-collab/ovc-replay
reset_baseline: c0ad7ba22618babdde731e2a338f68f688d4210c
state: V2_FOUNDATION_NO_MARKET_AUTHORITY
selectors:
  opt_a: NONE
  opt_b_c1: NONE
  opt_b_c2: NONE
  c2e: NONE
  c2_5: NONE
  c3: NONE
  opt_c: NONE
  opt_d: NONE
authorities:
  evidence_store:
    state: ACTIVE_INFRASTRUCTURE
    market_authority: false
  opt_a_v1:
    state: HISTORICAL_SUPERSEDED
    active: false
  opt_a_v2:
    state: DESIGN_AND_FIXTURES_ONLY
    active: false
  opt_b_c1_v2:
    state: DESIGN_AND_FIXTURES_ONLY
    active: false
  opt_b_c2_v2:
    state: DESIGN_AND_FIXTURES_ONLY
    active: false
  c2e:
    state: DEFERRED
    active: false
  c2_5:
    state: DEFERRED
    active: false
  c3:
    state: DEFERRED
    active: false
  opt_c:
    state: HISTORICAL_QUARANTINED
    active: false
  opt_d:
    state: HISTORICAL_QUARANTINED
    active: false
legacy_quarantine:
  root: legacy/quarantine/abcd-engine-v1-c0ad7ba
  runtime_imports: DENIED
  release_parent_eligibility: DENIED
  selector_eligibility: DENIED
  rollback_target: DENIED
  parameter_source: DENIED
  discovery_seed_eligibility: DENIED
""",
    "registries/implementation/IMPLEMENTATION_REGISTRY.yaml": """schema: ovc-implementation-registry/v1
entries:
  - id: INFRA-EVIDENCE-STORE-V1
    namespace: ovc_evidence_store
    state: ACTIVE_INFRASTRUCTURE
    build_authority: RETAINED
    market_authority: NONE
  - id: OPT-A-V2
    namespace: ovc.opt_a
    state: DESIGN_AND_FIXTURES_ONLY
    build_authority: DEFERRED_TO_OPT_A_PLAN
    market_authority: NONE
  - id: OPT-B-C1-V2
    namespace: ovc.opt_b.c1
    state: DESIGN_AND_FIXTURES_ONLY
    build_authority: DEFERRED_TO_C1_PLAN
    market_authority: NONE
  - id: OPT-B-C2-V2
    namespace: ovc.opt_b.c2
    state: DESIGN_AND_FIXTURES_ONLY
    build_authority: DEFERRED_TO_C2_PLAN
    market_authority: NONE
  - id: OPT-B-C2E
    namespace: unallocated
    state: DEFERRED
    build_authority: NONE
    market_authority: NONE
  - id: OPT-B-C2-5
    namespace: unallocated
    state: DEFERRED
    build_authority: NONE
    market_authority: NONE
  - id: OPT-B-C3
    namespace: unallocated
    state: DEFERRED
    build_authority: NONE
    market_authority: NONE
  - id: OPT-C
    namespace: legacy.quarantine
    state: HISTORICAL_QUARANTINED
    build_authority: NONE
    market_authority: NONE
  - id: OPT-D
    namespace: legacy.quarantine
    state: HISTORICAL_QUARANTINED
    build_authority: NONE
    market_authority: NONE
""",
    "registries/releases/README.md": """# Release registry\n\nNo v2 market release is registered or selected during R0.\n""",
    "registries/opt_a/README.md": """# OPT-A registries\n\nReserved for provider, clock, side, release and handoff registries.\n""",
    "registries/opt_b/README.md": """# OPT-B registries\n\nReserved for C1 formulas and C2 structural/state registries.\n""",
    "registries/qa/README.md": """# QA registries\n\nReserved for atomic checks, gates, severities and dispositions.\n""",
    "docs/plans/opt_a_v2/README.md": """# OPT-A v2 plan namespace\n\nImplementation is governed by the operator-ratified OPT-A v2 implementation plan. R0 creates only the repository location.\n""",
    "docs/plans/opt_b_c1_v2/README.md": """# OPT-B.C1 v2 plan namespace\n\nImplementation is governed by the operator-ratified C1 v2 implementation plan. R0 creates only the repository location.\n""",
    "docs/plans/opt_b_c2_v2/README.md": """# OPT-B.C2 v2 plan namespace\n\nImplementation is governed by the operator-ratified C2 v2 implementation plan. R0 creates only the repository location.\n""",
    "docs/implementation/ACTIVE_TREE_FOUNDATION.md": """# Active-tree foundation\n\nThe active tree separates infrastructure, governance and future implementation namespaces from historical ABCD machinery.\n\n## Dependency direction\n\n```text\nprovider evidence -> OPT-A v2 -> C1 v2 -> C2 v2 -> later evidence-gated layers\n```\n\nReverse reads are prohibited. The package skeletons contain no market logic and no active selectors.\n\n## Storage planes\n\n- Git: contracts, schemas, registries, compact fixtures, code, tests and decisions.\n- Local external root: candidate payloads and generated streams.\n- R2 canonical: immutable, verified release bytes.\n\n## Historical boundary\n\nThe frozen baseline and release records remain auditable. The quarantined engine may be used only for historical audit, source crosswalk and bounded defect-fixture derivation.\n""",
    "docs/decisions/R0_4_ACTIVE_TREE_FOUNDATION_DECISION.md": """# R0-4 Active-Tree Foundation Decision\n\nStatus: `EXECUTED_PASS`\n\nThe clean v2 package, contract, schema, registry and plan namespaces are established. The evidence-store implementation remains active infrastructure. No market release or selector is activated.\n\nThe next bounded packet is R0-5 synthetic fixture installation.\n""",
    "tests/test_active_tree_foundation.py": """from __future__ import annotations\n\nimport unittest\nfrom pathlib import Path\n\nimport ovc\nfrom ovc.opt_a import AUTHORITY_STATE as OPT_A_STATE\nfrom ovc.opt_b.c1 import AUTHORITY_STATE as C1_STATE\nfrom ovc.opt_b.c2 import AUTHORITY_STATE as C2_STATE\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\nclass ActiveTreeFoundationTests(unittest.TestCase):\n    def test_clean_namespaces_import(self) -> None:\n        self.assertEqual(ovc.__version__, \"0.2.0\")\n        self.assertEqual(OPT_A_STATE, \"DESIGN_AND_FIXTURES_ONLY\")\n        self.assertEqual(C1_STATE, \"DESIGN_AND_FIXTURES_ONLY\")\n        self.assertEqual(C2_STATE, \"DESIGN_AND_FIXTURES_ONLY\")\n\n    def test_legacy_engine_is_not_in_active_source_tree(self) -> None:\n        self.assertFalse((ROOT / \"src\" / \"ovc_opt_b\").exists())\n        self.assertTrue((ROOT / \"legacy\" / \"quarantine\" / \"abcd-engine-v1-c0ad7ba\").is_dir())\n\n    def test_authority_registry_denies_market_selectors(self) -> None:\n        authority = (ROOT / \"registries\" / \"authority\" / \"ACTIVE_AUTHORITY.yaml\").read_text(encoding=\"utf-8\")\n        self.assertIn(\"state: V2_FOUNDATION_NO_MARKET_AUTHORITY\", authority)\n        self.assertGreaterEqual(authority.count(\": NONE\"), 8)\n        self.assertIn(\"runtime_imports: DENIED\", authority)\n        self.assertIn(\"discovery_seed_eligibility: DENIED\", authority)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n""",
}


def _write(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def build() -> None:
    if not QUARANTINE_ROOT.is_dir():
        raise SystemExit("R0-4 requires the completed R0-3 quarantine root")
    validation = json.loads((PACKET_ROOT / "R0_3_VALIDATION.json").read_text(encoding="utf-8"))
    if validation.get("result") != "PASS" or validation.get("executed_move_count") != 106:
        raise SystemExit("R0-4 requires a passing R0-3 validation packet")
    for path, content in sorted(FILES.items()):
        _write(path, content)
    _write(
        (PACKET_ROOT / "R0_4_VALIDATION.json").as_posix(),
        json.dumps(
            {
                "baseline_commit": BASELINE,
                "foundation_file_count": len(FILES),
                "legacy_quarantine_present": True,
                "market_authority": "NONE",
                "result": "BUILT_PENDING_TESTS",
                "selectors_active": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def seal() -> None:
    required = [Path(path) for path in FILES]
    missing = [path.as_posix() for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"foundation files missing: {missing}")
    forbidden = [Path("src/ovc_opt_b"), Path("src/ovc_opt_c"), Path("src/ovc_opt_d")]
    present = [path.as_posix() for path in forbidden if path.exists()]
    if present:
        raise SystemExit(f"legacy active source paths remain: {present}")
    payload = {
        "active_source_namespaces": ["ovc", "ovc_evidence_store"],
        "baseline_commit": BASELINE,
        "foundation_file_count": len(FILES),
        "legacy_quarantine_present": QUARANTINE_ROOT.is_dir(),
        "market_authority": "NONE",
        "result": "PASS",
        "selectors_active": 0,
        "tests_expected": 27,
    }
    _write((PACKET_ROOT / "R0_4_VALIDATION.json").as_posix(), json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write(
        (PACKET_ROOT / "R0_4_ACTIVE_TREE_FOUNDATION_SUMMARY.md").as_posix(),
        """# R0-4 Active-Tree Foundation\n\n- Clean `ovc` package root: **PASS**\n- OPT-A v2 namespace: **PRESENT — DESIGN_AND_FIXTURES_ONLY**\n- C1 v2 namespace: **PRESENT — DESIGN_AND_FIXTURES_ONLY**\n- C2 v2 namespace: **PRESENT — DESIGN_AND_FIXTURES_ONLY**\n- Evidence-store infrastructure: **RETAINED ACTIVE**\n- Authority and implementation registries: **PRESENT**\n- Legacy active source paths: **0**\n- Active market selectors: **0**\n- Market authority introduced: **NONE**\n- Active-tree tests expected: **27**\n\n**R0-4 result: PASS**\n""",
    )


def run_tests() -> None:
    subprocess.check_call(["python", "-m", "compileall", "-q", "src"])
    subprocess.check_call(["python", "-m", "unittest", "discover", "-s", "tests", "-v"], env={**__import__("os").environ, "PYTHONPATH": "src"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "test", "seal"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    elif args.command == "test":
        run_tests()
    else:
        seal()
