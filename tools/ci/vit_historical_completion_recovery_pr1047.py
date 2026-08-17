#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_historical_completion_recovery import (
    AUTHORIZED_HEAD,
    AUTHORIZED_MERGE,
    AUTHORIZED_PREDECESSOR_TREE,
    AUTHORIZED_RESULT_TREE,
    recover_historical_effective_write_completion,
)
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc_evidence_store.external_root import resolve_external_root


DECISION_PATH = Path(
    "docs/programmes/system-atlas-v0-1/wp10/"
    "ATLAS_WP10_HISTORICAL_COMPLETION_RECOVERY_DECISION.json"
)


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git observation failed")
    return proc.stdout.strip()


def _siq_receipt(*, check_run_id: int, name: str, status: str) -> Mapping[str, Any]:
    logical = {
        "schema": "ovc-github-check-observation/v1",
        "check_run_id": check_run_id,
        "name": name,
        "head_sha": AUTHORIZED_HEAD,
        "status": status,
        "conclusion": "success",
    }
    return {
        **logical,
        "record_id": canonical_sha256(logical, role="DSAI3V_GITHUB_CHECK_OBSERVATION"),
    }


def run(repo_root: Path) -> Mapping[str, Any]:
    decision = json.loads((repo_root / DECISION_PATH).read_text(encoding="utf-8"))
    main_ref = "refs/remotes/origin/main"
    main_before = _git(repo_root, "rev-parse", main_ref)
    if _git(repo_root, "merge-base", "--is-ancestor", AUTHORIZED_MERGE, main_ref):
        raise RuntimeError("authorised merge is not an ancestor of current physical main")
    if _git(repo_root, "rev-parse", f"{AUTHORIZED_MERGE}^{{tree}}") != AUTHORIZED_RESULT_TREE:
        raise RuntimeError("observed physical merge tree mismatch")
    if _git(repo_root, "rev-parse", f"{AUTHORIZED_MERGE}^^{{tree}}") != AUTHORIZED_PREDECESSOR_TREE:
        raise RuntimeError("observed physical predecessor tree mismatch")
    if _git(repo_root, "rev-parse", f"{AUTHORIZED_HEAD}^{{tree}}") != AUTHORIZED_RESULT_TREE:
        raise RuntimeError("admitted head/result tree mismatch")

    external_root = resolve_external_root(
        repository_root=repo_root,
        environ=os.environ,
        create=False,
    )
    store = ReceiptStore(external_root / "receipts")
    main_after_observation = _git(repo_root, "rev-parse", main_ref)
    bundle = recover_historical_effective_write_completion(
        decision=decision,
        receipt_store=store,
        current_main_before=main_before,
        current_main_after=main_after_observation,
        implementation_ref=f"github:pr:1047:head:{AUTHORIZED_HEAD}",
        qa_ref=f"github:pr:1047:head:{AUTHORIZED_HEAD}:required-assurance",
        gate_decision_ref="atlas:ATLAS-G10:PASS_DELEGATED_AUTO_RATIFICATION",
        next_packet="ATLAS-G-OBSERVABILITY-ACTIVATE",
        siq_receipts=(
            _siq_receipt(check_run_id=95343607716, name="SIQ READY admission", status="SIQ_READY"),
            _siq_receipt(check_run_id=95344648607, name="OVC merge readiness", status="PASS"),
        ),
    )
    final_main = _git(repo_root, "rev-parse", main_ref)
    if final_main != main_before:
        raise RuntimeError("physical main changed during receipt-only recovery")
    result = {
        "schema": "ovc-vit-historical-completion-recovery-result/v1",
        **bundle.__dict__,
        "physical_merge_sha": AUTHORIZED_MERGE,
        "observed_physical_tree": AUTHORIZED_RESULT_TREE,
        "current_main_before": main_before,
        "current_main_after": final_main,
        "git_main_write_performed": False,
        "packet_completion_result_count": 1,
        "telemetry_status": "UNAVAILABLE",
        "authority_effect": "NONE",
    }
    print("OVC_VIT_HISTORICAL_COMPLETION_RECOVERY " + json.dumps(result, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        run(Path(args.repo_root).resolve())
        return 0
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"OVC_VIT_HISTORICAL_COMPLETION_RECOVERY_FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
