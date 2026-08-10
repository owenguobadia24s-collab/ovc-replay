from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "docs/releases/external-artifact-capacity-ownership-v0-1"
V09 = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_CAPACITY_EXCEEDED_EXTERNAL_BYTES.json"


def _j(path: Path):
    return json.loads(path.read_text())


def test_eacr_g0_is_bounded_and_non_scientific():
    decision = _j(REL / "EACR_G0_OPERATOR_DECISION.json")
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "BOUNDED_REPOSITORY_REMEDIATION_ONLY"
    assert "benchmark execution" in decision["explicit_exclusions"]
    assert "scientific method change" in decision["explicit_exclusions"]


def test_shared_infrastructure_is_upstream_of_srfd_execution_binding():
    crosswalk = _j(REL / "EACR_OWNERSHIP_CROSSWALK.json")
    assert crosswalk["dependency_direction"] == "SHARED_EVIDENCE_INFRASTRUCTURE -> PROGRAMME_EXECUTION_PROFILE"
    by_capability = {row["capability"]: row for row in crosswalk["classifications"]}
    assert by_capability["deterministic content-addressed chunk/compress/store/read-back verification"]["owner"] == "SHARED_EVIDENCE_INFRASTRUCTURE"
    assert by_capability["SRFD representation/segmentation/distance/family/sensitivity scientific experiment"]["owner"] == "SRFD"
    assert by_capability["SRFD run authority and token consumption"]["owner"] == "SRFD_GOVERNANCE"


def test_v09_failure_remains_blocked_and_historical():
    failure = _j(V09)
    assert failure["status"] == "BLOCKED_PRESERVED_NOT_COMPLETED"
    assert failure["work_units"]["completed_unit_count"] == 1626
    assert failure["work_units"]["remaining_unit_count"] == 394
    assert failure["authority"]["token_state"] == "CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN"
    assert "MUST_NOT_BE_RELABELED" in failure["checkpoint_lineage"]["preservation_rule"]
