from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "programmes" / "synergetics-v0-1"

def _load(rel: str):
    return json.loads((BASE / rel).read_text(encoding="utf-8"))

def test_synergetics_materialisation_records_and_caps():
    spec = _load("00_PROTOCOL/OVC_SYNERGETICS_R5_Model_and_Challenger_Specification_v0_1.json")
    lineage = _load("04_RESULTS_AND_EVIDENCE/OVC_SYNERGETICS_R0_R5_Lineage_State_v0_1.json")
    qa = _load("04_RESULTS_AND_EVIDENCE/OVC_SYNERGETICS_R0_R5_QA_v0_1.json")
    bind = _load("05_REPRODUCIBILITY/OVC_SYNERGETICS_R0_R5_Source_Binding_Manifest_v0_1.json")
    custody = _load("05_REPRODUCIBILITY/OVC_SYNERGETICS_R0_R5_Laboratory_Custody_Receipt_v0_1.json")
    decision = _load("06_REVIEWS_AND_DECISIONS/OVC_SYNERGETICS_R0_R5_Materialisation_Decision_v0_1.json")
    r6 = _load("06_REVIEWS_AND_DECISIONS/OVC_SYNERGETICS_R6_Parent_Freeze_Readiness_v0_2.json")

    assert spec["authority_effect"] == "NONE"
    assert lineage["authority_effect"] == "NONE"
    assert qa["status"] == "PASS_WITH_RETROSPECTIVE_SCOPE_RESTRICTION"
    assert qa["archive_hash_gate"] == "PASS"
    assert len(bind["decision_bearing_inputs"]) == 7
    assert custody["status"] == "PASS_CUSTODY_VERIFIED"
    assert custody["controlling_bundle"]["sha256"] == "cfd70605f14926376a9f8f27b77758b6e6fe6c499dc9ac17ccbd342aa74e2101"
    assert custody["implementation"]["runner_sha256"] == "cee1194f1daba444048b482eec8a1f18d6682c0996bf8c479498d6310802e38f"
    assert decision["decision"] == "PASS"
    assert decision["theory_promotion"] == "NOT_AUTHORISED"
    assert decision["r5_controlling_disposition"].startswith("NON_ADIABATIC_DEVELOPMENTAL_CONTROL_SURVIVING_CHALLENGER")
    assert r6["fresh_execution_status"] == "BLOCKED_DATA_AND_OPERATOR_AUTHORITY"

def test_r5_spec_and_exact_parent_hashes_are_frozen():
    spec_path = BASE / "00_PROTOCOL" / "OVC_SYNERGETICS_R5_Model_and_Challenger_Specification_v0_1.json"
    assert hashlib.sha256(spec_path.read_bytes()).hexdigest() == "84732220588c693109e96170fe825378e5c855a284884265b6386bb05b305a7b"
    bind = _load("05_REPRODUCIBILITY/OVC_SYNERGETICS_R0_R5_Source_Binding_Manifest_v0_1.json")
    hashes = {a["artifact_id"]: a["sha256"] for a in bind["decision_bearing_inputs"]}
    assert hashes["P5R1-AC-EXACT-ARCHIVE-0.1"] == "5c0eb1f1beafedc134349ef769453d675e74bbff9673cc92b5093c05f867a724"
    assert hashes["P5R1-AI-EXACT-ARCHIVE-0.1"] == "baa9681a84b3348cb3bb4c74d2e2a0ac5bf103ba896773ea21d9b047c11946c6"
