import json
from pathlib import Path
import copy

from ovc.opt_b.c2e_v2.handoff import build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


def test_quality_is_orthogonal_not_structural():
    payload = json.loads(FIXTURE.read_text())
    payload["diagnostic_namespace"] = {"quality_evidence": {"status": "ASSURED", "component_id": "QUALITY.001"}}
    frame = build_input_frame(copy.deepcopy(payload))
    assert set(key for key in frame["structural"] if key.endswith("_record_ids")) >= {
        "location_record_ids", "motion_record_ids", "organisation_record_ids", "interaction_record_ids"
    }
    assert "QUALITY" not in frame["structural"]
    assert frame["diagnostic_namespace"]["quality_evidence"]["status"] == "ASSURED"


def test_missing_optional_parent_does_not_globally_invalidate_local_frame():
    payload = json.loads(FIXTURE.read_text())
    remove_ids = {"CTX.001", "PARENT.FIXED.001", "PARENT.STRUCT.001", "PARENT.AXIS.001"}
    payload["parent_records"] = [row for row in payload["parent_records"] if row["record_id"] not in remove_ids]
    payload["lineage"]["parent_record_ids"] = [item for item in payload["lineage"]["parent_record_ids"] if item not in remove_ids]
    payload["context"] = {"context_resolution_bundle_id": None, "fixed_parent_links": [], "structural_object_links": [], "parent_axis_links": []}
    payload["evidence"]["dependency_results"][1] = {
        "dependency_id":"DEP.PARENT","role":"OPTIONAL","status":"NOT_COMPUTABLE","source_record_ids":[],"reason_codes":["AVAIL_REQUIRED_PARENT_MISSING"]
    }
    frame = build_input_frame(payload)
    assert frame["evidence"]["technical_status"] == "COMPUTABLE"
    assert frame["context"]["context_resolution_bundle_id"] is None
