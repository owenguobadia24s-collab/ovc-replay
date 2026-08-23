#!/usr/bin/env python3
"""Lightweight GRTIntegrationReadiness for an already-produced exact proof."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]


def _required(name: str, length: int | None = None) -> str:
    value = os.environ.get(name, "").strip()
    if not value or (length is not None and len(value) != length):
        raise ValueError(f"GRT_READINESS_INPUT_INVALID:{name}")
    return value


def main() -> int:
    try:
        proof_path = ROOT / _required("OVC_GRT_PROOF_PATH")
        expected_id = _required("OVC_GRT_PROOF_ID", 64)
        base_sha = _required("OVC_GRT_BASE_SHA", 40)
        head_sha = _required("OVC_GRT_HEAD_SHA", 40)
        placement_tree = _required("OVC_GRT_PLACEMENT_TREE_SHA", 40)
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        if not isinstance(proof, dict):
            raise ValueError("GRT_READINESS_PROOF_NOT_OBJECT")
        actual_id = str(proof.get("logical_sha256", ""))
        payload = dict(proof)
        payload.pop("logical_sha256", None)
        if actual_id != expected_id or canonical_sha256(payload) != expected_id:
            raise ValueError("GRT_READINESS_PROOF_ID_MISMATCH")
        if proof.get("profile") != "GRT-EXACT" or proof.get("result") != "PASS":
            raise ValueError("GRT_READINESS_PROOF_NOT_PASS")
        if proof.get("base_commit") != base_sha:
            raise ValueError("GRT_READINESS_BASE_MISMATCH")
        if proof.get("head_commit") != head_sha:
            raise ValueError("GRT_READINESS_HEAD_MISMATCH")
        if proof.get("candidate_tree") != placement_tree:
            raise ValueError("GRT_READINESS_TREE_MISMATCH")
        fetch = subprocess.run(
            ["git", "-C", str(ROOT), "fetch", "--no-tags", "origin", "main:refs/remotes/origin/main"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if fetch.returncode != 0:
            raise ValueError("GRT_READINESS_MAIN_FETCH_FAILED:" + fetch.stderr[-1000:])
        current = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "refs/remotes/origin/main"],
            text=True,
        ).strip()
        if current != base_sha:
            raise ValueError(f"GRT_READINESS_BASE_MOVED:{base_sha}->{current}")
        print(json.dumps({
            "schema": "grt-integration-readiness/v0.2",
            "proof_id": expected_id,
            "current_main_commit": current,
            "current_head_commit": head_sha,
            "current_integration_tree": placement_tree,
            "status": "READY",
            "authority_effect": "NONE_READINESS_ONLY",
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(f"::error title=GRT integration readiness::{type(exc).__name__}:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
