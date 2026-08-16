from __future__ import annotations

from typing import Any, Mapping

from ovc.development.identity import canonical_sha256

from .security import WRITE_ACTIONS, decide_tool_request


VIT_SUBSTRATE = "DSAI3V-VIT-GENERAL-AUTHORITY-v0.1"


class LocalToolBroker:
    """Narrow deny-by-default broker with separately gated ORCH-1 assisted-write authorization."""

    def __init__(
        self,
        *,
        active: bool = False,
        test_mode: bool = False,
        assisted_write_active: bool = False,
        assisted_write_authority_id: str | None = None,
    ) -> None:
        self.active = bool(active)
        self.test_mode = bool(test_mode)
        self.assisted_write_active = bool(assisted_write_active)
        self.assisted_write_authority_id = str(assisted_write_authority_id) if assisted_write_authority_id else None
        self.adapters = {
            "READ_REPOSITORY":"git-repository-read",
            "READ_FILE":"filesystem-read",
            "RUN_TESTS":"python-unittest",
            "WRITE_FILE":"filesystem-write-assisted",
            "GIT_COMMIT":"git-commit-assisted",
            "PUSH_BRANCH":"git-push-assisted",
        }

    def dispatch(self, *, envelope: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        decision = decide_tool_request(envelope, request)
        action = str(request.get("action", "")).upper()
        side_effect_authorized = False
        if decision["decision"] != "ALLOW":
            status, reason = "DENY", "SECURITY_DECISION_DENY"
        elif not self.active and not self.test_mode:
            status, reason = "DENY", "BROKER_INACTIVE"
        elif action in WRITE_ACTIONS:
            if not self.assisted_write_active:
                status, reason = "DENY", "WP5_WRITE_ADAPTER_INACTIVE"
            elif not self.assisted_write_authority_id:
                status, reason = "DENY", "G8C_AUTHORITY_RECORD_REQUIRED"
            else:
                status, reason = "PASS", "ASSISTED_WRITE_AUTHORIZED"
                side_effect_authorized = True
        elif action not in self.adapters:
            status, reason = "DENY", "NO_NARROW_ADAPTER"
        else:
            status, reason = "PASS", "TEST_MODE_WOULD_EXECUTE" if self.test_mode else "ADAPTER_AVAILABLE"
        logical = {
            "request_id":request.get("request_id"), "security_decision_id":decision["decision_id"],
            "status":status, "reason":reason, "adapter":self.adapters.get(action),
            "assisted_write_authority_id":self.assisted_write_authority_id,
            "side_effect_authorized":side_effect_authorized,
            "side_effect_performed":False,
            "merge_authority":"NONE",
        }
        if action == "PUSH_BRANCH":
            logical.update({
                "required_execution_substrate":VIT_SUBSTRATE,
                "branch_ref_authoritative":False,
                "permanent_pr_requires_vit_lineage":True,
                "direct_physical_main_candidate":False,
            })
        return {
            "schema":"ovc-dsai-tool-broker-receipt/v1", **logical,
            "authority_effect":"NONE", "receipt_id":canonical_sha256(logical, role="DSAI_TOOL_BROKER_RECEIPT"),
        }
