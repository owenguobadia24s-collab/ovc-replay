#!/usr/bin/env python3
"""Validate the DA-WP4B pre-activation shadow sequencing correction."""

from __future__ import annotations

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
]
POLICY = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json"
TARGET_PATH = "docs/releases/development-acceleration-v0-1/da-wp4b-shadow/DA_G4B_SHADOW_RECEIPT.json"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP4B corrective files: {missing}")

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
    assert readiness["post_shadow_conditions"] == ["QA_PASS", "REAL_PROPOSAL_BRANCH_SHADOW_PASS"]

    blocked_evidence = dict(evidence)
    blocked_evidence["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] = "BLOCKED"
    blocked = evaluate_shadow_readiness(blocked_evidence, policy)
    assert blocked["status"] == "BLOCK"
    assert "NOT_PASS:MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED" in blocked["blockers"]

    identity = ReceiptBotShadowIdentity(
        app_id=12345,
        installation_id=67890,
        app_slug="ovc-dev-accel-receipt-bot",
        repository="owenguobadia24s-collab/ovc-replay",
        credential_kind="GITHUB_APP_INSTALLATION_TOKEN",
        revocable=True,
        operator_connector=False,
        permissions={
            "contents": "write",
            "pull_requests": "write",
            "metadata": "read",
        },
    )
    adapter = RecordingShadowProposalAdapter()
    audit = execute_pre_activation_shadow(
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
    assert audit["mode"] == "PRE_ACTIVATION_SHADOW"
    assert audit["shadow_result"] == "PASS"
    assert audit["authority_active"] is False
    assert audit["production_transport_active"] is False
    assert audit["merge_performed"] is False
    assert audit["approval_performed"] is False
    assert audit["force_push_performed"] is False
    assert audit["history_rewrite_performed"] is False

    contract = read(REQUIRED[0])
    for token in [
        "PRE_ACTIVATION_SHADOW",
        "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
        "dedicated, independently revocable GitHub App",
        "one hash-bound JSON receipt",
        "authority_active=false",
    ]:
        assert token in contract

    powershell = read(REQUIRED[2])
    for token in [
        "OVC_RECEIPT_BOT_APP_ID",
        "OVC_RECEIPT_BOT_INSTALLATION_ID",
        "OVC_RECEIPT_BOT_PRIVATE_KEY_PATH",
        "Assert-ExternalRulesetEvidence",
        "STALE_MAIN_SHA",
        "authority_active = $false",
        "merge_performed = $false",
        "approval_performed = $false",
        "force_push_performed = $false",
    ]:
        assert token in powershell
    lowered = powershell.lower()
    assert "/merges" not in lowered
    assert "/reviews" not in lowered
    assert "force = $true" not in lowered

    state = json.loads(read(REQUIRED[6]))
    corrective = json.loads(read(REQUIRED[7]))
    qa = json.loads(read(REQUIRED[8]))
    assert state["packet_id"] == "DA-WP4B-CORRECTIVE-SHADOW"
    assert state["authority_active"] is False
    assert state["production_transport"] == "ABSENT_FAIL_CLOSED"
    assert state["shadow_transport"] == "LOCAL_POWERSHELL_GITHUB_APP_PRE_ACTIVATION_ONLY"
    assert len(state["retained_blockers"]) == 3
    assert corrective["defect"]["classification"] == "CORRECTABLE_IN_PACKET_SCOPE"
    assert corrective["correction"]["production_authority_change"] == "NONE"
    assert len(corrective["retained_blockers"]) == 3
    assert qa["authority_active"] is False
    assert qa["implementation_blocking_issues"] == []
    assert len(qa["activation_blocking_issues"]) == 3

    bodies = "\n".join(read(path) for path in REQUIRED)
    assert '"authority_active": true' not in bodies
    assert '"production_transport": "ACTIVE"' not in bodies

    print("DA-WP4B pre-activation shadow correction PASS; external shadow remains BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
