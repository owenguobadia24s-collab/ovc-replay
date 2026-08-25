from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.full_enforcement import (
    REQUIRED_FULL_G3_RULE_FAMILIES,
    _transition_rows,
    build_source_bound_snapshot,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
REG = ROOT / "registries/governance/grt_v0_2"
PGN = ROOT / "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json"
POLICY = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_3.json"
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/GRT2_G3_FULL_ENFORCEMENT_ADVERSARIAL_CASES_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot(*, inventory: dict, texts: dict, impact: list[str], referrers: dict | None = None, targets: set[str] | None = None, pgn: dict | None = None, workflow: dict | None = None, changed_rules: bool = False) -> dict:
    return build_source_bound_snapshot(
        commit="1" * 40,
        tree="2" * 40,
        inventory=inventory,
        texts=texts,
        impact_paths=impact,
        referrers=referrers or {},
        current_targets=targets or set(),
        pointer_errors=[],
        rule_bundle=load(REG / "GRT_RULE_BUNDLE_v0_2.json"),
        root_registry=load(REG / "GRT_ROOT_REGISTRY_v0_2.json"),
        pgn_state=pgn or load(PGN),
        workflow_policy=workflow or load(POLICY),
        b0_valid=True,
        rule_bundle_changed=changed_rules,
    )


def finding(rows: list[dict], rule_id: str) -> dict:
    return next(row for row in rows if row["rule_id"] == rule_id)


def evaluation(rows: list[dict], rule_id: str) -> dict:
    return next(row for row in rows if row["rule_id"] == rule_id)


def test_full_g3_family_surface_is_materialized_even_without_applicable_subject_in_every_family() -> None:
    inv = {"src/pkg/a.py": {"blob_hash": "a" * 40}}
    result = snapshot(inventory=inv, texts={"src/pkg/a.py": '# {"programme_id":"P1"}\n'}, impact=["src/pkg/a.py"])
    assert set(result["family_coverage"]) == set(REQUIRED_FULL_G3_RULE_FAMILIES)
    assert set(result["family_coverage"].values()) == {"EVALUATED"}
    assert not any(error.startswith("RULE_FAMILY_SKIPPED") for error in result["adapter_errors"])


def test_missing_pgn_adoption_is_observed_not_promoted() -> None:
    inv = {"src/pkg/a.py": {"blob_hash": "a" * 40}}
    result = snapshot(inventory=inv, texts={"src/pkg/a.py": '# {"programme_id":"P1"}\n'}, impact=["src/pkg/a.py"])
    assert result["pgn_native_genesis_adoption_active"] is False
    r300 = finding(result["findings"], "GRT-R300")
    assert r300["debt_extent"]["accepted_native_genesis_binding_count"] == 0
    assert str(load(PGN)["authority"]["native_genesis_adoption"]).startswith("DENIED")


def test_conflicting_source_bound_owners_fail_closed() -> None:
    inv = {"src/pkg/a.py": {"blob_hash": "a" * 40}, "docs/a.json": {"blob_hash": "b" * 40}, "docs/b.json": {"blob_hash": "c" * 40}}
    texts = {"src/pkg/a.py": "", "docs/a.json": '{"programme_id":"P1","path":"src/pkg/a.py"}', "docs/b.json": '{"programme_id":"P2","path":"src/pkg/a.py"}'}
    result = snapshot(inventory=inv, texts=texts, impact=list(inv), referrers={"src/pkg/a.py": ["docs/a.json", "docs/b.json"]})
    assert finding(result["findings"], "GRT-R200")["debt_extent"]["source_bound_owner_count"] == 2


def test_non_authoritative_decision_packet_cannot_assign_source_bound_owner() -> None:
    implementation = "src/pkg/a.py"
    packet = "docs/programmes/example/TERMINAL_DECISION.json"
    inv = {implementation: {"blob_hash": "a" * 40}, packet: {"blob_hash": "b" * 40}}
    texts = {
        implementation: "",
        packet: json.dumps({
            "programme_id": "P1",
            "subject_path": implementation,
            "operator_decision_required": True,
            "authority_effect": "NONE_DECISION_PACKET_ONLY",
        }),
    }
    result = snapshot(inventory=inv, texts=texts, impact=list(inv), referrers={implementation: [packet]})
    assert finding(result["findings"], "GRT-R200")["debt_extent"]["source_bound_owner_count"] == 0


def test_required_dependency_without_current_target_state_is_not_evaluable() -> None:
    path = "registries/implementation/example/STATE.json"
    inv = {path: {"blob_hash": "a" * 40}}
    texts = {path: '{"programme_id":"P1","status":"RUNNING","edges":[{"edge_type":"REQUIRES","from_programme_id":"P1","to_programme_id":"P2","hardness":"HARD","source_kind":"SOURCE_EXPLICIT"}]}' }
    result = snapshot(inventory=inv, texts=texts, impact=[path], targets={path})
    assert any(row["rule_id"] == "GRT-R500" for row in result["not_evaluable"])
    assert any("REQUIRED_DEPENDENCY_TARGET_CURRENT_STATE_NOT_EVALUABLE" in error for error in result["adapter_errors"])


def test_import_only_dependency_never_becomes_hard_current_dependency() -> None:
    path = "records/dependency.json"
    inv = {path: {"blob_hash": "a" * 40}}
    texts = {path: '{"programme_id":"P1","edge_type":"REQUIRES","from_programme_id":"P1","to_programme_id":"P2","hardness":"HARD","source_kind":"IMPORT_CORROBORATED"}' }
    result = snapshot(inventory=inv, texts=texts, impact=[path])
    rows = [row for row in result["evaluations"] if row["rule_id"] == "GRT-R500"]
    assert rows and all(row["evaluation_status"] == "NOT_APPLICABLE" for row in rows)


def test_fixture_dependency_example_is_not_promoted_to_live_dependency_authority() -> None:
    path = "fixtures/example/dependency_graph.json"
    inv = {path: {"blob_hash": "a" * 40}}
    texts = {path: '{"edges":[{"edge_type":"REQUIRES","from_node":"A","to_node":"B","hardness":"HARD","source_kind":"SOURCE_EXPLICIT","status":"ACCEPTED"}]}' }
    result = snapshot(inventory=inv, texts=texts, impact=[path])
    assert not any(row["rule_id"] in {"GRT-R500", "GRT-R600"} for row in result["evaluations"])
    assert not result["not_evaluable"]


def test_orphan_schema_and_unregistered_workflow_are_actionable_findings() -> None:
    inv = {"schemas/example.schema.json": {"blob_hash": "a" * 40}, ".github/workflows/unregistered.yml": {"blob_hash": "b" * 40}}
    result = snapshot(inventory=inv, texts={path: "" for path in inv}, impact=list(inv))
    assert finding(result["findings"], "GRT-R421")
    assert finding(result["findings"], "GRT-R805")


def _f(rule: str, subject: str, extent: int) -> dict:
    fid = "GRT.FIND." + canonical_sha256({"rule": rule, "subject": subject})[:24]
    return {"finding_id": fid, "rule_id": rule, "rule_family": "OWNERSHIP", "subject_artifact_id": subject, "debt_extent": {"violations": extent}, "evidence_refs": []}


def test_debt_transition_algebra_grandfathers_only_predecessor_findings() -> None:
    unchanged = _transition_rows({"findings": [_f("GRT-R200", "A", 1)]}, {"findings": [_f("GRT-R200", "A", 1)]})
    reduced = _transition_rows({"findings": [_f("GRT-R200", "A", 2)]}, {"findings": [_f("GRT-R200", "A", 1)]})
    expanded = _transition_rows({"findings": [_f("GRT-R200", "A", 1)]}, {"findings": [_f("GRT-R200", "A", 2)]})
    new = _transition_rows({"findings": []}, {"findings": [_f("GRT-R200", "A", 1)]})
    assert unchanged[0]["admission"] == "PASS"
    assert reduced[0]["admission"] == "PASS"
    assert expanded[0]["admission"] == "FAIL"
    assert new[0]["admission"] == "FAIL"


def test_rule_semantic_change_cannot_be_hidden_as_runtime_correction() -> None:
    result = snapshot(inventory={}, texts={}, impact=[], changed_rules=True)
    assert "RULE_SEMANTIC_CHANGE_REQUIRES_OPERATOR_APPROVED_AMENDMENT" in result["adapter_errors"]
    assert evaluation(result["evaluations"], "GRT-R954")["evaluation_status"] == "VIOLATION"


def test_adversarial_fixture_declares_required_fail_closed_cases() -> None:
    ids = {row["id"] for row in load(FIXTURE)["cases"]}
    assert {"MISSING_SOURCE_BINDING", "CONFLICTING_OWNER", "GRANDFATHERED_UNCHANGED", "NEW_ACTIONABLE_DEBT", "EXPANDED_BASELINE_DEBT", "IMPORT_ONLY_HARD_DEPENDENCY", "ORPHAN_SCHEMA", "WORKFLOW_GOVERNANCE_MISSING", "RULE_FAMILY_NO_APPLICABLE_SUBJECT", "RULE_SEMANTIC_CHANGE"} <= ids
