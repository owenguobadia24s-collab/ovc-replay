from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import B0_SOURCE_COMMIT
from ovc.programme_genesis.grt_v0_2.g3_readiness import reconcile_observer_transition_candidates


ROOT = Path(__file__).resolve().parents[3]


def _ensure_b0_source_is_locally_reachable() -> None:
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{B0_SOURCE_COMMIT}^{{commit}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if probe.returncode == 0:
        return
    fetched = subprocess.run(
        ["git", "-C", str(ROOT), "fetch", "--no-tags", "origin", B0_SOURCE_COMMIT],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert fetched.returncode == 0, fetched.stderr


def test_current_repository_transition_audit_proves_g3_zero_prerequisite() -> None:
    # B0 is immutable source evidence produced by the historical GRT v0.1
    # scanner.  The current topology engine may evolve while remaining able to
    # inspect that exact source commit, so this audit binds the immutable Git
    # source identity and 569-member population rather than requiring the
    # current scanner to reproduce the historical scanner's topology digest.
    _ensure_b0_source_is_locally_reachable()
    baseline = build_repository_topology(ROOT, ref=B0_SOURCE_COMMIT)
    current = build_repository_topology(ROOT, ref="HEAD")
    assert baseline["portfolio"]["source_commit"] == B0_SOURCE_COMMIT
    assert len(baseline["anomalies"]) == 569
    result = reconcile_observer_transition_candidates(
        baseline_topology=baseline,
        current_topology=current,
    )
    assert result["baseline_observer_condition_count"] == 569
    assert result["current_commit"] == current["portfolio"]["source_commit"]
    # G3 may not be presented while either zero claim remains unproved.  The
    # complete source-backed diagnostic is attached to a failure so the packet
    # can repair/classify the exact conditions rather than weakening the gate.
    diagnostic = json.dumps(result, sort_keys=True)
    assert result["transition_debt_zero_proven"] is True, diagnostic
    assert result["baseline_expansion_zero_proven"] is True, diagnostic
