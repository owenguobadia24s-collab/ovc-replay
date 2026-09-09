import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.sff.core import SFFContractError, content_identity
from ovc.research_operations.sff.readiness import REQUIRED_GREAL_FIELDS, compile_greal_candidate


ROOT = Path(__file__).resolve().parents[3]
ORG1 = ROOT / "docs/programmes/sff-v0-1/wp9/org1"
OLD_MANIFEST = ROOT / "docs/programmes/sff-v0-1/wp9/SFFI_GREAL_CANDIDATE_BUNDLE_v0_1.json"
OLD_GATE = ROOT / "docs/programmes/sff-v0-1/wp9/SFFI_GREAL_SCI_PREREG_OPERATOR_GATE_PACKET_v0_1.json"
INPUT = ORG1 / "SFFI_GREAL_ORG1_CANDIDATE_INPUT_v0_1.json"
MANIFEST = ORG1 / "SFFI_GREAL_ORG1_CANDIDATE_BUNDLE_v0_1.json"
DECISION = ORG1 / "SFFI_GREAL_ORG1_SUPERSESSION_OPERATOR_DECISION_v0_1.json"
AUTHORITY = ORG1 / "SFFI_GREAL_ORG1_AUTHORITY_CHAIN_v0_1.json"
FREEZE = ORG1 / "SFFI_GREAL_ORG1_EFFECTIVE_FREEZE_RECEIPT_v0_1.json"
STATE = ROOT / "records/research_operations/sff/SFFI_PROGRAMME_STATE_v0_2.json"
POINTER = ROOT / "registries/research_operations/sff/SFFI_GREAL_CURRENT_CANDIDATE_v0_1.json"

OLD_ID = "sff-greal-candidate:ab3967aadba8503c6179079b6b820c21a543210f04ddca6febd85dc3ed7c6a53"
MODEL_SET = "b139d57331830bad0d9ded1296c4fa20477bfbd0566da86b72aa9b160c6e2a29"
EVAL_FREEZE = "a895753a34af70f50d4b95e6ae87787121d9f0133823faa45e750e8c81aa56ca"
GTARGET_APPROVAL = "6cf36faabc30048a1fc24cabf69c1163341171227f29b5e4a254b39e194e2920"
SOURCE_APPROVAL = "1135c746fcf49aeb5c5c92ee94a5b8a0e8dd5a9f1db0f6370eaa2b9ca010ffeb"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_org1_successor_candidate_is_exact_and_old_candidate_is_preserved() -> None:
    old = read(OLD_MANIFEST)
    old_gate = read(OLD_GATE)
    supplied = read(INPUT)["fields"]
    compiled = compile_greal_candidate(supplied)
    manifest = read(MANIFEST)

    assert old["candidate_id"] == OLD_ID
    assert old_gate["candidate_id"] == OLD_ID
    assert tuple(compiled.fields) == REQUIRED_GREAL_FIELDS
    assert len(compiled.fields) == 29
    assert manifest["candidate_id"] == compiled.candidate_id
    assert manifest["bundle_sha256"] == compiled.bundle_sha256
    assert manifest["preregistration_bundle_id"] == compiled.preregistration_bundle_id
    assert manifest["atomic_freeze_receipt_candidate"] == compiled.fields["atomic_freeze_receipt_candidate"]
    assert manifest["supersedes_candidate_id"] == OLD_ID
    assert compiled.fields["static_model_generation"]["model_set_sha256"] == MODEL_SET
    assert compiled.fields["no_outcome_access_embargo_proof"]["protected_outcomes_accessed"] is False
    assert compiled.fields["no_outcome_access_embargo_proof"]["eval_population_freeze_sha256"] == EVAL_FREEZE
    assert compiled.fields["population"]["eval_a"]["source_bundle_sha256"] == "fcfeab08b0b255e25e413b551b3c75c763469d126dd74e9dbe25129a92343eaa"
    assert compiled.fields["population"]["eval_b"]["source_bundle_sha256"] == "3f3beea0af3f43ab9c3c334847d4a8d3eb0bc555bf8dabb18a72d45782a474b7"
    assert compiled.fields["population"]["mutually_disjoint"] is True


