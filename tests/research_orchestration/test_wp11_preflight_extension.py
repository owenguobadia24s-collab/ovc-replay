from __future__ import annotations

import json
from pathlib import Path

from ovc.research_orchestration.closeout import MetadataOnlyExtensionAdapter, build_extension_plan, preflight_real_population
from ovc.research_orchestration.golden import build_golden_plan

ROOT = Path(__file__).resolve().parents[2]
C2E_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_27.json"


def test_real_population_preflight_denies_before_protected_data_resolution() -> None:
    state = json.loads(C2E_STATE.read_text(encoding="utf-8"))
    plan = build_golden_plan()
    result = preflight_real_population(main_sha="WP11-BASELINE", c2e_state=state, plan=plan)
    assert result["execution_status"] == "NOT_AUTHORISED"
    assert result["readiness_disposition"] == "REAL_RUN_NOT_READY_AND_NOT_AUTHORISED"
    assert result["protected_data_accessed"] is False
    assert result["owner_gate"] == "C2E2-G6-RUN-AUTH"
    assert "C2E2_G6_FRESH_RUN_AUTH_REQUIRED" in result["blockers"]
    assert "C2E_REPLACEMENT_REAL_SOURCE_FRAME_POPULATION_NOT_FROZEN" in result["blockers"]
    assert "C2E_ACTIVE_BOUNDARY_PACK_NONE" in result["blockers"]
    assert result["blocked_stage_id"] == "C2E_V0_2"
    assert "SRI_REPRESENTATION" in result["blocked_descendants"]
    assert "RESEARCH_OPERATIONS" in result["blocked_descendants"]


def test_future_metadata_stage_registers_and_executes_without_scheduler_change() -> None:
    plan = build_extension_plan()
    assert plan.ordered_stage_ids == ("RESEARCH_OPERATIONS", "FUTURE_METADATA_ONLY")
    adapter = MetadataOnlyExtensionAdapter()
    first = adapter.execute({"source_refs": ["B", "A"], "metadata": {"kind": "future-test-stage"}})
    second = adapter.execute({"source_refs": ["A", "B"], "metadata": {"kind": "future-test-stage"}})
    assert first == second
    assert first["scientific_effect"] == "NONE"
    assert first["authority_effect"] == "NONE"


def test_extension_is_metadata_only_and_cannot_create_reserved_authority() -> None:
    result = MetadataOnlyExtensionAdapter().execute({"metadata": {"selector": "NONE", "execution": "NONE"}})
    assert result["authority_effect"] == "NONE"
    assert result["scientific_effect"] == "NONE"
