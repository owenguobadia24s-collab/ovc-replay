from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from ovc.development.identity import canonical_json_bytes
from ovc.shared_systems.ro_dmrp_shadow import (
    RODMRPShadowAdapterBinding,
    RODMRPShadowError,
    RODMRPSharedSystemsConsumptionManifest,
    adapt_ro_record,
    build_read_only_artifact_binding,
    build_ro_evidence_frontier,
    compare_ro_dual_run,
    crosswalk_ro_state,
    evaluate_ro_adapter_complexity,
    inspect_read_only_artifacts,
    unwrap_ro_record,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / (
    "fixtures/shared_systems/ro_dmrp_shadow/"
    "SHSI_WP8_RO_DMRP_HISTORICAL_SHADOW_FIXTURE_v0_1.json"
)
BUDGET_PATH = ROOT / (
    "registries/implementation/shared_systems_v0_1/"
    "SHSI_PILOT_ACCEPTANCE_BUDGET_v0_1.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


FIXTURE = load(FIXTURE_PATH)


def manifest() -> RODMRPSharedSystemsConsumptionManifest:
    return RODMRPSharedSystemsConsumptionManifest(
        "SHSI-WP8-RO-DMRP-CONSUME-v0.1",
        FIXTURE["programme_id"],
        "DMRPI-GREAL-EC1",
        "SHSI-WP6-FOUNDATION-v0.1",
        FIXTURE["current_state"]["path"],
        FIXTURE["current_state"]["git_blob_sha"],
        tuple(FIXTURE["owner_provider_refs"]),
        tuple(FIXTURE["owner_source_refs"]),
        tuple(FIXTURE["owner_research_roles"]),
        tuple(FIXTURE["owner_provider_refs"]),
        tuple(FIXTURE["owner_source_refs"]),
        tuple(FIXTURE["owner_research_roles"]),
    )


def adapter() -> RODMRPShadowAdapterBinding:
    return RODMRPShadowAdapterBinding(
        "SHSI-WP8-RO-DMRP-WRAP-v0.1",
        "ovc-dmrp-wp1-synthetic-fixtures/v1",
        "ovc://shared-systems/ro-dmrp/shadow/v0.1",
    )


def test_historical_owner_records_are_exact_lawful_git_blobs() -> None:
    for item in [*FIXTURE["sources"], FIXTURE["current_state"], FIXTURE["current_pointer"]]:
        path = ROOT / item["path"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert len(raw) == item["byte_count"]
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"]


def test_consumption_is_read_only_shadow_and_cannot_add_owner_facts() -> None:
    row = manifest()
    assert row.access_mode == "READ_ONLY" and row.status == "SHADOW_ONLY"
    assert not row.current_binding_changed and not row.artifact_store_created
    assert row.writes_performed == () and row.authority_effect == "NONE"
    with pytest.raises(RODMRPShadowError, match="UNOWNED_PROVIDER_ADDITION"):
        replace(row, consumed_provider_refs=("REPOSITORY_GIT", "NEW_PROVIDER"))
    with pytest.raises(RODMRPShadowError, match="UNOWNED_SOURCE_ADDITION"):
        replace(row, consumed_source_refs=(*row.consumed_source_refs, "new/source"))
    with pytest.raises(RODMRPShadowError, match="UNOWNED_RESEARCH_ROLE_ADDITION"):
        replace(row, consumed_research_roles=("DISCOVERY", "VALIDATION"))
    with pytest.raises(RODMRPShadowError, match="WRITE_ACTIVATION_OR_STORE"):
        replace(row, writes_performed=("APPEND_RESEARCH_OPERATIONS",))
    with pytest.raises(RODMRPShadowError, match="WRITE_ACTIVATION_OR_STORE"):
        replace(row, artifact_store_created=True)


def test_frozen_is_lifecycle_only_and_never_authority() -> None:
    crosswalk, vector = crosswalk_ro_state(
        "SHSI-WP8-RO-FROZEN-CROSSWALK-v0.1",
        lifecycle_state="FROZEN",
        authority_state="FROZEN",
    )
    assert crosswalk.shared_lifecycle_state == "FROZEN"
    assert crosswalk.shared_authority_state == "UNKNOWN"
    assert vector.value("LIFECYCLE", "RESEARCH_OPERATIONS").owner_state == "FROZEN"
    assert vector.authority("RESEARCH_OPERATIONS") == "UNKNOWN"
    with pytest.raises(RODMRPShadowError, match="FROZEN_AS_AUTHORITY"):
        replace(crosswalk, shared_authority_state="FROZEN")
    with pytest.raises(RODMRPShadowError, match="AUTHORITY_DECISION_REF_REQUIRED"):
        replace(crosswalk, owner_lifecycle_state="COMPLETED", shared_lifecycle_state="COMPLETED", shared_authority_state="AUTHORISED_BOUNDED")


def test_synthetic_evidence_frontier_preserves_identity_and_missing_fails_closed() -> None:
    source = load(ROOT / FIXTURE["sources"][0]["path"])
    evaluation = build_ro_evidence_frontier(
        "SHSI-WP8-RO-EVIDENCE-v0.1",
        source,
        source_generation="SYNTH.DMRP.WP1.G1",
        evaluation_cutoff="2026-08-22T00:00:00Z",
        dependency_manifest_ref="SHSI-WP8-RO-DEPENDENCIES-v0.1",
    )
    assert evaluation.status == "READY" and not evaluation.frontier.missing_entries
    assert len(evaluation.record_identity_refs) == len(source["fixtures"]) == 3
    stripped = {**source, "fixtures": source["fixtures"][:-1]}
    missing = build_ro_evidence_frontier(
        "SHSI-WP8-RO-EVIDENCE-MISSING-v0.1",
        stripped,
        source_generation="SYNTH.DMRP.WP1.G1",
        evaluation_cutoff="2026-08-22T00:00:00Z",
        dependency_manifest_ref="SHSI-WP8-RO-DEPENDENCIES-v0.1",
    )
    assert missing.status == "NOT_EVALUABLE"
    assert missing.frontier.missing_entries == ("RESEARCH_QUESTION_RECORD",)
    assert missing.reason_codes == ("REQUIRED_RECORD_MISSING",)
    with pytest.raises(RODMRPShadowError, match="NON_SYNTHETIC_FIXTURE"):
        build_ro_evidence_frontier(
            "BAD",
            {**source, "status": "REAL"},
            source_generation="SYNTH.DMRP.WP1.G1",
            evaluation_cutoff="2026-08-22T00:00:00Z",
            dependency_manifest_ref="SHSI-WP8-RO-DEPENDENCIES-v0.1",
        )


def test_repository_artifacts_are_reachable_without_external_fetch_or_store() -> None:
    bindings = []
    available = {}
    for index, item in enumerate(FIXTURE["sources"], start=1):
        raw = (ROOT / item["path"]).read_bytes()
        binding = build_read_only_artifact_binding(
            f"SHSI-WP8-RO-ARTIFACT-{index}", item["path"], raw
        )
        bindings.append(binding)
        available[binding.descriptor.artifact_ref] = raw
        assert not binding.external_artifact_fetch_performed
        assert not binding.artifact_store_created and binding.writes_performed == ()
    reachable = inspect_read_only_artifacts("SHSI-WP8-REACH-v0.1", bindings, available)
    assert reachable.status == "REACHABLE"
    assert all(item.status == "PRESENT_VERIFIED" for item in reachable.observations)
    missing = inspect_read_only_artifacts(
        "SHSI-WP8-REACH-MISSING-v0.1", bindings, {next(iter(available)): next(iter(available.values()))}
    )
    assert missing.status == "GAPPED"
    assert any(item.status == "MISSING" for item in missing.observations)
    corrupt = dict(available)
    corrupt[bindings[0].descriptor.artifact_ref] += b"corrupt"
    mismatch = inspect_read_only_artifacts("SHSI-WP8-REACH-BAD-v0.1", bindings, corrupt)
    assert mismatch.status == "GAPPED"
    assert mismatch.observations[0].status == "HASH_MISMATCH"


def test_shadow_adapter_round_trip_dual_run_and_budget() -> None:
    source = load(ROOT / FIXTURE["sources"][0]["path"])
    binding = adapter()
    wrapped = adapt_ro_record(binding, source)
    shadow = unwrap_ro_record(binding, wrapped)
    assert shadow == source
    assert wrapped["source_logical_sha256"] != wrapped["logical_id"]
    comparison = compare_ro_dual_run("SHSI-WP8-RO-DUAL-v0.1", source, shadow)
    assert comparison.status == "PASS" and not comparison.divergent
    changed = {**shadow, "market_authority": "FABRICATED"}
    assert compare_ro_dual_run("BAD", source, changed).status == "BLOCK"
    with pytest.raises(RODMRPShadowError, match="NON_IDENTITY_MAPPING"):
        replace(binding, field_mapping=(("fixtures", "evidence"),))
    with pytest.raises(RODMRPShadowError, match="SEMANTIC_FABRICATION"):
        replace(binding, semantic_inventions=("authority",))

    import ovc.shared_systems.ro_dmrp_shadow as module

    source_text = Path(inspect.getsourcefile(module.adapt_ro_record)).read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "adapt_ro_record"
    )
    code_lines = node.end_lineno - node.lineno + 1
    byte_delta = max(0, len(canonical_json_bytes(wrapped)) - len(canonical_json_bytes(source)))
    budget = load(BUDGET_PATH)["pilot_acceptance_budget"]
    ledger = evaluate_ro_adapter_complexity(
        "SHSI-WP8-RO-LEDGER-v0.1",
        binding,
        budget=budget,
        code_surface_lines=code_lines,
        artifact_byte_delta=byte_delta,
    )
    assert ledger.status == "PASS"
    assert ledger.active_adapter_count == 0 and ledger.adapter_mapping_count == 1
    blocked = evaluate_ro_adapter_complexity(
        "SHSI-WP8-RO-LEDGER-BAD",
        binding,
        budget=budget,
        code_surface_lines=code_lines,
        artifact_byte_delta=byte_delta,
        incident_contribution_count=1,
    )
    assert blocked.status == "BLOCK"
    assert blocked.exceeded_dimensions == ("ADAPTER_INCIDENT_CONTRIBUTION_COUNT",)


def test_wp8_schema_declares_every_shadow_object_and_validation_stays_locked() -> None:
    schema = load(ROOT / "schemas/shared_systems/ro_dmrp_shadow_consumer_v0_1.schema.json")
    expected = {
        "RODMRPSharedSystemsConsumptionManifest",
        "RODMRPStatePlaneCrosswalk",
        "RODMRPEvidenceEvaluation",
        "RODMRPReadOnlyArtifactBinding",
        "RODMRPShadowAdapterBinding",
        "RODMRPDualRunComparison",
        "RODMRPAdapterComplexityLedger",
    }
    assert expected <= set(schema["$defs"])
    assert FIXTURE["constraints"]["validation"] == "LOCKED_UNCONSUMED"
    assert FIXTURE["constraints"]["external_artifact_fetch"] is False
    assert FIXTURE["constraints"]["authority_effect"] == "NONE"
