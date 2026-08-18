from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.canonical import canonical_json_bytes
from ovc.research_operations.p1cdi.bootstrap import (
    BOOTSTRAP_OBJECT_TYPES,
    BOOTSTRAP_SOURCE_ROOTS,
    BootstrapCensusError,
    build_historical_membership_events,
    freeze_source_census,
    reconcile_source_census,
    scan_repository_source_subjects,
)
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import (
    load_json,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = load_json(
    "fixtures/research_operations/p1cdi/P1CDII_WP3_BOOTSTRAP_FIXTURES_v0_1.json"
)
BASE_COMMIT = "35d3dc736d5b16b3113a89cc1733a9c75bafd139"


def _write_fixture_repository(root: Path) -> None:
    for item in FIXTURE["owner_record_documents"] + FIXTURE["excluded_documents"]:
        path = root / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(item["document"]))


def _frozen_fixture_census(tmp_path: Path) -> dict:
    _write_fixture_repository(tmp_path)
    subjects = scan_repository_source_subjects(tmp_path)
    return freeze_source_census(
        census_id="P1CDI-G0-SOURCE-CENSUS:fixture:v0.1",
        as_of_commit=BASE_COMMIT,
        subjects=subjects,
    )


def _reconciled_fixture_subjects(census: dict) -> list[dict]:
    expected = {
        item["path"]: item["expected_disposition"]
        for item in FIXTURE["owner_record_documents"]
    }
    result = copy.deepcopy(census["subjects"])
    for subject in result:
        path = subject["source_locator"].split("#", 1)[0]
        subject["migration_disposition"] = expected[path]
    return result


def test_registry_closes_exact_owner_roots_and_dmrp_types() -> None:
    registry = load_json("registries/research_operations/p1cdi/bootstrap_source_registry.json")
    dmrp = load_json("registries/research_operations/DMRP_OBJECT_TYPE_REGISTRY_v0_1.json")
    assert registry["status"] == "CLOSED"
    assert registry["authority_effect"] == "NONE"
    assert tuple(sorted(item["path"] for item in registry["source_roots"])) == BOOTSTRAP_SOURCE_ROOTS
    assert set(BOOTSTRAP_OBJECT_TYPES) <= set(dmrp["object_types"])
    assert registry["silent_omission"] == "FORBIDDEN"
    assert registry["summary_reconstruction"] == "FORBIDDEN"
    assert "fixtures/research_operations/ec1" in {
        item["path"] for item in registry["excluded_roots"]
    }


def test_exact_scan_includes_every_durable_subject_and_excludes_synthetic_and_summary(
    tmp_path: Path,
) -> None:
    census = _frozen_fixture_census(tmp_path)
    assert census["expected_subject_count"] == FIXTURE["expected_subject_count"]
    assert len(census["subjects"]) == FIXTURE["expected_subject_count"]
    locators = {item["source_locator"].split("#", 1)[0] for item in census["subjects"]}
    assert locators == {item["path"] for item in FIXTURE["owner_record_documents"]}
    assert all(item["migration_disposition"] == "PENDING" for item in census["subjects"])
    duplicate_hashes = [
        item["source_sha256"]
        for item in census["subjects"]
        if "study_a" in item["source_locator"]
    ]
    assert len(duplicate_hashes) == 2
    assert len(set(duplicate_hashes)) == 1
    assert len({item["subject_id"] for item in census["subjects"]}) == len(census["subjects"])


def test_nested_explicit_source_objects_are_not_silently_omitted(tmp_path: Path) -> None:
    path = tmp_path / "records/research_operations/ec1/cycle.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        canonical_json_bytes(
            {
                "record_type": "EvidenceCycleGeneration",
                "results": [
                    {
                        "object_type": "P1DiscoveryResult",
                        "source_generation": "ec1:cycle:1",
                        "dmrp_conformance_class": "DMRP_CONFORMANT",
                        "visibility_state": "PATH1_SAFE",
                        "currentness_state": "HISTORICAL",
                    }
                ],
            }
        )
    )
    subjects = scan_repository_source_subjects(tmp_path)
    assert len(subjects) == 1
    assert subjects[0]["source_locator"].endswith("#/results/0")


