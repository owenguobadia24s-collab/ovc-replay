import json
from pathlib import Path

import pytest

from ovc.research_operations.sff.core import SFFContractError, canonical_bytes
from ovc.research_operations.sff.readiness import REQUIRED_GREAL_FIELDS, compile_greal_candidate


ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "docs/programmes/sff-v0-1/wp9/SFFI_GREAL_CANDIDATE_INPUT_v0_1.json"
MANIFEST = ROOT / "docs/programmes/sff-v0-1/wp9/SFFI_GREAL_CANDIDATE_BUNDLE_v0_1.json"


def candidate_input():
    return json.loads(INPUT.read_text(encoding="utf-8"))["fields"]


def test_exact_candidate_is_complete_content_addressed_and_reproducible() -> None:
    first = compile_greal_candidate(candidate_input())
    second = compile_greal_candidate(candidate_input())
    assert tuple(first.fields) == REQUIRED_GREAL_FIELDS
    assert len(first.fields) == 29
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.candidate_id.endswith(first.bundle_sha256)
    assert first.fields["atomic_freeze_receipt_candidate"]["atomic"] is True
    assert first.fields["atomic_freeze_receipt_candidate"]["protected_outcomes_accessed"] is False
    assert first.fields["atomic_freeze_receipt_candidate"]["real_study_frozen"] is False
    assert first.status == "REAL_SCIENTIFIC_PREREG_READY_CANDIDATE_ONLY"
    assert first.scientific_forecastability == "NOT_EVALUATED"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["candidate_id"] == first.candidate_id
    assert manifest["bundle_sha256"] == first.bundle_sha256
    assert manifest["explicit_field_count"] == len(first.fields)
    assert manifest["preregistration_bundle_id"] == first.preregistration_bundle_id
    assert manifest["atomic_freeze_receipt_candidate"] == first.fields["atomic_freeze_receipt_candidate"]


def test_readiness_fails_closed_for_missing_default_outcome_access_or_review_block() -> None:
    fields = candidate_input(); del fields["rollback"]
    with pytest.raises(SFFContractError, match="MISSING"):
        compile_greal_candidate(fields)
    fields = candidate_input(); fields["materiality_rule"] = "TBD"
    with pytest.raises(SFFContractError, match="UNRESOLVED"):
        compile_greal_candidate(fields)
    fields = candidate_input(); fields["no_outcome_access_embargo_proof"]["protected_outcomes_accessed"] = True
    with pytest.raises(SFFContractError, match="EMBARGO"):
        compile_greal_candidate(fields)
    fields = candidate_input(); fields["independent_reviewer_binding"]["decision"] = "BLOCK"
    with pytest.raises(SFFContractError, match="REVIEW"):
        compile_greal_candidate(fields)
