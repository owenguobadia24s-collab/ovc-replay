import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
REVEAL = WP8 / "ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json"
TEMPLATE = WP8 / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json"
MANIFEST = WP8 / "ASOCSI_WP8_S01_STAGE1_WP7_PROJECTION_MANIFEST_v0_1.json"
ARTIFACT = WP8 / "ASOCSI_WP8_S01_STAGE1_REVIEW_WORKBOOK_ARTIFACT_v0_1.json"
QA = WP8 / "ASOCSI_WP8_S01_STAGE1_HUMAN_REVIEW_INTERFACE_QA_v0_1.json"
SCHEMA = ROOT / "schemas/research_operations/asocs/asocs_stage1_fidelity_judgement_v0_1.schema.json"

EXPECTED_REVEAL_SHA = "5ae775fd5ac9ad5afcecec4f57f3b3fb4fdb5d1d25e2a8d1d9769fde1c52f5c7"
EXPECTED_TEMPLATE_SHA = "607b1d48137b01f3cbb9ea7ae737382fe6ee152497e412fcb725b6ae635b9c9b"
EXPECTED_WORKBOOK_SHA = "4c4a2b6cccb8b2d4551ce6365fe82a6d04519f62cb90b61a004d22f3b739e2b4"
EXPECTED_WORKBOOK_BYTES = 485487
EXPECTED_WP7_SOURCE_SHA = "19101e1e0a32b5d9c605ad3e21242b14e292c4a585c5a37edd1e9279b9b0005f"
EXPECTED_WP7_HUMAN_SHA = "9aaa80991365cf290122caef513f0e8d706a7b1283475fa041d01d8e5f9f1a0e"
CASE19 = "ASOCS.BLIND.9b251b8cfedc5e9a61396830"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_raw_stage1_machine_records_remain_byte_identical():
    assert _sha(REVEAL) == EXPECTED_REVEAL_SHA
    assert _sha(TEMPLATE) == EXPECTED_TEMPLATE_SHA


def test_exact_25_case_order_identity_and_predecessor_bindings():
    reveal = _load(REVEAL)
    template = _load(TEMPLATE)
    manifest = _load(MANIFEST)
    assert reveal["case_count"] == 25
    assert len(reveal["cases"]) == len(template["cases"]) == len(manifest["cases"]) == 25
    assert [c["presentation_ordinal"] for c in reveal["cases"]] == list(range(1, 26))
    assert [c["presentation_ordinal"] for c in manifest["cases"]] == list(range(1, 26))
    for ordinal, (rc, tc, wc) in enumerate(
        zip(reveal["cases"], template["cases"], manifest["cases"]), start=1
    ):
        assert rc["presentation_ordinal"] == tc["presentation_ordinal"] == wc["presentation_ordinal"] == ordinal
        assert rc["case_id"] == tc["case_id"] == wc["case_id"]
        assert rc["review_unit_id"] == tc["review_unit_id"]
        assert rc["predecessor_blind_record_sha256"] == tc["predecessor_blind_record_sha256"]


def test_wp7_projection_is_bound_to_actual_frozen_reviewer_interface():
    manifest = _load(MANIFEST)
    assert manifest["case_count"] == 25
    assert manifest["source"]["drive_downloaded_bytes_sha256"] == EXPECTED_WP7_SOURCE_SHA
    assert manifest["source"]["prior_frozen_human_input_sha256"] == EXPECTED_WP7_HUMAN_SHA
    assert manifest["source"]["embedded_authoritative_review_html_sha256"] == "582b956fe9c996894e95daef33ae1821daef05668bf3c6186074443ee1522ffc"
    assert manifest["projection_rule"] == "CASE_ID + ORDINAL + WP7 LOCAL SOURCE_NATIVE SVG + FROZEN REVIEW_STATUS + FROZEN A0-A8 ONLY"
    assert all(len(c["projection_sha256"]) == 64 for c in manifest["cases"])
    assert manifest["later_stage_evidence_included"] is False


