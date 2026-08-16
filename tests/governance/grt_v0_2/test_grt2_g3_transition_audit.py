from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import B0_SOURCE_COMMIT, B0_TOPOLOGY_SHA256
from ovc.programme_genesis.grt_v0_2.g3_readiness import reconcile_observer_transition_candidates


ROOT = Path(__file__).resolve().parents[3]


def test_current_repository_transition_audit_is_reproducible(capsys) -> None:
    baseline = build_repository_topology(ROOT, ref=B0_SOURCE_COMMIT)
    current = build_repository_topology(ROOT, ref="HEAD")
    assert baseline["topology_sha256"] == B0_TOPOLOGY_SHA256
    assert len(baseline["anomalies"]) == 569
    result = reconcile_observer_transition_candidates(
        baseline_topology=baseline,
        current_topology=current,
    )
    print("GRT2_G3_TRANSITION_AUDIT=" + json.dumps(result, sort_keys=True))
    assert result["baseline_observer_condition_count"] == 569
    assert result["current_commit"] == current["portfolio"]["source_commit"]
