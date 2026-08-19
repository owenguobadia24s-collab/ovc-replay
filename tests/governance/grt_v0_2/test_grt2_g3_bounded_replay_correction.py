from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2 import full_enforcement as base
from ovc.programme_genesis.grt_v0_2.full_enforcement_bounded import (
    _apply_pointer_violations,
    _pointer_catalog,
)

ROOT = Path(__file__).resolve().parents[3]
REG = ROOT / "registries/governance/grt_v0_2"
PGN = ROOT / "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json"
POLICY = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_3.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_relative_current_state_pointer_resolves_inside_own_registry_directory() -> None:
    pointer = "registries/implementation/example/CURRENT_STATE_POINTER.json"
    target = "registries/implementation/example/STATE_v3.json"
    inventory = {pointer: {}, target: {}}
    texts = {pointer: '{"programme_id":"P1","status":"COMPLETED","current_state":"STATE_v3.json"}'}
    current, status_targets, violations = _pointer_catalog(inventory=inventory, texts=texts)
    assert current == {target}
    assert target in status_targets
    assert violations == []


def test_authoritative_state_pointer_key_is_source_bound_current_target() -> None:
    pointer = "registries/implementation/example/CURRENT_STATE_POINTER.json"
    target = "registries/implementation/example/STATE_v9.json"
    inventory = {pointer: {}, target: {}}
    texts = {pointer: '{"programme_id":"P1","status":"COMPLETED","authoritative_state":"registries/implementation/example/STATE_v9.json"}'}
    current, status_targets, violations = _pointer_catalog(inventory=inventory, texts=texts)
    assert current == {target}
    assert target in status_targets
    assert violations == []


def test_provably_missing_pointer_target_becomes_r700_debt_not_adapter_blind_spot() -> None:
    pointer = "registries/implementation/example/CURRENT_STATE_POINTER.json"
    inventory = {pointer: {"blob_hash": "a" * 40}}
    texts = {pointer: '{"programme_id":"P1","status":"COMPLETED","current_state":"MISSING.json"}'}
    current, status_targets, violations = _pointer_catalog(inventory=inventory, texts=texts)
    assert current == set()
    assert status_targets == {pointer}
    assert len(violations) == 1
    assert violations[0]["reason"].startswith("CURRENT_STATE_POINTER_TARGET_MISSING:")

    rules = load(REG / "GRT_RULE_BUNDLE_v0_2.json")
    snapshot = base.build_source_bound_snapshot(
        commit="1" * 40,
        tree="2" * 40,
        inventory=inventory,
        texts=texts,
        impact_paths=[pointer],
        referrers={},
        current_targets=status_targets,
        pointer_errors=[],
        rule_bundle=rules,
        root_registry=load(REG / "GRT_ROOT_REGISTRY_v0_2.json"),
        pgn_state=load(PGN),
        workflow_policy=load(POLICY),
        b0_valid=True,
    )
    _apply_pointer_violations(snapshot, violations=violations, rule_bundle=rules)
    assert not snapshot["adapter_errors"]
    assert any(row["rule_id"] == "GRT-R700" for row in snapshot["findings"])