def test_external_workbook_is_content_addressed_and_contract_bound():
    artifact = _load(ARTIFACT)
    assert artifact["artifact_role"] == "HUMAN_REVIEW_WORKBOOK_PRESENTATION_PROJECTION"
    assert artifact["authoritative_machine_record"] is False
    assert artifact["sha256"] == EXPECTED_WORKBOOK_SHA
    assert artifact["byte_size"] == EXPECTED_WORKBOOK_BYTES
    assert artifact["mime_type"] == "text/html"
    assert artifact["external_store"] == "GOOGLE_DRIVE"
    assert artifact["source_bindings"]["stage1_reveal_packet"]["sha256"] == EXPECTED_REVEAL_SHA
    assert artifact["source_bindings"]["stage1_human_input_template"]["sha256"] == EXPECTED_TEMPLATE_SHA
    contract = artifact["workbook_contract"]
    assert contract["case_count"] == 25
    assert contract["presentation_order"] == "FROZEN_SESSION_ORDER"
    assert contract["wp7_chart_projection"] == "ORIGINAL_LOCAL_SOURCE_NATIVE_SVG_FROM_FROZEN_WP7_REVIEWER_WORKBOOK"
    assert contract["wp7_observations"] == ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8_CONFIDENCE", "A8_AMBIGUITY"]
    assert contract["stage1_machine_source_policy"] == "LOAD_ONLY_EXACT_HASH_BOUND_REVEAL_AND_TEMPLATE"
    assert contract["c1_exact_value_policy"] == "DIRECT_RAW_PACKET_VALUE_NO_RECOMPUTATION"
    assert contract["human_formatting_policy"] == "PRESENTATIONAL_ONLY_DETERMINISTIC"
    assert contract["human_response_prepopulation"] == "NONE"
    assert contract["automatic_submission"] is False
    assert contract["repository_mutation"] is False


def test_c1_packet_contains_exact_values_and_workbook_forbids_recomputation():
    reveal = _load(REVEAL)
    artifact = _load(ARTIFACT)
    assert reveal["human_reviewer_does_not_recompute_formula_arithmetic"] is True
    assert reveal["mechanical_arithmetic_check"] == "PASS_EXACT_FROZEN_TRACE_PAYLOAD_FOR_ANCHOR_CASES"
    anchor_cases = [c for c in reveal["cases"] if c["revealed_evidence"]["kind"] == "ANCHOR_15M"]
    assert len(anchor_cases) == 24
    for case in anchor_cases:
        c1 = case["revealed_evidence"]["c1"]
        assert isinstance(c1["measurements"], dict)
        assert isinstance(c1["categorical"]["direction"], str)
        assert c1["schema"] == "ovc-asocs-c1-morphology-audit/v0_1"
    assert artifact["workbook_contract"]["c1_exact_value_policy"] == "DIRECT_RAW_PACKET_VALUE_NO_RECOMPUTATION"


def test_human_readable_values_are_separate_presentational_projections():
    artifact = _load(ARTIFACT)
    qa = _load(QA)
    assert artifact["workbook_contract"]["human_formatting_policy"] == "PRESENTATIONAL_ONLY_DETERMINISTIC"
    assert qa["validation"]["06_human_formatting_deterministic_projection_only"]["status"] == "PASS"
    assert "exact values remain separately visible and authoritative" in qa["validation"]["06_human_formatting_deterministic_projection_only"]["evidence"]


def test_stage1_firewall_has_no_stage2_c2_composition_c2e_or_occurrence_context_evidence():
    reveal = _load(REVEAL)
    artifact = _load(ARTIFACT)
    qa = _load(QA)
    assert reveal["stage"] == "SOURCE_C1_FIDELITY"
    assert reveal["stage_index"] == 1
    assert reveal["later_stage_reveal_status"] == "NOT_CONSTRUCTED_NOT_REVEALED"
    assert artifact["workbook_contract"]["stage2_reveal"] == "NOT_CONSTRUCTED_NOT_REVEALED"
    for key in (
        "07_no_stage2_c2_structural_evidence",
        "08_no_c2_composition_evidence",
        "09_no_c2e_evidence",
        "10_no_occurrence_context_evidence",
    ):
        assert qa["validation"][key]["status"] == "PASS"


