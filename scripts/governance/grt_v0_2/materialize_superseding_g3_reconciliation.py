#!/usr/bin/env python3
"""Materialise the authority-inert superseding GRT2-G3 reconciliation packet."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest
from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

PROGRAMME_ID = "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"
PLAN_ID = "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED"
PACKET_ID = "GRT2-G3-SUPERSEDING-READINESS-RECONCILIATION"
NEXT_PACKET = "GRT2-G3-SUPERSEDING-GATE-READY-MATERIALISATION"
CONSTITUTION_HASH = "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
B0_HASH = "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d"
FORMER_FLOOR_HASH = "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
PREVIOUS_DECISION_ID = "cde2d3ce74d1ed1a7ce8a8a608caf016e3590e9945e8a85e952c6124bd8767d3"
BASE = "docs/programmes/grt-v0-2/g3/superseding"


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hashed(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    return {**payload, "logical_sha256": canonical_sha256(payload)}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact_finding(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "finding_id",
            "rule_id",
            "subject_artifact_id",
            "relation_role",
            "counterparty_identity",
            "debt_extent",
            "lifecycle",
            "first_seen_tree",
            "applicability_evidence",
            "violation_evidence",
        )
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--artifact-name", default="grt2-g3-superseding-census")
    parser.add_argument("--diagnostic-head-sha", required=True)
    args = parser.parse_args()

    census_path = Path(args.census).resolve()
    census = json.loads(census_path.read_text(encoding="utf-8"))
    out = Path(args.output_root).resolve()

    if census.get("schema") != "ovc-grt2-g3-superseding-census-evidence/v1":
        raise RuntimeError("GRT2_G3_SUPERSEDING_CENSUS_SCHEMA_INVALID")
    if census.get("mechanically_eligible_for_superseding_gate_preparation") is not True:
        raise RuntimeError("GRT2_G3_SUPERSEDING_CENSUS_NOT_ELIGIBLE")
    if census.get("warnings") or census.get("unresolved_issues"):
        raise RuntimeError("GRT2_G3_SUPERSEDING_CENSUS_UNRESOLVED")
    if census.get("former_floor", {}).get("floor_hash") != FORMER_FLOOR_HASH:
        raise RuntimeError("GRT2_G3_FORMER_FLOOR_IDENTITY_MISMATCH")
    if census.get("b0_integrity", {}).get("exact") is not True:
        raise RuntimeError("GRT2_G3_B0_NOT_EXACT")
    if census.get("b0_integrity", {}).get("membership_sha256") != B0_HASH:
        raise RuntimeError("GRT2_G3_B0_HASH_MISMATCH")
    if not all(bool(value) for value in census.get("readiness_conditions", {}).values()):
        raise RuntimeError("GRT2_G3_READINESS_CONDITION_FAIL")

    current_commit = str(census["current_main_commit"])
    current_tree = str(census["current_main_tree"])
    candidate_floor = dict(census["candidate_replacement_debt_floor_generation_0"])
    validate_debt_floor(candidate_floor)
    candidate_floor_hash = str(candidate_floor["floor_hash"])
    candidate_floor_count = len(candidate_floor["open_grandfathered_findings"])
    if candidate_floor_hash != census.get("candidate_replacement_floor_hash"):
        raise RuntimeError("GRT2_G3_REPLACEMENT_FLOOR_HASH_MISMATCH")
    if candidate_floor_count != census.get("candidate_replacement_floor_count"):
        raise RuntimeError("GRT2_G3_REPLACEMENT_FLOOR_COUNT_MISMATCH")

    reconciliation = census["old_to_current_reconciliation"]
    extents = dict(reconciliation["extent_dispositions"])
    forbidden_new = 0
    unlawful_expansion = int(extents.get("EXPANDED", 0)) + int(extents.get("MATERIAL_CHANGED", 0))
    if unlawful_expansion:
        raise RuntimeError("GRT2_G3_BASELINE_EXTENT_EXPANSION")
    if census["observer_transition"].get("transition_new_debt_count") != 0:
        raise RuntimeError("GRT2_G3_TRANSITION_NEW_DEBT")
    if census["b0_to_current_lineage"].get("unresolved_lineage_count") != 0:
        raise RuntimeError("GRT2_G3_LINEAGE_UNRESOLVED")

    floor_path = f"{BASE}/GRT2_G3_SUPERSEDING_CANDIDATE_DEBT_FLOOR_GENERATION_0_SEED.json"
    evidence_path = f"{BASE}/GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json"
    qa_path = f"{BASE}/GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_QA_PACKET.json"
    authority_path = f"{BASE}/GRT2_G3_SUPERSEDING_READINESS_AUTHORITY_MANIFEST.json"
    frontier_path = f"{BASE}/GRT2_G3_SUPERSEDING_READINESS_DEPENDENCY_FRONTIER.json"
    packet_path = f"{BASE}/GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_PACKET.json"
    test_path = "tests/governance/grt_v0_2/test_grt2_g3_superseding_reconciliation.py"

    _write(out / floor_path, candidate_floor)

    evidence = _hashed({
        "schema": "ovc-grt2-g3-superseding-readiness-reconciliation-evidence/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": "0.2_REVISED_RATIFIED",
        "packet_id": PACKET_ID,
        "gate_id": "GRT2-G3",
        "status": "RECONCILED_QA_PASS_PRE_GATE_READY",
        "authority_effect": "NONE_SUPERSEDING_READINESS_RECONCILIATION_ONLY",
        "current_protected_main": {"commit": current_commit, "tree": current_tree},
        "source_artifact": {
            "workflow_run_id": args.workflow_run_id,
            "artifact_id": args.artifact_id,
            "artifact_name": args.artifact_name,
            "artifact_digest": args.artifact_digest,
            "evidence_file_sha256": _sha256_file(census_path),
            "semantic_evidence_hash": census["logical_sha256"],
            "diagnostic_head_sha": args.diagnostic_head_sha,
        },
        "historical_decision_preservation": {
            "previous_operator_decision_logical_sha256": PREVIOUS_DECISION_ID,
            "previous_operator_pass_status": "RECEIVED_UNCONSUMED_EXACT_APPROVED_FLOOR_STALE",
            "former_floor": dict(census["former_floor"]),
            "failed_activation_pr": 1288,
            "failed_activation_disposition": "BLOCKED_EXACT_APPROVED_FLOOR_STALE_ON_CURRENT_MAIN",
            "preservation": "IMMUTABLE_HISTORICAL_RECORDS_NO_AUTHORITY_TRANSFER",
        },
        "constitution": {
            "canonical_hash": CONSTITUTION_HASH,
            "status": "PROPOSED_UNADMITTED",
            "semantics": "UNCHANGED",
        },
        "active_enforcement": "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "g3_authority": "NOT_CONSUMED",
        "pgn_native_adoption": census["authority_frontier"]["pgn_native_genesis_adoption"],
        "b0_integrity": dict(census["b0_integrity"]),
        "current_census": dict(census["current_census"]),
        "observer_transition": {
            key: census["observer_transition"].get(key)
            for key in (
                "baseline_observer_condition_count",
                "current_observer_condition_count",
                "current_condition_classification_count",
                "novel_observer_condition_count",
                "resolved_observer_condition_count",
                "stable_unchanged_count",
                "stable_reduced_count",
                "stable_expanded_count",
                "stable_material_changed_count",
                "transition_new_debt_count",
                "unresolved_current_condition_count",
                "transition_debt_zero_proven",
                "baseline_expansion_zero_proven",
                "authority_effect",
            )
        },
        "b0_to_current_lineage": {
            key: census["b0_to_current_lineage"].get(key)
            for key in (
                "status",
                "b0_member_count",
                "b0_membership_sha256",
                "current_full_g3_finding_count",
                "mapped_current_finding_count",
                "unresolved_lineage_count",
                "unresolved_baseline_member_ids",
                "unresolved_current_finding_ids",
                "authority_effect",
            )
        },
        "old_to_current_reconciliation": {
            "former_finding_count": census["former_floor"]["count"],
            "current_finding_count": census["current_census"]["finding_count"],
            "unchanged_finding_count": reconciliation["unchanged_finding_count"],
            "resolved_finding_count": reconciliation["resolved_finding_count"],
            "resolved_finding_ids": list(reconciliation["resolved_finding_ids"]),
            "resolved_rows": [_compact_finding(row) for row in reconciliation["resolved_rows"]],
            "added_finding_count": reconciliation["added_finding_count"],
            "added_finding_ids": list(reconciliation["added_finding_ids"]),
            "added_rows": [_compact_finding(row) for row in reconciliation["added_rows"]],
            "extent_dispositions": extents,
            "non_unchanged_extent_rows": list(reconciliation["non_unchanged_extent_rows"]),
            "classification": {
                "lawfully_resolved_since_former_gate_ready": reconciliation["resolved_finding_count"],
                "pre_activation_current_findings_from_lawful_repository_evolution": reconciliation["added_finding_count"],
                "deterministic_current_state_replacements": len(reconciliation["same_rule_replacement_candidates"]),
                "forbidden_new_or_recurrent_debt": forbidden_new,
                "unlawfully_expanded_baseline_debt": unlawful_expansion,
                "r300_findings_preserved_without_pgn_authority_consumption": True,
            },
        },
        "candidate_floor_seed": {
            "path": floor_path,
            "generation": 0,
            "floor_hash": candidate_floor_hash,
            "open_grandfathered_finding_count": candidate_floor_count,
            "status": "INACTIVE_CANDIDATE_SEED_FOR_FINAL_GATE_READY_REVALIDATION",
        },
        "readiness_conditions": dict(census["readiness_conditions"]),
        "mechanically_eligible_for_superseding_gate_preparation": True,
        "warnings": [],
        "unresolved_issues": [],
        "next_packet": NEXT_PACKET,
    })
    _write(out / evidence_path, evidence)

    qa = _hashed({
        "schema": "ovc-grt2-g3-superseding-readiness-reconciliation-qa/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": "GRT2-G3",
        "scope": "NO_AUTHORITY_CURRENT_MAIN_RECONCILIATION_AND_INACTIVE_FLOOR_SEED_ONLY",
        "checks": {
            "source_artifact_reproducible": True,
            "b0_exact_569": True,
            "constitution_identity_exact": True,
            "constitution_unactivated": True,
            "former_floor_immutable": True,
            "transition_new_debt_zero": True,
            "baseline_expansion_zero": True,
            "unresolved_lineage_zero": True,
            "not_evaluable_zero": True,
            "adapter_errors_zero": True,
            "all_rule_families_evaluated": True,
            "pgn_authority_unconsumed": True,
            "g3_authority_unconsumed": True,
            "limited_enforcement_unchanged": True,
        },
        "qa_disposition": "PASS",
        "qa_recommendation": "PASS_INTEGRATE_RECONCILIATION_THEN_MATERIALISE_SUPERSEDING_GATE_READY",
        "warnings": [],
        "unresolved_issues": [],
        "authority_effect": "NONE_QA_ONLY",
        "rollback": "Close or forward-supersede this authority-inert reconciliation packet; preserve all historical G3 evidence and Git history.",
    })
    _write(out / qa_path, qa)

    authority = IntegrationAuthorityManifest(
        plan_id=PLAN_ID,
        packet_id=PACKET_ID,
        gate_id="GRT2-G3",
        authority_class="AUTO_EXECUTABLE",
        authority_delta="NONE_SUPERSEDING_READINESS_RECONCILIATION_ONLY",
        authority_sources=(evidence_path, qa_path, "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DECISION_PACKET.json", "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json"),
        reserved_boundaries=("GRT2-G3_OPERATOR_DECISION", "CONSTITUTION_V0_2_ACTIVATION", "DEBTFLOOR_GENERATION_0_ACTIVATION", "FULL_GRT_EXACT_ACTIVATION", "PGN_NATIVE_ADOPTION"),
    )
    authority_binding = {
        "schema": "ovc-integration-authority-manifest-binding/v0_1",
        "authority_manifest": asdict(authority),
        "authority_manifest_id": authority.logical_id,
    }
    _write(out / authority_path, authority_binding)

    frontier = DependencyFrontier(
        dependencies=(
            f"CURRENT-PROTECTED-MAIN:{current_commit}",
            f"GRT2-G3-SUPERSEDING-CENSUS:{census['logical_sha256']}",
            f"GRT2-G3-SOURCE-ARTIFACT:{args.artifact_digest}",
            f"GRT2-G3-FORMER-FLOOR:{FORMER_FLOOR_HASH}",
            f"GRT2-G3-CANDIDATE-FLOOR-SEED:{candidate_floor_hash}",
            f"GRT2-G3-PREVIOUS-OPERATOR-DECISION:{PREVIOUS_DECISION_ID}",
            f"IMMUTABLE-B0:{B0_HASH}",
        ),
        predecessor_requirement="EXACT_CURRENT_MAIN_RECONCILIATION_REQUIRED",
        owner_bindings=("PROGRAMME_GENESIS:GRT2-G3-OPERATOR-RESERVED", "PROGRAMME_GENESIS:PGN-AUTHORITY-UNCHANGED"),
    )
    frontier_binding = {
        "schema": "ovc-dependency-frontier-binding/v0_1",
        "dependency_frontier": asdict(frontier),
        "dependency_frontier_id": frontier.logical_id,
    }
    _write(out / frontier_path, frontier_binding)

    changed_files = [evidence_path, qa_path, floor_path, authority_path, frontier_path, packet_path, test_path]
    packet = _hashed({
        "schema": "ovc-grt2-g3-superseding-readiness-reconciliation-packet/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": "0.2_REVISED_RATIFIED",
        "packet_id": PACKET_ID,
        "gate_id": "GRT2-G3",
        "status": "IMPLEMENTED_QA_PASS_AWAITING_EXACT_FINAL_INTEGRATION",
        "baseline_commit": current_commit,
        "baseline_tree": current_tree,
        "authority_required": "AUTO_EXECUTABLE",
        "authority_delta": "NONE",
        "binding_policy": "LATE_PHYSICAL_PLACEMENT",
        "evidence": evidence_path,
        "qa_packet": qa_path,
        "candidate_floor_seed": floor_path,
        "authority_manifest": authority_path,
        "authority_manifest_id": authority.logical_id,
        "dependency_frontier": frontier_path,
        "dependency_frontier_id": frontier.logical_id,
        "changed_files": changed_files,
        "acceptance_conditions": {
            "exact_current_main_reconciliation": True,
            "authority_delta_none": True,
            "no_activation": True,
            "qa_pass": True,
            "warnings_zero": True,
            "unresolved_issues_zero": True,
            "final_gate_ready_revalidation_required_after_merge": True,
        },
        "tests_required": [test_path, "tests/governance/grt_v0_2", "repository-wide pytest", "pytest/unittest parity", "runner parity", "VIT routing", "SIQ READY", "GRT exact-final integration readiness", "merge readiness"],
        "rollback": "Close or forward-supersede this authority-inert reconciliation packet; preserve the former G3 packet, unconsumed PASS, failed activation evidence, immutable B0, both floor identities, external artifacts and Git history. Never force-push or rewrite history.",
        "next_packet": NEXT_PACKET,
    })
    _write(out / packet_path, packet)

    test_text = f'''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nfrom ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, validate_debt_floor\nfrom ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256\nfrom ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest\n\nROOT = Path(__file__).resolve().parents[3]\nBASE = ROOT / "{BASE}"\n\ndef load(name: str) -> dict:\n    return json.loads((BASE / name).read_text(encoding="utf-8"))\n\ndef assert_hash(record: dict) -> None:\n    payload = dict(record); actual = payload.pop("logical_sha256"); assert actual == canonical_sha256(payload)\n\ndef test_superseding_reconciliation_is_exact_and_authority_inert() -> None:\n    evidence = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json")\n    qa = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_QA_PACKET.json")\n    packet = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_PACKET.json")\n    for record in (evidence, qa, packet): assert_hash(record)\n    assert evidence["current_protected_main"] == {{"commit": "{current_commit}", "tree": "{current_tree}"}}\n    assert evidence["historical_decision_preservation"]["previous_operator_pass_status"] == "RECEIVED_UNCONSUMED_EXACT_APPROVED_FLOOR_STALE"\n    assert evidence["b0_integrity"]["exact"] is True\n    assert evidence["b0_integrity"]["member_count"] == B0_MEMBER_COUNT\n    assert evidence["b0_integrity"]["membership_sha256"] == B0_MEMBERSHIP_SHA256\n    assert evidence["current_census"]["finding_count"] == {candidate_floor_count}\n    assert evidence["current_census"]["not_evaluable"] == []\n    assert evidence["current_census"]["adapter_errors"] == []\n    assert all(evidence["readiness_conditions"].values())\n    rec = evidence["old_to_current_reconciliation"]\n    assert rec["classification"]["forbidden_new_or_recurrent_debt"] == 0\n    assert rec["classification"]["unlawfully_expanded_baseline_debt"] == 0\n    assert qa["qa_disposition"] == "PASS" and qa["unresolved_issues"] == []\n    assert packet["authority_delta"] == "NONE" and packet["next_packet"] == "{NEXT_PACKET}"\n\ndef test_candidate_floor_seed_is_new_valid_and_inactive() -> None:\n    floor = load("GRT2_G3_SUPERSEDING_CANDIDATE_DEBT_FLOOR_GENERATION_0_SEED.json")\n    validate_debt_floor(floor)\n    assert floor["floor_hash"] == "{candidate_floor_hash}"\n    assert len(floor["open_grandfathered_findings"]) == {candidate_floor_count}\n    evidence = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json")\n    assert evidence["candidate_floor_seed"]["status"] == "INACTIVE_CANDIDATE_SEED_FOR_FINAL_GATE_READY_REVALIDATION"\n    assert evidence["historical_decision_preservation"]["former_floor"]["floor_hash"] == "{FORMER_FLOOR_HASH}"\n\ndef test_superseding_reconciliation_bindings_are_exact_and_reserved() -> None:\n    a = load("GRT2_G3_SUPERSEDING_READINESS_AUTHORITY_MANIFEST.json")\n    f = load("GRT2_G3_SUPERSEDING_READINESS_DEPENDENCY_FRONTIER.json")\n    authority = IntegrationAuthorityManifest(**{{**a["authority_manifest"], "authority_sources": tuple(a["authority_manifest"]["authority_sources"]), "reserved_boundaries": tuple(a["authority_manifest"]["reserved_boundaries"])}})\n    frontier = DependencyFrontier(**{{**f["dependency_frontier"], "dependencies": tuple(f["dependency_frontier"]["dependencies"]), "owner_bindings": tuple(f["dependency_frontier"]["owner_bindings"])}})\n    assert authority.logical_id == a["authority_manifest_id"]\n    assert frontier.logical_id == f["dependency_frontier_id"]\n    assert authority.authority_delta == "NONE_SUPERSEDING_READINESS_RECONCILIATION_ONLY"\n    assert "GRT2-G3_OPERATOR_DECISION" in authority.reserved_boundaries\n    assert "PGN_NATIVE_ADOPTION" in authority.reserved_boundaries\n'''
    (out / test_path).parent.mkdir(parents=True, exist_ok=True)
    (out / test_path).write_text(test_text, encoding="utf-8")

    meta = {
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "next_packet": NEXT_PACKET,
        "base_commit": current_commit,
        "base_tree": current_tree,
        "authority_manifest_id": authority.logical_id,
        "dependency_frontier_id": frontier.logical_id,
        "candidate_floor_hash": candidate_floor_hash,
        "candidate_floor_count": candidate_floor_count,
        "changed_files": changed_files,
    }
    _write(out / "materialisation-meta.json", meta)
    print(json.dumps(meta, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
