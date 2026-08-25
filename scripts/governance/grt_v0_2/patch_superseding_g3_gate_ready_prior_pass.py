#!/usr/bin/env python3
"""Keep the already-received superseding G3 PASS bound to the r4 floor only.

This helper is authority-inert. It patches any freshly materialised replacement
GATE_READY packet so the earlier operator PASS remains explicitly unconsumed.
The fresh floor identity is read from the newly materialised gate and is never
silently equated with the r4 approved object.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path.cwd().resolve()
BASE = ROOT / "docs/programmes/grt-v0-2/g3/superseding"
STATE = ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json"
GATE = BASE / "GRT2_G3_SUPERSEDING_GATE_READY_DECISION_PACKET.json"
INSTRUCTION = BASE / "GRT2_G3_SUPERSEDING_OPERATOR_INSTRUCTION_RECEIPT.json"

R4_GATE_DECISION_ID = "34ca4e8e34963f87384a3fd08a9b8ebd69e2b4c7198418e197238a328ffc23e2"
R4_GATE_MERGE = "8a0423fdb29bc855b340ceb1021d1b030ac12ed7"
R4_GATE_TREE = "a7749f2a16239362d3f30d7f6a337d4cef205b28"
R4_APPROVED_FLOOR_COUNT = 1641
R4_APPROVED_FLOOR_HASH = "f93994585bd189e188dfde047f38bb6355554ac7c9abce61079026573d676bdb"
R4_INSTRUCTION_ID = "034f8e1f21dbea440c3feb35fbcee066ee92f3f89d7961f090393b36e8e42f04"
STALE_STATUS = "RECEIVED_UNCONSUMED_APPROVED_R4_FLOOR_STALE_AFTER_GATE_READY_MERGE"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_hashed(path: Path, record: dict[str, Any]) -> None:
    payload = dict(record)
    payload.pop("logical_sha256", None)
    payload["logical_sha256"] = canonical_sha256(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    instruction = load(INSTRUCTION)
    if instruction.get("logical_sha256") != R4_INSTRUCTION_ID:
        raise RuntimeError("R4_SUPERSEDING_OPERATOR_INSTRUCTION_IDENTITY_MISMATCH")
    approved = instruction.get("approved_object", {})
    if approved.get("replacement_floor_count") != R4_APPROVED_FLOOR_COUNT or approved.get("replacement_floor_hash") != R4_APPROVED_FLOOR_HASH:
        raise RuntimeError("R4_SUPERSEDING_OPERATOR_APPROVED_OBJECT_MISMATCH")
    if instruction.get("consumed") is not False:
        raise RuntimeError("R4_SUPERSEDING_OPERATOR_PASS_ALREADY_CONSUMED")

    gate = load(GATE)
    replacement = gate.get("proposed_debt_floor_generation_0", {})
    fresh_floor_hash = str(replacement.get("floor_hash", ""))
    fresh_floor_count = int(replacement.get("count", -1))
    if len(fresh_floor_hash) != 64 or fresh_floor_count < 0:
        raise RuntimeError("FRESH_SUPERSEDING_FLOOR_IDENTITY_INVALID")
    if fresh_floor_hash == R4_APPROVED_FLOOR_HASH:
        raise RuntimeError("R4_APPROVED_FLOOR_REPRODUCED_USE_EXACT_R4_REVALIDATION_PATH")
    census_id = str(gate.get("readiness_reconciliation", {}).get("exact_current_census_logical_sha256", ""))
    if len(census_id) != 64:
        raise RuntimeError("FRESH_SUPERSEDING_CENSUS_IDENTITY_INVALID")

    gate["operator_instruction_status"] = STALE_STATUS
    gate["prior_superseding_operator_pass"] = {
        "instruction_receipt_logical_sha256": R4_INSTRUCTION_ID,
        "gate_ready_decision_identity": R4_GATE_DECISION_ID,
        "gate_ready_merge_commit": R4_GATE_MERGE,
        "gate_ready_merge_tree": R4_GATE_TREE,
        "approved_floor_generation": 0,
        "approved_floor_count": R4_APPROVED_FLOOR_COUNT,
        "approved_floor_hash": R4_APPROVED_FLOOR_HASH,
        "fresh_census_logical_sha256": census_id,
        "fresh_replacement_floor_count": fresh_floor_count,
        "fresh_replacement_floor_hash": fresh_floor_hash,
        "status": STALE_STATUS,
        "consumed": False,
        "non_transfer": "The r4 PASS does not approve this replacement floor; a fresh operator decision is required.",
    }
    gate["exact_work_after_pass"] = [
        "Re-resolve protected main and reproduce this exact replacement generation-0 floor.",
        "Record a fresh operator GRT2-G3 superseding PASS against this exact decision identity.",
        "Activate only Constitution v0.2, this exact generation-0 DebtFloor, FULL_GRT_EXACT and NO_NEW_HYGIENE_DEBT == 0.",
        "Run post-activation qualification and continue only into plan-authorised post-G3 GRT packets.",
    ]
    write_hashed(GATE, gate)

    state = load(STATE)
    if state.get("candidate_debt_floor_hash") != fresh_floor_hash:
        raise RuntimeError("FRESH_SUPERSEDING_STATE_FLOOR_MISMATCH")
    state["superseding_operator_pass"] = STALE_STATUS
    state["prior_superseding_gate_ready_decision_identity"] = R4_GATE_DECISION_ID
    state["prior_superseding_gate_ready_merge_commit"] = R4_GATE_MERGE
    state["fresh_operator_decision_required"] = True
    write_hashed(STATE, state)

    print(json.dumps({
        "status": "PASS_AUTHORITY_UNCONSUMED_FRESH_DECISION_REQUIRED",
        "r4_gate_decision_identity": R4_GATE_DECISION_ID,
        "r4_approved_floor_hash": R4_APPROVED_FLOOR_HASH,
        "fresh_census_logical_sha256": census_id,
        "fresh_floor_count": fresh_floor_count,
        "fresh_floor_hash": fresh_floor_hash,
        "changed_files": [str(GATE.relative_to(ROOT)), str(STATE.relative_to(ROOT))],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