def test_operator_chain_grants_only_exact_org1_after_parent_materialisation() -> None:
    manifest = read(MANIFEST)
    decision = read(DECISION)
    authority = read(AUTHORITY)
    freeze = read(FREEZE)
    state = read(STATE)
    pointer = read(POINTER)

    assert decision["operator_command"] == "OVC SUPERSEDE SFFI-GREAL-SCI-PREREG WITH ORG1"
    assert decision["decision"] == "SUPERSEDE"
    assert decision["old_candidate_id"] == OLD_ID
    assert decision["new_candidate_id"] == manifest["candidate_id"]
    assert decision["scoring_authority_sha256"] == GTARGET_APPROVAL
    assert decision["source_intake_authority_sha256"] == SOURCE_APPROVAL

    assert authority["supersession_alone_grants_scoring"] is False
    assert authority["gtarget_pass_alone_without_parent_materialisation_grants_scoring"] is False
    assert [step["step"] for step in authority["chain"]] == [1, 2, 3]
    assert authority["chain"][0]["sha256"] == SOURCE_APPROVAL
    assert authority["chain"][1]["sha256"] == GTARGET_APPROVAL

    assert freeze["candidate_id"] == manifest["candidate_id"]
    assert freeze["model_set_sha256"] == MODEL_SET
    assert freeze["eval_population_freeze_sha256"] == EVAL_FREEZE
    assert freeze["protected_outcomes_accessed"] is False
    assert freeze["real_study_frozen"] is True
    payload = {
        "candidate_id": freeze["candidate_id"],
        "preregistration_bundle_id": freeze["preregistration_bundle_id"],
        "candidate_freeze_receipt_id": freeze["candidate_freeze_receipt_id"],
        "operator_supersession_command": freeze["operator_supersession_command"],
        "gtarget_operator_approval_sha256": freeze["gtarget_operator_approval_sha256"],
        "eval_population_freeze_sha256": freeze["eval_population_freeze_sha256"],
        "model_set_sha256": freeze["model_set_sha256"],
        "protected_outcomes_accessed": freeze["protected_outcomes_accessed"],
        "real_study_frozen": freeze["real_study_frozen"],
        "atomic": freeze["atomic"],
    }
    assert freeze["receipt_id"] == content_identity("sff-greal-effective-freeze-receipt", payload)

    assert pointer["current_candidate_id"] == manifest["candidate_id"]
    assert pointer["supersedes_candidate_id"] == OLD_ID
    assert state["greal_candidate_id"] == manifest["candidate_id"]
    assert state["protected_outcomes_accessed"] is False
    assert state["validation_state"] == "LOCKED_UNCONSUMED"
    assert state["next_packet"] == "ORG1-R4-EVAL-A-PROSPECTIVE-REPLAY"


def test_org1_candidate_fails_closed_on_outcome_or_identity_mutation() -> None:
    supplied = read(INPUT)["fields"]

    leaked = copy.deepcopy(supplied)
    leaked["no_outcome_access_embargo_proof"]["protected_outcomes_accessed"] = True
    with pytest.raises(SFFContractError, match="EMBARGO"):
        compile_greal_candidate(leaked)

    retuned = copy.deepcopy(supplied)
    retuned["static_model_generation"]["model_set_sha256"] = "changed"
    changed = compile_greal_candidate(retuned)
    assert changed.candidate_id != read(MANIFEST)["candidate_id"]

    expanded = copy.deepcopy(supplied)
    expanded["exposure_class"]["sides"].append("ASK")
    changed = compile_greal_candidate(expanded)
    assert changed.candidate_id != read(MANIFEST)["candidate_id"]
