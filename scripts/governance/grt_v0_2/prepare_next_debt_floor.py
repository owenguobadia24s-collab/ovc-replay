#!/usr/bin/env python3
"""DebtFloor preparation compatibility helper after GRT2-G3 rollback.

The operator-approved rollback makes G0/G1/G2 immutable historical evidence and
removes DebtFloor advancement from ordinary packet integration. This helper is
kept so existing packet tooling does not break: it emits a deterministic no-write
receipt and never mutates the historical floor pointer or generation files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
AUTHORITY = ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json"
POINTER = ROOT / "registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"GRT_FLOOR_PREP_RECORD_NOT_OBJECT:{path}")
    return value


def _validate_rollback_authority(authority: Mapping[str, Any]) -> None:
    if authority.get("authority_status") != "ACTIVE_ON_MAIN_MATERIALISATION":
        raise ValueError("GRT_FLOOR_PREP_ROLLBACK_AUTHORITY_NOT_ACTIVE")
    if authority.get("enforcement_mode") != "LIMITED_NEW_ARTIFACT_ENFORCEMENT":
        raise ValueError("GRT_FLOOR_PREP_ROLLBACK_MODE_MISMATCH")
    if authority.get("g3_status") != "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT":
        raise ValueError("GRT_FLOOR_PREP_ROLLBACK_STATUS_MISMATCH")
    if authority.get("ordinary_packet_debt_floor_generation_required") is not False:
        raise ValueError("GRT_FLOOR_PREP_DEBTFLOOR_GENERATION_STILL_REQUIRED")
    if authority.get("debt_floor_current_pointer_status") != "HISTORICAL_NON_ENFORCING_DO_NOT_ADVANCE":
        raise ValueError("GRT_FLOOR_PREP_POINTER_NOT_HISTORICAL")


def prepare(base_ref: str, head_ref: str) -> dict[str, Any]:
    base = _git("rev-parse", f"{base_ref}^{{commit}}")
    head = _git("rev-parse", f"{head_ref}^{{commit}}")
    authority = _load(AUTHORITY)
    pointer = _load(POINTER)
    _validate_rollback_authority(authority)
    return {
        "schema": "ovc-grt2-debt-floor-preparation-receipt/v2",
        "base_commit": base,
        "head_commit": head,
        "status": "DISABLED_BY_GRT2_G3_ROLLBACK",
        "enforcement_mode": authority["enforcement_mode"],
        "ordinary_packet_debt_floor_generation_required": False,
        "floor_mutation_required": False,
        "historical_pointer_generation": pointer.get("generation"),
        "historical_pointer_floor_hash": pointer.get("floor_hash"),
        "historical_pointer_definition": pointer.get("definition"),
        "historical_pointer_status": authority["debt_floor_current_pointer_status"],
        "authority_record": "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json",
        "operator_decision_record": "docs/programmes/grt-v0-2/g3/GRT2_G3_ROLLBACK_OPERATOR_DECISION.json",
        "authority_effect": "NONE_COMPATIBILITY_NO_WRITE_RECEIPT",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        receipt = prepare(args.base, args.head)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"::error title=GRT DebtFloor preparation::{type(exc).__name__}:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