def test_reconciliation_is_exact_complete_and_source_faithful(tmp_path: Path) -> None:
    census = _frozen_fixture_census(tmp_path)
    reconciled = _reconciled_fixture_subjects(census)
    completeness = reconcile_source_census(
        manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:fixture:v0.1",
        census=census,
        subjects=reconciled,
    )
    assert completeness["complete"] is True
    assert completeness["expected_subject_count"] == FIXTURE["expected_subject_count"]
    assert completeness["reconciled_subject_count"] == FIXTURE["expected_subject_count"]
    assert {
        item["migration_disposition"] for item in completeness["subjects"]
    } == {"MIGRATED", "EXACT_DUPLICATE", "VISIBILITY_BLOCKED"}
    frozen = {item["subject_id"]: item for item in census["subjects"]}
    for result in completeness["subjects"]:
        original = frozen[result["subject_id"]]
        assert {
            key: value for key, value in result.items() if key != "migration_disposition"
        } == {
            key: value for key, value in original.items() if key != "migration_disposition"
        }


@pytest.mark.parametrize("mutation", ["omit", "add", "source_hash", "pending"])
def test_reconciliation_fails_closed_on_omission_extra_mutation_or_pending(
    tmp_path: Path, mutation: str
) -> None:
    census = _frozen_fixture_census(tmp_path)
    reconciled = _reconciled_fixture_subjects(census)
    if mutation == "omit":
        reconciled.pop()
    elif mutation == "add":
        extra = copy.deepcopy(reconciled[0])
        extra["subject_id"] = "p1cdi:bootstrap-source:extra"
        extra["source_locator"] = "records/research_operations/ec1/extra.json#/"
        reconciled.append(extra)
    elif mutation == "source_hash":
        reconciled[0]["source_sha256"] = "f" * 64
    else:
        reconciled[0]["migration_disposition"] = "PENDING"
    with pytest.raises(BootstrapCensusError):
        reconcile_source_census(
            manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:invalid:v0.1",
            census=census,
            subjects=reconciled,
        )


def test_generation_zero_membership_is_historical_only_and_exactly_bound(tmp_path: Path) -> None:
    census = _frozen_fixture_census(tmp_path)
    completeness = reconcile_source_census(
        manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:fixture:v0.1",
        census=census,
        subjects=_reconciled_fixture_subjects(census),
    )
    migrated_ids = [
        item["subject_id"]
        for item in completeness["subjects"]
        if item["migration_disposition"] == "MIGRATED"
    ]
    bindings = {subject_id: f"p1:generation:{index}" for index, subject_id in enumerate(migrated_ids)}
    events = build_historical_membership_events(
        completeness=completeness,
        generation_by_subject=bindings,
        effective_time="2026-08-18T00:00:00Z",
    )
    assert len(events) == FIXTURE["expected_historical_event_count"]
    assert {event["activity_state"] for event in events} == {"HISTORICAL"}
    assert all(event["authority_effect"] == "NONE" for event in events)
    lifecycle_schema = load_json(
        "schemas/research_operations/p1cdi/p1cdi_lifecycle_currentness_v0_1.schema.json"
    )
    for event in events:
        validate_contract(lifecycle_schema, event)
    with pytest.raises(BootstrapCensusError):
        build_historical_membership_events(
            completeness=completeness,
            generation_by_subject={},
            effective_time="2026-08-18T00:00:00Z",
        )


