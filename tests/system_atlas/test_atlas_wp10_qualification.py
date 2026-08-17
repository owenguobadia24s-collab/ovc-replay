from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas import (
    AtlasQualificationError,
    build_exact_git_shadow_graph,
    build_qualification_report,
    build_reference_generation,
    canonical_sha256,
    evaluate_operational_budget,
    evaluate_retention_budget,
    materialize_generation,
    measure_operational_profile,
    prove_exact_current_publication_shadow,
    scan_retention_inventory,
    validate_live_shadow_binding,
)
from ovc.system_atlas.registries import load_registry_bundle


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas/system_atlas"
GRAPH = ROOT / "fixtures/system_atlas/wp1/ATLAS_WP1_SYNTHETIC_GRAPH_v0_1.json"
CASES = ROOT / "fixtures/system_atlas/wp10/ATLAS_WP10_QUALIFICATION_CASES_v0_1.json"
SHADOW = ROOT / "fixtures/system_atlas/wp10/ATLAS_WP10_LIVE_CURRENT_SHADOW_BINDING_v0_1.json"
OPERATIONAL = ROOT / "registries/system_atlas/ATLAS_OPERATIONAL_BUDGET_v0_1.json"
RETENTION = ROOT / "registries/system_atlas/ATLAS_RETENTION_BUDGET_v0_1.json"
WP10 = ROOT / "docs/programmes/system-atlas-v0-1/wp10"
EXTERNAL_EVIDENCE = ROOT.parent.parent / "ovc-replay-external-artifacts/system_atlas/generations/wp10/ATLAS_WP10_Q0_Q6_EVIDENCE.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inline_local_refs(node, root):
    if isinstance(node, list):
        return [inline_local_refs(item, root) for item in node]
    if not isinstance(node, dict):
        return node
    if set(node) == {"$ref"} and node["$ref"].startswith("#/"):
        target = root
        for part in node["$ref"][2:].split("/"):
            target = target[part]
        return inline_local_refs(target, root)
    return {key: inline_local_refs(value, root) for key, value in node.items()}


def validate(document: dict, schema_name: str) -> None:
    schema = load(SCHEMAS / schema_name)
    validate_against_schema(document, inline_local_refs(schema, schema))


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def current_shadow_graph() -> tuple[dict, dict]:
    source = load(GRAPH)
    registries = load_registry_bundle(ROOT)
    binding = load(SHADOW)
    graph = build_exact_git_shadow_graph(
        source,
        registries,
        repository_root=ROOT,
        repository_commit=binding["source_commit"],
        repository_tree=binding["source_tree"],
        graph_id="atlas:graph:wp10-exact-current-publication.v0.1",
        generation_id=f"atlas:generation:wp10-live-shadow:{binding['source_commit']}",
        completeness_profile="ATLAS_WP10_EXACT_CURRENT_PUBLICATION_MECHANISM_SHADOW",
    )
    return graph, registries


def test_wp10_budget_registries_and_live_shadow_binding_are_schema_valid() -> None:
    validate(load(OPERATIONAL), "atlas_operational_budget_v0_1.schema.json")
    validate(load(RETENTION), "atlas_retention_budget_v0_1.schema.json")
    binding = load(SHADOW)
    validate(binding, "atlas_live_shadow_binding_v0_1.schema.json")
    receipt = validate_live_shadow_binding(binding, ROOT)
    assert receipt["result"] == "PASS_EXACT_GIT_TREE_LIVE_SHADOW"
    assert receipt["source_binding_count"] == 34
    assert binding["source_commit"] == git("rev-parse", "f8711a2fa0d643c87abb45a0985bf526c0f9915a")
    assert binding["source_tree"] == git("rev-parse", "f8711a2fa0d643c87abb45a0985bf526c0f9915a^{tree}")
    c2p = next(row for row in binding["source_bindings"] if row["node_id"] == "c2p")
    assert c2p["path"] == "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_1.json"
    research = next(row for row in binding["source_bindings"] if row["node_id"] == "research")
    assert research["path"] == "records/research_operations/ec1/prsc/PRSCI_PROGRAMME_STATE_v0_1.json"


