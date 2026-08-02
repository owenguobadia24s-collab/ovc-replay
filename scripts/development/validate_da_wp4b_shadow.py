#!/usr/bin/env python3
"""Validate DA-WP4B pre-activation shadow and exact branch-protection evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.receipt_bot import evaluate_work_packet, load_policy, load_work_packet  # noqa: E402
from ovc.development.receipt_bot_shadow import (  # noqa: E402
    RecordingShadowProposalAdapter,
    ReceiptBotShadowIdentity,
    evaluate_shadow_readiness,
    execute_pre_activation_shadow,
)

POLICY = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json"
TARGET_PATH = "docs/releases/development-acceleration-v0-1/da-wp4b-shadow/DA_G4B_SHADOW_RECEIPT.json"
RULESET_PATH = "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json"
AUDIT_PATH = "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_EXTERNAL_AUDIT.json"
RULESET_SHA256 = "ed6fe8eb2c030fc185adbf70ae4571fca3fee2f3fbab8002267c8da2b221c0c4"
AUDIT_CANONICAL_SHA256 = "3d21a03d1772491da6cd1722712a816abd200b1f7f69fa76548ffa3b6a6476ea"
REQUIRED = [
    "contracts/development/OVC_RECEIPT_BOT_PRE_ACTIVATION_SHADOW_CONTRACT_v0_1.md",
    "src/ovc/development/receipt_bot_shadow.py",
    "scripts/development/run_da_g4b_shadow.ps1",
    "fixtures/development/receipt_bot/work_packet_shadow_v0_1.json",
    "fixtures/development/receipt_bot/shadow_receipt_payload_v0_1.json",
    "tests/development/test_receipt_bot_shadow.py",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_DA_WP4B_CORRECTIVE_STATE_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_CORRECTIVE_SHADOW_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_CORRECTIVE_SHADOW_QA_PACKET.json",
    AUDIT_PATH,
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_QA_REVIEW.json",
    RULESET_PATH,
]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP4B shadow files: {missing}")

    policy = load_policy(POLICY)
    packet = load_work_packet(ROOT / REQUIRED[3])
    payload = (ROOT / REQUIRED[4]).read_bytes()
    plan = evaluate_work_packet(packet, policy)
    assert plan["status"] == "PASS"
    assert plan["idempotency_status"] == "NEW"
    assert plan["authority"]["active"] is False
    assert plan["authority"]["merge_api_available"] is False

    evidence = {
        condition: "PASS"
        for condition in policy.required_activation_conditions
        if condition not in {"REAL_PROPOSAL_BRANCH_SHADOW_PASS", "QA_PASS"}
    }
    readiness = evaluate_shadow_readiness(evidence, policy)
    assert readiness["status"] == "PASS"
    assert readiness["shadow_execution_authorized"] is True
    assert readiness["authority_active"] is False

    identity = ReceiptBotShadowIdentity(
        app_id=12345,
        installation_id=67890,
        app_slug="ovc-dev-accel-receipt-bot",
        repository="owenguobadia24s-collab/ovc-replay",
        credential_kind="GITHUB_APP_INSTALLATION_TOKEN",
        revocable=True,
        operator_connector=False,
        permissions={"contents": "write", "pull_requests": "write", "metadata": "read"},
    )
    adapter = RecordingShadowProposalAdapter()
    local_audit = execute_pre_activation_shadow(
        plan,
        adapter,
        shadow_readiness=readiness,
        identity=identity,
        content_by_path={TARGET_PATH: payload},
    )
    assert [row["action"] for row in adapter.calls] == [
        "CREATE_BOT_BRANCH",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "OPEN_OR_UPDATE_PULL_REQUEST",
    ]
    assert local_audit["shadow_result"] == "PASS"
    assert local_audit["authority_active"] is False
    assert local_audit["production_transport_active"] is False
    assert local_audit["merge_performed"] is False
    assert local_audit["approval_performed"] is False
    assert local_audit["force_push_performed"] is False
    assert local_audit["history_rewrite_performed"] is False

    ruleset_raw = (ROOT / RULESET_PATH).read_bytes()
    assert hashlib.sha256(ruleset_raw).hexdigest() == RULESET_SHA256
    ruleset = json.loads(ruleset_raw)
    assert ruleset["enforcement"] == "active"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"

    external = json.loads(read(AUDIT_PATH))
    canonical_external = dict(external)
    recorded_sha = canonical_external.pop("external_audit_file_sha256")
    canonical_bytes = json.dumps(canonical_external, indent=2).encode("utf-8") + b"\n"
    assert hashlib.sha256(canonical_bytes).hexdigest() == recorded_sha == AUDIT_CANONICAL_SHA256
    assert external["ruleset_evidence_path"] == RULESET_PATH
    assert external["ruleset_evidence_sha256"] == RULESET_SHA256
    assert external["operator_connector"] is False
    assert external["pull_request_number"] == 211
    assert external["authority_active"] is False
    assert external["production_transport_active"] is False
    assert external["merge_performed"] is False
    assert external["approval_performed"] is False
    assert external["force_push_performed"] is False
    assert external["history_rewrite_performed"] is False

    state = json.loads(read(REQUIRED[6]))
    qa = json.loads(read(REQUIRED[8]))
    shadow_qa = json.loads(read(REQUIRED[10]))
    assert state["authority_active"] is False
    assert state["production_transport"] == "ABSENT_FAIL_CLOSED"
    assert state["shadow"]["pull_request"] == 211
    assert state["shadow"]["open_unmerged"] is True
    assert qa["authority_active"] is False
    assert qa["implementation_blocking_issues"] == []
    assert shadow_qa["shadow_pull_request"] == 211
    assert shadow_qa["shadow_pr_must_remain_unmerged"] is True
    assert shadow_qa["authority_active"] is False

    bodies = "\n".join(read(path) for path in REQUIRED)
    assert '"authority_active": true' not in bodies
    assert '"production_transport": "ACTIVE"' not in bodies

    print("DA-WP4B pre-activation shadow and exact ruleset evidence PASS; activation remains inactive")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
