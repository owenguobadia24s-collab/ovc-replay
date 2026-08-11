from __future__ import annotations

from typing import Any, Mapping

from ovc.development.identity import canonical_sha256

from .security import WRITE_ACTIONS, decide_tool_request


class LocalToolBroker:
    """Narrow inactive-by-default broker. WP5 test mode never performs side effects."""

    def __init__(self, *, active: bool = False, test_mode: bool = False) -> None:
        self.active = bool(active)
        self.test_mode = bool(test_mode)
        self.adapters = {
            "READ_REPOSITORY":"git-repository-read",
            "READ_FILE":"filesystem-read",
            "RUN_TESTS":"python-unittest",
            "WRITE_FILE":"filesystem-write-disabled",
            "GIT_COMMIT":"git-write-disabled",
            "PUSH_BRANCH":"git-write-disabled",
        }

    def dispatch(self, *, envelope: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        decision = decide_tool_request(envelope, request)
        action = str(request.get("action", "")).upper()
        if decision["decision"] != "ALLOW":
            status, reason = "DENY", "SECURITY_DECISION_DENY"
        elif not self.active and not self.test_mode:
            status, reason = "DENY", "BROKER_INACTIVE"
        elif action in WRITE_ACTIONS:
            status, reason = "DENY", "WP5_WRITE_ADAPTER_INACTIVE"
        elif action not in self.adapters:
            status, reason = "DENY", "NO_NARROW_ADAPTER"
        else:
            status, reason = "PASS", "TEST_MODE_WOULD_EXECUTE" if self.test_mode else "ADAPTER_AVAILABLE"
        logical = {
            "request_id":request.get("request_id"), "security_decision_id":decision["decision_id"],
            "status":status, "reason":reason, "adapter":self.adapters.get(action),
            "side_effect_performed":False,
        }
        return {
            "schema":"ovc-dsai-tool-broker-receipt/v1", **logical,
            "authority_effect":"NONE", "receipt_id":canonical_sha256(logical, role="DSAI_TOOL_BROKER_RECEIPT"),
        }