def test_operational_budget_passes_complete_observations_and_fails_typed_without_sampling() -> None:
    budget = load(OPERATIONAL)
    observations = {
        "environment": "windows",
        "measurements": {name: 0 for name in budget["required_dimensions"]},
    }
    passed = evaluate_operational_budget(budget, observations)
    validate(passed, "atlas_operational_budget_receipt_v0_1.schema.json")
    assert passed["result"] == "PASS"
    exceeded = deepcopy(observations)
    exceeded["measurements"]["FULL_BUILD_MS"] = budget["limits"]["FULL_BUILD_MS"]["maximum"] + 1
    failed = evaluate_operational_budget(budget, exceeded)
    assert failed["result"] == "CAPACITY_EXCEEDED"
    assert failed["completeness"] == "INCOMPLETE_DEGRADED"
    assert failed["sampling"] == "FORBIDDEN_NOT_USED"
    assert failed["protected_security_evidence"] == "PRESERVED_NOT_DROPPED"
    with pytest.raises(AtlasQualificationError, match="OBSERVATIONS_INCOMPLETE"):
        evaluate_operational_budget(budget, {"environment": "windows", "measurements": {}})


def test_host_operational_measurement_covers_every_frozen_dimension(tmp_path: Path) -> None:
    graph, registries = current_shadow_graph()
    predecessor = build_reference_generation(load(GRAPH), registries)
    cases = load(CASES)
    observations, current = measure_operational_profile(
        graph,
        registries,
        predecessor_bundle=predecessor,
        working_directory=tmp_path / "runtime",
        ordinary_queries=cases["ordinary_queries"],
        analytical_queries=cases["analytical_queries"],
        browser_render_layout_ms=250,
        browser_bundle_growth_bytes=0,
        repository_root=ROOT,
    )
    assert observations["environment"] == ("windows" if os.name == "nt" else os.name)
    assert observations["reference_root_hash"] == observations["incremental_root_hash"] == current.root_hash
    receipt = evaluate_operational_budget(load(OPERATIONAL), observations)
    expected = "PASS" if os.name == "nt" else "CAPACITY_EXCEEDED"
    assert receipt["environment_result"] == expected
    assert receipt["result"] == expected
    if expected == "CAPACITY_EXCEEDED":
        assert receipt["completeness"] == "INCOMPLETE_DEGRADED"
        assert receipt["sampling"] == "FORBIDDEN_NOT_USED"
        assert receipt["protected_security_evidence"] == "PRESERVED_NOT_DROPPED"
    assert set(observations["measurements"]) == set(load(OPERATIONAL)["required_dimensions"])


def test_exact_current_publication_is_proven_only_in_isolated_shadow(tmp_path: Path) -> None:
    graph, registries = current_shadow_graph()
    bundle = build_reference_generation(graph, registries, repository_root=ROOT)
    binding = load(SHADOW)
    canonical_root = tmp_path / "canonical"
    canonical_pointer = canonical_root / "generations/CURRENT.json"
    canonical_pointer.parent.mkdir(parents=True)
    canonical_pointer.write_text('{"sentinel":"unchanged"}\n', encoding="utf-8")
    before = canonical_pointer.read_bytes()
    receipt = prove_exact_current_publication_shadow(
        bundle,
        tmp_path / "publication-shadow",
        current_main={"commit": binding["source_commit"], "tree": binding["source_tree"]},
        canonical_external_root=canonical_root,
    )
    validate(receipt, "atlas_exact_current_publication_shadow_receipt_v0_1.schema.json")
    assert receipt["result"] == "PASS_EXACT_CURRENT_SHADOW_ONLY"
    assert receipt["canonical_publication"] is False
    assert canonical_pointer.read_bytes() == before
    with pytest.raises(AtlasQualificationError, match="MUST_BE_ISOLATED"):
        prove_exact_current_publication_shadow(
            bundle,
            canonical_root,
            current_main={"commit": binding["source_commit"], "tree": binding["source_tree"]},
            canonical_external_root=canonical_root,
        )