def test_clean_rebuild_is_byte_deterministic(tmp_path: Path) -> None:
    first = _frozen_fixture_census(tmp_path)
    second = _frozen_fixture_census(tmp_path)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    first_complete = reconcile_source_census(
        manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:fixture:v0.1",
        census=first,
        subjects=_reconciled_fixture_subjects(first),
    )
    second_complete = reconcile_source_census(
        manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:fixture:v0.1",
        census=second,
        subjects=_reconciled_fixture_subjects(second),
    )
    assert canonical_json_bytes(first_complete) == canonical_json_bytes(second_complete)


def test_two_clean_repository_processes_reproduce_exact_frozen_outputs() -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts/research_operations/run_p1cdii_wp3_bootstrap.py"),
    ]
    env = {**os.environ, "PYTHONHASHSEED": "random"}
    first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, env=env).stdout
    second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, env=env).stdout
    assert first == second
    assert first.decode().strip() == (
        "9f26d49a79bef2b703ce5c866039c8bb38ab7a7d9d072cf1cf9fb82b159a79c9"
    )


def test_lawful_main_freeze_and_completeness_are_exact_zero_member_rebuild() -> None:
    frozen = load_json(
        "records/research_operations/p1cdi/P1CDI_BOOTSTRAP_SOURCE_CENSUS_MANIFEST_v0_2.json"
    )
    completeness = load_json(
        "records/research_operations/p1cdi/P1CDI_BOOTSTRAP_SOURCE_COMPLETENESS_MANIFEST_v0_1.json"
    )
    rebuilt = freeze_source_census(
        census_id=frozen["census_id"],
        as_of_commit=frozen["as_of_commit"],
        subjects=scan_repository_source_subjects(ROOT),
    )
    rebuilt_complete = reconcile_source_census(
        manifest_id=completeness["manifest_id"],
        census=rebuilt,
        subjects=[],
    )
    assert rebuilt == frozen
    assert rebuilt_complete == completeness
    assert frozen["as_of_commit"] == BASE_COMMIT
    assert frozen["expected_subject_count"] == 0
    assert completeness["complete"] is True
    bootstrap_schema = load_json(
        "schemas/research_operations/p1cdi/p1cdi_bootstrap_v0_1.schema.json"
    )
    validate_contract(bootstrap_schema, frozen)
    validate_contract(bootstrap_schema, completeness)


def test_wp3_delegated_pass_is_conditioned_on_exact_final_integration() -> None:
    implementation = load_json(
        "docs/programmes/p1cdi-v0-1/wp3/P1CDII_WP3_IMPLEMENTATION_PACKET_v0_1.json"
    )
    qa = load_json("docs/programmes/p1cdi-v0-1/wp3/P1CDII_WP3_QA_PACKET_v0_1.json")
    decision = load_json(
        "docs/programmes/p1cdi-v0-1/wp3/P1CDII_G3_DELEGATED_DECISION_v0_1.json"
    )
    state = load_json("records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json")
    assert implementation["authority"]["authority_delta"] == "NONE"
    assert implementation["source_census"]["recognized_admissible_source_subjects"] == 0
    assert implementation["source_census"]["complete"] is True
    assert implementation["historical_current_separation"]["automatic_current_publication"] == "DENIED"
    assert qa["status"] == "PASS_PENDING_EXACT_FINAL_INTEGRATION"
    assert qa["g3_decision"] == "PASS_PENDING_EXACT_FINAL_INTEGRATION"
    assert qa["wp4_authorised_after_exact_final_integration"] is True
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "NONE"
    assert decision["integration_condition"] == (
        "EXACT_FINAL_REQUIRED_CI_PRVITR_VIT_GRT_SIQ_READY_PASS"
    )
    assert decision["operational_current_pointer_publication"] == "DENIED_SEPARATELY_GOVERNED"
    assert state["current_packet"] == "P1CDII-WP3"
    assert state["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-WP3"]["status"] == "COMPLETED"
    assert state["next_packet"] == "P1CDII-WP4"
    validate_contract(
        load_json("schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json"),
        state,
    )
