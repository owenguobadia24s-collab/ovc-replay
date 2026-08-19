from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def canonical_sha256(record: dict) -> str:
    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_operator_pass_materialises_exact_admission_delta():
    decision = load(
        "docs/releases/development-skills-v0-3/cers-persistent-supervisor/admission/"
        "CERS_G_OVC_WIDE_ADMISSION_1_OPERATOR_DECISION_v0_1.json"
    )
    assert decision["gate_id"] == "CERS-G-OVC-WIDE-ADMISSION-1"
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["operator_phrase"] == "OVC APPROVE CERS-G-OVC-WIDE-ADMISSION-1 PASS"
    assert decision["operator_decision_time"] == "2026-08-19T21:15:00+01:00"
    assert decision["future_programme_auto_admission"] is False
    assert decision["operator_boundary_policy"] == "PARK"
    assert set(decision["newly_admitted_programmes"]) == {
        "OVC-P2CTI-CONFORMANCE-v0.1",
        "OVC-ASOCS-6M-v0.1",
        "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
    }


def test_root_registry_and_admission_registry_are_exact_and_exhaustive():
    roots = load("registries/development/skills/cers/CERS_PROGRAMME_ROOT_REGISTRY_v0_2.json")
    registry = load(
        "registries/development/skills/cers/CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_4.json"
    )
    root_map = {row["root_id"]: row["path"] for row in roots["roots"]}
    assert set(root_map) == {
        "CERS", "DSAI3V_VIT", "DSAI3V_ASYNC_ASSURANCE", "DSAI2_ORCH345",
        "GRT_V0_2", "PRVITR", "P2CTI", "ASOCSI",
    }
    assert registry["source_root_registry"].endswith("CERS_PROGRAMME_ROOT_REGISTRY_v0_2.json")
    assert registry["status"] == "ACTIVE_PERSISTENT"
    assert registry["future_programme_auto_admission"] is False
    entries = {row["programme_id"]: row for row in registry["entries"]}
    assert set(entries) == {
        "OVC-DSAI3V-CERS-CONFORMANCE-v0.1",
        "OVC-P2CTI-CONFORMANCE-v0.1",
        "OVC-ASOCS-6M-v0.1",
        "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
    }
    excluded = {row["programme_id"] for row in registry["exclusions"]}
    assert excluded == {
        "OVC-DSAI-VIT-v0.3",
        "OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-v0.1",
        "OVC-DSAI-v0.2",
        "OVC-PRVIT-LIVE-REMEDIATION-CONFORMANCE-v0.1",
    }
    hashes = {row["admission_id"]: row["canonical_sha256"] for row in registry["entry_hashes"]}
    for entry in registry["entries"]:
        assert hashes[entry["admission_id"]] == canonical_sha256(entry)
        assert entry["operator_boundary_policy"] == "PARK"
        assert entry["eligible_authority_classes"] == ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"]
        assert entry["eligible_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
        assert entry["allowed_side_effect_classes"] == ["BRANCH_REVERSIBLE"]
        assert entry["revocation_behavior"] == "DISABLE_NEW_DISPATCH"


def test_each_new_admission_preserves_its_reserved_boundary():
    registry = load(
        "registries/development/skills/cers/CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_4.json"
    )
    entries = {row["programme_id"]: row for row in registry["entries"]}

    p2cti = entries["OVC-P2CTI-CONFORMANCE-v0.1"]
    assert p2cti["current_state_root"] == "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json"
    assert "P2CTI_OBSERVABILITY_ACTIVATION" in p2cti["explicit_prohibitions"]
    assert "P2CTI_CONTINUOUS_INTAKE_WRITES" in p2cti["explicit_prohibitions"]

    asocsi = entries["OVC-ASOCS-6M-v0.1"]
    assert asocsi["current_state_root"] == "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
    assert "HUMAN_REVIEW_OR_HUMAN_INPUT_AUTOMATION" in asocsi["explicit_prohibitions"]
    assert "ASOCSI_G7_OPERATOR_BOUNDARY_BYPASS" in asocsi["explicit_prohibitions"]

    grt = entries["OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"]
    assert grt["current_state_root"] == "registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json"
    assert "GRT2_G3_ACTIVATION" in grt["explicit_prohibitions"]
    assert "CONSTITUTION_ACTIVATION" in grt["explicit_prohibitions"]
    assert "DEBT_FLOOR_ACTIVATION" in grt["explicit_prohibitions"]


def test_cers_state_advances_append_only_and_keeps_persistent_run_bounded():
    old = load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_17.json")
    pointer = load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
    current = load(pointer["current_state"])
    old_registry = load("registries/development/skills/cers/CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_3.json")

    assert old["admission_registry"].endswith("CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_3.json")
    assert len(old_registry["entries"]) == 1
    assert current["supersedes_state"] == "OVC_DSAI3V_CERS_STATE_v0_17.json"
    assert pointer["current_state"].endswith("OVC_DSAI3V_CERS_STATE_v0_18.json")
    assert current["packet_id"] == "CERS-G-OVC-WIDE-ADMISSION-1"
    assert current["decision"] == "PASS"
    assert current["decision_authority"] == "OPERATOR"
    assert current["persistent_run"] == "ACTIVATED"
    assert current["persistent_general_dispatch"] == "ALLOWED_EXACT_ADMITTED_SCOPE_ONLY"
    assert current["parallel_physical_merge"] is False
    assert current["reserved_authority_unchanged"] is True
    assert current["admission_expansion_gate"]["effective_admitted_programme_count"] == 4
    assert current["admission_expansion_gate"]["operator_required_boundaries"] == "PARK"


def test_census_records_open_work_as_reconcile_not_duplicate_start():
    census = load(
        "docs/releases/development-skills-v0-3/cers-persistent-supervisor/admission/"
        "CERS_OVC_WIDE_ADMISSION_CENSUS_v0_1.json"
    )
    open_work = {row["programme_id"]: row for row in census["open_work_reconciliation"]}
    assert open_work["OVC-P2CTI-CONFORMANCE-v0.1"]["open_pr"] == 1247
    assert open_work["OVC-ASOCS-6M-v0.1"]["open_pr"] == 1253
    assert open_work["OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"]["open_pr"] == 1252
    assert all("NO_DUPLICATE_START" in row["rule"] for row in open_work.values())