def test_retention_budget_preserves_recovery_milestone_and_incident_evidence_report_only(tmp_path: Path) -> None:
    graph, registries = current_shadow_graph()
    predecessor = build_reference_generation(load(GRAPH), registries)
    current = build_reference_generation(graph, registries, predecessor_root_hash=predecessor.root_hash, repository_root=ROOT)
    materialize_generation(predecessor, tmp_path)
    materialize_generation(current, tmp_path)
    incident = tmp_path / "incidents/wp10/record.json"
    incident.parent.mkdir(parents=True)
    incident.write_text('{"status":"retained"}\n', encoding="utf-8")
    inventory = scan_retention_inventory(
        tmp_path,
        current_root_hash=current.root_hash,
        predecessor_root_hash=predecessor.root_hash,
        milestone_root_hashes=[predecessor.root_hash],
    )
    receipt = evaluate_retention_budget(load(RETENTION), inventory)
    validate(receipt, "atlas_retention_budget_receipt_v0_1.schema.json")
    assert receipt["result"] == "PASS"
    assert receipt["destructive_action_count"] == 0
    assert set(receipt["protected_root_hashes"]) == {current.root_hash, predecessor.root_hash}

    constrained = deepcopy(load(RETENTION))
    constrained["maximum_total_generation_bytes"] = 0
    failed = evaluate_retention_budget(constrained, inventory)
    assert failed["result"] == "CAPACITY_EXCEEDED_REPORT_ONLY"
    assert failed["destructive_action_count"] == 0


def test_q0_q6_pass_cannot_claim_qualification_before_independent_review() -> None:
    stages = {f"Q{number}": "PASS" for number in range(7)}
    operational = {"result": "PASS", "receipt_hash": "a" * 64}
    retention = {"result": "PASS", "receipt_hash": "b" * 64}
    pending = build_qualification_report(
        stages,
        live_shadow_receipt_hash="c" * 64,
        publication_receipt_hash="d" * 64,
        operational_receipt=operational,
        retention_receipt=retention,
        q6_ind_status="PENDING_ELIGIBLE_INDEPENDENT_REVIEW",
    )
    validate(pending, "atlas_qualification_report_v0_1.schema.json")
    assert pending["status"] == "ATLAS_Q0_Q6_PASS_Q6_IND_PENDING"
    assert pending["activation_eligibility"] == "INELIGIBLE_PENDING_Q6_IND"
    assert pending["activation_status"] == "NOT_ACTIVATED_OPERATOR_GATE_REQUIRED"
    assert pending["canonical_publication"] is False
    assert pending["write_authority"] == "ABSENT"

    independently_reviewed = build_qualification_report(
        stages,
        live_shadow_receipt_hash="c" * 64,
        publication_receipt_hash="d" * 64,
        operational_receipt=operational,
        retention_receipt=retention,
        q6_ind_status="PASS_ELIGIBLE_INDEPENDENT_REVIEW",
    )
    assert independently_reviewed["status"] == "ATLAS_IMPLEMENTED_QUALIFIED_LIVE_SHADOW"
    assert independently_reviewed["activation_status"] == "NOT_ACTIVATED_OPERATOR_GATE_REQUIRED"


def test_wp10_fixture_families_cover_ratified_zero_tolerance_and_historical_cases() -> None:
    cases = load(CASES)
    assert len(cases["zero_tolerance_families"]) == 11
    assert len(cases["permanent_fixture_families"]) == 17
    assert len(cases["historical_golden_cases"]) == 6
    assert cases["capacity_adversarial"]["required_failure"] == "CAPACITY_EXCEEDED"
    assert cases["capacity_adversarial"]["sampling"] == "FORBIDDEN"
    assert canonical_sha256(cases)


