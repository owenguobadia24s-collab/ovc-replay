"""Historical Market Grammar C2E v0.1 conformance helpers.

This module deliberately invokes the historical implementation unchanged and
returns comparison evidence only.  It never converts a historical episode ID
into a C2E v0.2 identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ovc.opt_b.market_grammar.episode_ledger import build_episode_ledger

ROOT = Path(__file__).resolve().parents[4]
LEGACY_FIXTURE = ROOT / "fixtures/market_grammar/wp2/c2e_ledger_cases.json"
LEGACY_ARTIFACTS = (
    ROOT / "contracts/opt_b/market_grammar/MG_C2E_EPISODE_LEDGER_CONTRACT_v0_1.md",
    ROOT / "schemas/opt_b/market_grammar/c2e_episode_record_v0_1.schema.json",
    ROOT / "schemas/opt_b/market_grammar/c2e_phase_record_v0_1.schema.json",
    ROOT / "schemas/opt_b/market_grammar/c2e_ledger_v0_1.schema.json",
    ROOT / "schemas/opt_b/market_grammar/c2e_binding_v0_1.schema.json",
    ROOT / "registries/opt_b/market_grammar/MG_C2E_BOUNDARY_POLICY_v0_1.json",
    ROOT / "registries/opt_b/market_grammar/MG_C2E_LIFECYCLE_REGISTRY_v0_1.json",
    ROOT / "src/ovc/opt_b/market_grammar/episode_ledger.py",
    LEGACY_FIXTURE,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_legacy_fixture_conformance() -> dict[str, Any]:
    fixture = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for case in fixture["valid_cases"]:
        ledger = build_episode_ledger(case["records"], build_cutoff=case["build_cutoff"])
        valid.append({
            "case_id": case["case_id"],
            "ledger_id": ledger.ledger_id,
            "episode_ids": [item.episode_id for item in ledger.episodes],
            "episode_count": len(ledger.episodes),
            "not_evaluable_count": len(ledger.not_evaluable),
            "statuses": [item.status.value for item in ledger.episodes],
            "boundary_causes": [item.boundary_cause.value for item in ledger.episodes],
            "phase_kinds": [[phase.phase_kind.value for phase in item.phases] for item in ledger.episodes],
        })
    for case in fixture["invalid_cases"]:
        try:
            build_episode_ledger(case["records"], build_cutoff=case["build_cutoff"])
        except ValueError as exc:
            invalid.append({"case_id": case["case_id"], "error": str(exc)})
        else:
            raise AssertionError(f"legacy invalid fixture did not fail: {case['case_id']}")
    return {
        "schema": "c2e_legacy_fixture_conformance/v0_2",
        "legacy_policy_id": fixture["policy_id"],
        "legacy_authority": fixture["authority"],
        "comparison_only": True,
        "runtime_selectable_by_c2e2": False,
        "valid_results": valid,
        "invalid_results": invalid,
        "artifact_sha256": {str(path.relative_to(ROOT)): _sha256(path) for path in LEGACY_ARTIFACTS},
    }