def test_no_stage1_human_response_is_prepopulated_or_inferred():
    template = _load(TEMPLATE)
    artifact = _load(ARTIFACT)
    for case in template["cases"]:
        j = case["human_judgement"]
        assert j["fidelity_disposition"] is None
        assert j["observational_correspondence"] == ""
        assert j["prior_bridge_disposition"] is None
        assert j["semantic_leakage"] is None
        assert j["traceability"] is None
        assert j["information_gap_disposition"] is None
        assert j["notes"] == ""
        assert j["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert artifact["workbook_contract"]["human_response_prepopulation"] == "NONE"


def test_case19_source_gap_warning_contract():
    reveal = _load(REVEAL)
    artifact = _load(ARTIFACT)
    qa = _load(QA)
    case19 = reveal["cases"][18]
    assert case19["case_id"] == CASE19
    evidence = case19["revealed_evidence"]
    assert evidence["kind"] == "SOURCE_GAP"
    assert evidence["c1_disposition"] == "C1_NOT_EVALUABLE_SOURCE"
    assert evidence["repair_applied"] is False
    assert artifact["workbook_contract"]["case19_source_gap_warning"] == "PROMINENT"
    assert qa["case19"]["judgement_preselected"] is False
    assert qa["case19"]["contract_guidance"] == [
        "INFORMATION_GAP_EVALUATED_FIRST",
        "SOURCE_LIMITATION_NOT_AUTOMATIC_SEMANTIC_FAILURE",
        "SOURCE_GAP_C1_UNAVAILABLE_NOT_ARITHMETIC_DEFECT",
    ]


def test_export_scaffold_preserves_machine_bindings_and_matches_judgement_schema():
    template = _load(TEMPLATE)
    schema = _load(SCHEMA)
    artifact = _load(ARTIFACT)
    out = copy.deepcopy(template)
    valid = {
        "fidelity_disposition": "PASS_FIDELITY",
        "observational_correspondence": "Human-authored test value.",
        "prior_bridge_disposition": "VALID",
        "semantic_leakage": "NONE",
        "traceability": "PASS",
        "information_gap_disposition": "NOT_INFORMATION_GAP",
        "notes": "",
    }
    required = set(schema["required"])
    props = schema["properties"]
    for src, dst in zip(template["cases"], out["cases"]):
        dst["human_judgement"].update(valid)
        j = dst["human_judgement"]
        assert required <= set(j)
        for field in (
            "fidelity_disposition",
            "prior_bridge_disposition",
            "semantic_leakage",
            "traceability",
            "information_gap_disposition",
        ):
            assert j[field] in props[field]["enum"]
        assert len(j["observational_correspondence"]) >= props["observational_correspondence"]["minLength"]
        assert j["construct_survival_decision"] == props["construct_survival_decision"]["const"]
        assert j["schema"] == props["schema"]["const"]
        assert j["stage"] == props["stage"]["const"]
        for key in ("case_id", "presentation_ordinal", "review_unit_id", "predecessor_blind_record_sha256"):
            assert dst[key] == src[key]
    assert artifact["export"]["filename"] == "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT.json"
    assert artifact["export"]["only_human_judgement_fields_mutable"] is True
    assert artifact["export"]["base_template_sha256"] == EXPECTED_TEMPLATE_SHA


def test_all_thirteen_interface_validation_checks_are_pass():
    qa = _load(QA)
    assert len(qa["validation"]) == 13
    assert {key[:2] for key in qa["validation"]} == {f"{i:02d}" for i in range(1, 14)}
    assert all(item["status"] == "PASS" for item in qa["validation"].values())
    assert qa["qa_recommendation"] == "PASS"
    assert qa["stage2_reveal_started"] is False