def test_wp10_gate_state_and_independent_review_closeout_preserve_activation_boundary() -> None:
    gate = load(WP10 / "ATLAS_G10_GATE_PACKET.json")
    qa = load(WP10 / "ATLAS_WP10_QA_PACKET.json")
    request = load(WP10 / "ATLAS_WP10_INDEPENDENT_REVIEW_REQUEST.json")
    review = load(WP10 / "ATLAS_WP10_INDEPENDENT_REVIEW_RECORD.json")
    binding = load(ROOT / "registries/system_atlas/ATLAS_INDEPENDENT_REVIEWER_BINDING_v0_1.json")
    activation = load(WP10 / "ATLAS_G_OBSERVABILITY_ACTIVATE_PACKET.json")
    authority = load(WP10 / "ATLAS_WP10_VIT_AUTHORITY_MANIFEST.json")
    dependency = load(WP10 / "ATLAS_WP10_VIT_DEPENDENCY_FRONTIER.json")
    state = load(ROOT / "registries/implementation/system_atlas_v0_1/ATLAS_PROGRAMME_STATE_v0_1.json")
    pointer = load(ROOT / "registries/implementation/system_atlas_v0_1/CURRENT_STATE_POINTER.json")
    policy = load(ROOT / "registries/system_atlas/ATLAS_GENERATION_POLICY_REGISTRY_v0_1.json")
    final_report = load(WP10 / "ATLAS_WP10_FINAL_QUALIFICATION_REPORT.json")
    if gate["decision"] == "NOT_YET_ELIGIBLE":
        assert gate["acceptance_results"]["Q6_IND"] == "PENDING_RENEWED_EXACT_CURRENT_SUBJECT_REVIEW"
        assert gate["terminal_state_claimed"] is False
        assert qa["qa_recommendation"] == "PASS_Q0_Q6_REQUEST_RENEWED_Q6_IND_DO_NOT_RATIFY_G10"
        assert request["status"] == "PENDING_RENEWED_EXACT_CURRENT_SUBJECT_REVIEW"
        assert request["review_output"]["decision"] == "PENDING"
        assert binding["status"] == "RENEWAL_REQUIRED_EXACT_CURRENT_SUBJECT"
        validate(final_report, "atlas_qualification_report_v0_1.schema.json")
        assert final_report["report_hash"] == canonical_sha256({key: value for key, value in final_report.items() if key != "report_hash"})
        assert final_report["status"] == "ATLAS_Q0_Q6_PASS_Q6_IND_PENDING"
        assert activation["status"] == "INELIGIBLE_PENDING_RENEWED_Q6_IND_AND_G10_INTEGRATION"
        assert state["status"] == pointer["status"] == "ATLAS_WP10_Q0_Q6_PASS_Q6_IND_PENDING"
        assert state["next_packet"] == pointer["next_packet"] == "ATLAS-WP10-Q6-IND"
        assert state["blockers"] == ["Q6_IND_ELIGIBLE_INDEPENDENT_PASS_REQUIRED"]
        assert not (ROOT.parent.parent / "ovc-replay-external-artifacts/system_atlas/generations/CURRENT.json").exists()
        return
    assert gate["decision"] == "PASS"
    assert gate["ratification_class"] == "DELEGATED_AUTO_RATIFICATION"
    assert gate["acceptance_results"]["Q6_IND"] == "PASS_ELIGIBLE_INDEPENDENT_REVIEW"
    assert gate["terminal_state_claimed"] is True
    assert qa["qa_recommendation"] == "PASS_Q6_IND_AUTO_RATIFY_G10_INTEGRATE_THEN_STOP_AT_OPERATOR_ACTIVATION_GATE"
    assert qa["blockers"] == []
    assert request["status"] == "COMPLETED_PASS"
    assert request["review_output"]["decision"] == "PASS_ELIGIBLE_INDEPENDENT_REVIEW"
    assert review["verdict"] == "PASS"
    assert review["blocking_findings"] == []
    assert all(row["result"] == "PASS" for row in review["scope_results"])
    assert binding["reviewer_role"] == "ELIGIBLE_INDEPENDENT_IMPLEMENTATION_STAGE_REVIEWER"
    assert binding["no_self_review"] is True
    assert binding["operator_substitution"] is False
    validate(final_report, "atlas_qualification_report_v0_1.schema.json")
    assert final_report["report_hash"] == canonical_sha256({key: value for key, value in final_report.items() if key != "report_hash"})
    assert final_report["status"] == "ATLAS_IMPLEMENTED_QUALIFIED_LIVE_SHADOW"
    assert activation["status"] == "GATE_READY_OPERATOR_REQUIRED_AFTER_G10_INTEGRATION"
    assert activation["operator_decision"] is None
    assert activation["operational_reliance"] == "DENIED_PENDING_OPERATOR_DECISION"
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert dependency["logical_id"] == canonical_sha256(dependency["payload"])
    assert state["status"] == pointer["status"] == "ATLAS_IMPLEMENTED_QUALIFIED_LIVE_SHADOW"
    assert state["next_packet"] == pointer["next_packet"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
    assert state["blockers"] == []
    assert policy["status"] == "FROZEN_ATLAS_G10"
    assert policy["retention"] == "FROZEN_ATLAS_RETENTION_BUDGET_REPORT_ONLY_NO_DELETE"
    assert not (ROOT.parent.parent / "ovc-replay-external-artifacts/system_atlas/generations/CURRENT.json").exists()


def test_wp10_external_evidence_matches_bound_hash_when_available() -> None:
    if EXTERNAL_EVIDENCE.is_file():
        import hashlib

        qa = load(WP10 / "ATLAS_WP10_QA_PACKET.json")
        assert hashlib.sha256(EXTERNAL_EVIDENCE.read_bytes()).hexdigest() == qa["external_evidence"]["sha256"]
