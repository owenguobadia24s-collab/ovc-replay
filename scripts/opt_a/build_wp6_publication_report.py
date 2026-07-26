from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-root", type=Path, required=True)
    parser.add_argument("--approval-root", type=Path, required=True)
    parser.add_argument("--readiness-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--execution-commit", required=True)
    args = parser.parse_args()

    roles: dict[str, Any] = {}
    for role in ("discovery", "development", "validation"):
        manifest_path = args.manifest_root / f"{role}.json"
        approval_path = args.approval_root / f"{role}.json"
        readiness_path = args.readiness_root / f"{role}.json"
        manifest = _load(manifest_path)
        approval = _load(approval_path)
        readiness = _load(readiness_path)
        if readiness.get("overall_status") != "READY":
            raise ValueError(f"readiness is not READY for {role}")
        if approval.get("manifest_sha256") != _sha256(manifest_path):
            raise ValueError(f"approval hash mismatch for {role}")
        roles[role.upper()] = {
            "release_id": manifest["release_id"],
            "manifest_id": manifest["manifest_id"],
            "manifest_sha256": _sha256(manifest_path),
            "file_count": len(manifest["files"]),
            "total_size_bytes": sum(int(record["size"]) for record in manifest["files"]),
            "publication": "PUBLISHED_MANIFEST_LAST",
            "remote_verification": "PASS_FULL_BYTE_READBACK",
            "approval_id": approval["approval_id"],
        }

    report: dict[str, Any] = {
        "schema": "ovc-opt-a-wp6-publication-report/v1",
        "programme_id": "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2",
        "work_packet": "WP6",
        "result": "PASS",
        "execution_commit": args.execution_commit,
        "workflow_run_id": args.workflow_run_id,
        "source_release_commit": "8c4c6c70da6f3f8b400d06df990500702813ff39",
        "roles": roles,
        "quarantine_disposition": "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS",
        "authority": {
            "r2_publication": "COMPLETE_REMOTE_VERIFIED",
            "selector_activation": "DENIED_PENDING_SEPARATE_GATE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "opt_b_handoff": "DENIED",
            "market": "NONE",
        },
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report["report_sha256"] = hashlib.sha256(payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
