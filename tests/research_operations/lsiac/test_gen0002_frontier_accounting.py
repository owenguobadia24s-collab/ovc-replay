from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.lsiac.gen0002 import (
    EXPECTED_COREFERENCE_GROUPS,
    EXPECTED_FROZEN_PASSPORT_SET_SHA256,
    EXPECTED_PASSPORT_COUNT,
    EXPECTED_SUBJECT_COUNT,
    audit_frozen_passport_subject_identity,
)

ROOT = Path(__file__).resolve().parents[3]


def test_gen0002_reconstructs_exact_frozen_frontier_accounting() -> None:
    result = audit_frozen_passport_subject_identity(ROOT)
    assert result["frozen_source_passport_set_sha256"] == EXPECTED_FROZEN_PASSPORT_SET_SHA256
    assert result["passport_count"] == EXPECTED_PASSPORT_COUNT == 434
    assert result["subject_count"] == EXPECTED_SUBJECT_COUNT == 431
    assert result["source_bytes_changed"] is False
    assert result["scientific_disposition_changed"] is False
    assert result["scientific_accession_decisions"] == 0
    print("LSIAC_GEN0002_AUDIT_RESULT " + json.dumps(result, sort_keys=True, separators=(",", ":")))


def test_gen0002_exact_coreference_groups_are_exhaustive() -> None:
    result = audit_frozen_passport_subject_identity(ROOT)
    groups = {
        row["subject_id"]: row["passport_count"]
        for row in result["co_reference_groups"]
    }
    assert groups == EXPECTED_COREFERENCE_GROUPS
    assert result["multi_passport_subject_count"] == 3
    assert result["singleton_subject_count"] == 428

    by_subject = {row["subject_id"]: row["passport_ids"] for row in result["co_reference_groups"]}
    assert by_subject["OVC-MULTICLOCK-NONLINEAR-DYNAMICS-0005"] == ["D001-01", "D001-02"]
    assert by_subject["OVC-MULTICLOCK-PERSISTENCE-DWELL-0006"] == ["D002-01", "D002-02"]
    assert by_subject["OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER"] == ["B0415", "D011-00"]


def test_gen0002_is_accounting_repair_only() -> None:
    result = audit_frozen_passport_subject_identity(ROOT)
    forbidden = {
        "inheritance_role",
        "inheritance_roles",
        "retain_forward",
        "destination_binding_set",
        "architecture_effect_set",
        "surviving_statement",
        "scientific_promotion",
    }
    assert forbidden.isdisjoint(result)
    assert result["authority_effect"] == "NONE_ACCOUNTING_REPAIR_ONLY"
