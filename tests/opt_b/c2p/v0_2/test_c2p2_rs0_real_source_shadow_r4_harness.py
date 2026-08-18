from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import run_indexed_empirical_runtime


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts/c2p2_rs0_real_source_shadow_r4.py"
SPEC = importlib.util.spec_from_file_location("c2p2_rs0_real_source_shadow_r4_test_target", SCRIPT)
assert SPEC and SPEC.loader
r4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r4)


def level_row(ordinal: int, *, value: str) -> dict:
    stamp = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * ordinal)
    iso = stamp.isoformat().replace("+00:00", "Z")
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": f"R4-HARNESS-{ordinal:04d}",
        "source_record_kind": "C2_LEVEL",
        "instrument": "GBPUSD",
        "side": "ASK",
        "clock": "15M",
        "first_valid_time": iso,
        "evaluation_cutoff": iso,
        "geometry_signature": {
            "horizon_id": "H15",
            "level_type": "SWING_HIGH",
            "value": value,
            "origin": "R4_HARNESS",
            "structural_depth": 1,
        },
        "relation_topology": ["REL-A"],
    }


def test_r4_authority_and_prelaunch_bind_exact_qualified_generation() -> None:
    decision = json.loads((ROOT / r4.DECISION_PATH).read_text(encoding="utf-8"))
    prelaunch = json.loads((ROOT / r4.PRELAUNCH_PATH).read_text(encoding="utf-8"))
    authority = json.loads((ROOT / r4.AUTHORITY_PATH).read_text(encoding="utf-8"))
    prior = json.loads((ROOT / r4.PRIOR_CONSUMPTION_PATH).read_text(encoding="utf-8"))

    assert decision["decision"] == "PASS"
    assert decision["accepted_evidence_contract"]["contract_id"] == r4.EVIDENCE_CONTRACT
    assert prelaunch["status"] == "PASS"
    assert prelaunch["source_read"] is False
    assert prelaunch["semantic_execution_started"] is False
    assert authority["authority_id"] == r4.AUTHORITY_ID
    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["run_count_remaining"] == 1
    assert authority["no_vit"] is True
    assert authority["runtime_binding"]["binding_id"] == r4.RUNTIME_BINDING_ID
    assert authority["runtime_binding"]["evidence_contract_id"] == r4.EVIDENCE_CONTRACT
    assert prior["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4"
    assert prior["execution_count_consumed"] == 1
    assert prior["run_count_remaining"] == 0


def test_repo_bindings_validate_without_source_read_or_token_consumption() -> None:
    observed = r4.validate_repo_bindings(ROOT)
    assert observed["authority_id"] == r4.AUTHORITY_ID
    assert observed["runtime_binding_id"] == r4.RUNTIME_BINDING_ID
    assert observed["runtime_generation_id"] == r4.RUNTIME_GENERATION_ID
    assert observed["evidence_contract_id"] == r4.EVIDENCE_CONTRACT
    assert observed["source_order_binding_id"] == r4.SOURCE_ORDER_BINDING_ID
    assert observed["source_materialisation_id"] == r4.SOURCE_MATERIALISATION_ID
    assert observed["capacity"]["external_storage_limit_bytes"] == r4.STORAGE_LIMIT


def test_compact_scientific_summary_reads_indexed_v02_evidence_contract(tmp_path: Path) -> None:
    spec = {
        "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        "activation_eligible": False,
    }
    rows = [
        level_row(0, value="1.2500"),
        level_row(1, value="1.2500"),
        level_row(2, value="1.2500"),
        level_row(3, value="1.2600"),
        level_row(4, value="1.2700"),
    ]
    work = tmp_path / "indexed"
    manifest = run_indexed_empirical_runtime(
        rows,
        spec,
        {"entries": []},
        work_dir=work,
        checkpoint_cadence=2,
        storage_limit_bytes=r4.STORAGE_LIMIT,
    )
    summary = r4.compact_scientific_summary(work / manifest["database_file"], manifest)
    assert summary["runtime_generation_id"] == r4.RUNTIME_GENERATION_ID
    assert summary["evidence_contract_id"] == r4.EVIDENCE_CONTRACT
    assert summary["counts"]["processed_source_record_ids"] == len(rows)
    assert summary["negative_coverage_summary"]["certificate_count"] == len(rows)
    assert summary["negative_coverage_summary"]["contract_id"] == r4.EVIDENCE_CONTRACT
    assert sum(summary["decision_terminal_counts"].values()) == len(rows)


def test_workflow_is_authority_triggered_single_use_and_no_vit() -> None:
    text = (ROOT / ".github/workflows/c2p2-rs0-real-source-shadow-run-r4.yml").read_text(encoding="utf-8")
    assert "run/c2p2-rs0-real-source-shadow-r4-20260818" in text
    assert "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_5.json" in text
    assert "Launch exactly one authorised R4 A/B/C real-source shadow execution" in text
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_4.json" in text
    assert "actions/download-artifact@v4" in text
    assert "run-id: '32010902424'" in text
    assert "vit-" not in text.lower()
    assert "no_vit" in text.lower()


def test_r4_packet_preserves_selection_activation_validation_denials() -> None:
    packet = json.loads((
        ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R4_PACKET_v0_1.json"
    ).read_text(encoding="utf-8"))
    assert packet["status"] == "PREPARED_PENDING_SINGLE_USE_AUTHORITY"
    assert packet["selection_state"] == "NONE"
    assert packet["activation_state"] == "NONE"
    assert packet["validation"] == "LOCKED_UNCONSUMED"
    assert packet["no_vit"] is True
    assert packet["next_gate_on_completion"] == "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION"
    assert packet["next_gate_on_post_semantic_failure"] == "C2P2-RS0-RUN-RECOVERY-R4"
