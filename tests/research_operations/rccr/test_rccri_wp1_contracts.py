import json
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.research_operations.rccr.core import (
    FAMILIES,
    RCCRAppendOnlyCollision,
    RCCRAppendOnlyStore,
    RCCRValidationError,
    canonical_json_bytes,
    logical_identity,
    validate_canonical_object,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = json.loads((ROOT / "fixtures/research_operations/rccr/v0_1/RCCRI_WP1_COMPACT_FIXTURES.json").read_text())["fixtures"]


def test_all_seven_schemas_are_closed_and_fixtures_validate():
    assert set(FAMILIES) == set(FIXTURES)
    for family in FAMILIES:
        schema = json.loads((ROOT / f"schemas/research_operations/rccr/v0_1/{family}.schema.json").read_text())
        assert schema["additionalProperties"] is False
        validate_canonical_object(family, FIXTURES[family])
        assert FIXTURES[family]["authority_effect"] == "NONE"


def test_canonical_hash_is_restart_and_cross_order_stable():
    original = FIXTURES["ResearchCoverageItem"]
    reversed_order = dict(reversed(list(original.items())))
    assert canonical_json_bytes(original) == canonical_json_bytes(reversed_order)
    assert logical_identity("ResearchCoverageItem", original) == logical_identity("ResearchCoverageItem", reversed_order)


def test_unknown_mandatory_enum_and_unknown_field_fail_closed():
    bad = deepcopy(FIXTURES["ResearchCoverageAssessment"])
    bad["coverage_status"] = "MAYBE"
    with pytest.raises(RCCRValidationError, match="UNKNOWN_MANDATORY_ENUM"):
        validate_canonical_object("ResearchCoverageAssessment", bad)
    bad = deepcopy(FIXTURES["RCCRRefreshTrigger"])
    bad["surprise"] = True
    with pytest.raises(RCCRValidationError, match="SCHEMA_CLOSED"):
        validate_canonical_object("RCCRRefreshTrigger", bad)


def test_authority_and_path_payload_leakage_fail_closed():
    bad = deepcopy(FIXTURES["ResearchCoverageItem"])
    bad["authority_effect"] = "ACTIVATE"
    with pytest.raises(RCCRValidationError):
        validate_canonical_object("ResearchCoverageItem", bad, require_identity=False)
    bad = deepcopy(FIXTURES["ResearchCoverageItem"])
    bad["source"]["source_artifact_ref"] = "../../secret"
    with pytest.raises(RCCRValidationError, match="PATH_TRAVERSAL"):
        validate_canonical_object("ResearchCoverageItem", bad, require_identity=False)


def test_append_only_collision_and_audit(tmp_path):
    observed = []
    store = RCCRAppendOnlyStore(tmp_path, audit_callback=observed.append)
    record = FIXTURES["ResearchCoverageItem"]
    path = store.write("ResearchCoverageItem", record)
    assert json.loads(path.read_text()) == record
    assert observed[0]["authority_effect"] == "NONE"
    assert len(list((tmp_path / "audit").glob("*.json"))) == 1
    with pytest.raises(RCCRAppendOnlyCollision):
        store.write("ResearchCoverageItem", record)


def test_supersession_requires_explicit_predecessor(tmp_path):
    store = RCCRAppendOnlyStore(tmp_path)
    predecessor = FIXTURES["ResearchCoverageAssessment"]
    store.write("ResearchCoverageAssessment", predecessor)
    successor = deepcopy(predecessor)
    successor["supersedes_assessment_id"] = predecessor["coverage_assessment_id"]
    successor["coverage_status"] = "PARTIAL"
    successor["coverage_assessment_id"] = logical_identity("ResearchCoverageAssessment", successor)
    store.supersede("ResearchCoverageAssessment", predecessor, successor, supersession_field="supersedes_assessment_id")
    bad = deepcopy(successor)
    bad["supersedes_assessment_id"] = "wrong"
    bad["coverage_assessment_id"] = logical_identity("ResearchCoverageAssessment", bad)
    with pytest.raises(RCCRValidationError, match="SUPERSESSION_LINEAGE_REQUIRED"):
        store.supersede("ResearchCoverageAssessment", predecessor, bad, supersession_field="supersedes_assessment_id")
