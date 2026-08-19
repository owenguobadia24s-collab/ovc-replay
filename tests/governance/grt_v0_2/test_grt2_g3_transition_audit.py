from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBERSHIP_SHA256, B0_SOURCE_COMMIT
from ovc.programme_genesis.grt_v0_2.g3_readiness import (
    baseline_topology_from_member_records,
    reconcile_observer_transition_candidates,
)


ROOT = Path(__file__).resolve().parents[3]
B0_MEMBERS = ROOT / "registries/governance/grt_v0_2/baseline/GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"


def _load_b0_members() -> list[dict]:
    return [json.loads(line) for line in B0_MEMBERS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_current_repository_transition_audit_proves_g3_zero_prerequisite() -> None:
    # B0 is the immutable 569-member source evidence produced by the historical
    # GRT v0.1 scanner. Current scanner semantics are intentionally not replayed
    # over the historical tree: doing so would rewrite the observation model.
    baseline = baseline_topology_from_member_records(_load_b0_members())
    current = build_repository_topology(ROOT, ref="HEAD")
    assert baseline["portfolio"]["source_commit"] == B0_SOURCE_COMMIT
    assert baseline["baseline_member_count"] == 569
    assert baseline["baseline_membership_sha256"] == B0_MEMBERSHIP_SHA256
    result = reconcile_observer_transition_candidates(
        baseline_topology=baseline,
        current_topology=current,
    )
    assert result["baseline_observer_condition_count"] == 569
    assert result["current_commit"] == current["portfolio"]["source_commit"]
    # G3 may not be presented while either zero claim remains unproved. The
    # complete source-backed diagnostic is attached to a failure so the packet
    # can classify/repair exact conditions rather than weakening the gate.
    diagnostic = json.dumps(result, sort_keys=True)
    assert result["transition_debt_zero_proven"] is True, diagnostic
    assert result["baseline_expansion_zero_proven"] is True, diagnostic
