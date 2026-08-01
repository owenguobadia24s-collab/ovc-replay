from __future__ import annotations

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_ACTIVATION_GATE_PACKET.json"
QA = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_ACTIVATION_QA_PACKET.json"
IMPLEMENTATION = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_ACTIVATION_IMPLEMENTATION_PACKET.json"
DECISION = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_OPERATOR_DECISION.json"
RECEIPT = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_DECISION_MERGE_RECEIPT.json"
AUTHORITY = ROOT / "registries/research_console/RC_G5_C2_SEQUENCE_EVIDENCE_AUTHORITY_v0_1.json"
HOME = ROOT / "apps/research_console/Home.py"
WRAPPER = ROOT / "apps/research_console/rc_g5_console.py"
ACTIVE_SOURCE = ROOT / "apps/research_console/ro4_active_projection_source.py"
VIEW = ROOT / "apps/research_console/c2_sequence_evidence.py"
FIXTURE = ROOT / "fixtures/research_operations/v0_4/RO4_WP5_CONSOLE_PROJECTION_FIXTURE_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    required = (GATE, QA, IMPLEMENTATION, DECISION, RECEIPT, AUTHORITY, HOME, WRAPPER, ACTIVE_SOURCE, VIEW, FIXTURE)
    for path in required:
        if not path.is_file():
            raise SystemExit("RC_G5_ACTIVATION_REQUIRED_FILE_MISSING:" + str(path.relative_to(ROOT)))

    gate = load(GATE)
    qa = load(QA)
    decision = load(DECISION)
    receipt = load(RECEIPT)
    authority = load(AUTHORITY)
    fixture = load(FIXTURE)

    if decision.get("decision") != "PASS" or decision.get("decision_id") != "RC-G5.OPERATOR.PASS.20260801T084900Z":
        raise SystemExit("RC_G5_ACTIVATION_OPERATOR_DECISION_FAILURE")
    if receipt.get("squash_merge_commit") != "12cf93e9eec93c9b2245393bf8fb262109790e2d":
        raise SystemExit("RC_G5_ACTIVATION_DECISION_MERGE_RECEIPT_FAILURE")
    if gate.get("operator_decision_required") is not False or gate.get("auto_ratifiable") is not True:
        raise SystemExit("RC_G5_ACTIVATION_GATE_FLAGS_FAILURE")
    if gate.get("proposed_authority_delta") != "ACTIVATE_APPROVED_LOCAL_READ_ONLY_ROUTE":
        raise SystemExit("RC_G5_ACTIVATION_DELTA_FAILURE")
    if gate.get("status") not in {"QA_REVIEW_PENDING_CI", "APPROVED_PENDING_FINAL_HEAD_CHECKS_AND_MERGE", "COMPLETED"}:
        raise SystemExit("RC_G5_ACTIVATION_GATE_STATUS_FAILURE")
    if gate.get("unresolved_issues"):
        raise SystemExit("RC_G5_ACTIVATION_UNRESOLVED_ISSUES")

    if authority.get("status") != "ENABLED_LOCAL_READ_ONLY" or authority.get("enabled") is not True:
        raise SystemExit("RC_G5_ACTIVATION_ROUTE_NOT_ENABLED")
    if authority.get("operator_decision_id") != decision.get("decision_id"):
        raise SystemExit("RC_G5_ACTIVATION_AUTHORITY_DECISION_MISMATCH")
    if authority.get("route_id") != "RESEARCH.C2_SEQUENCE_EVIDENCE":
        raise SystemExit("RC_G5_ACTIVATION_ROUTE_ID_FAILURE")
    if authority.get("current_route_state") != "ENABLED_LOCAL_READ_ONLY":
        raise SystemExit("RC_G5_ACTIVATION_ROUTE_STATE_FAILURE")
    if authority.get("writes") != "NONE" or authority.get("annotation_actions") != "NONE":
        raise SystemExit("RC_G5_ACTIVATION_WRITE_BOUNDARY_FAILURE")
    if authority.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("RC_G5_ACTIVATION_VALIDATION_BOUNDARY_FAILURE")
    if authority.get("remote_deployment") != "DENIED":
        raise SystemExit("RC_G5_ACTIVATION_REMOTE_BOUNDARY_FAILURE")
    if len(authority.get("panel_classes", [])) != 8 or len(set(authority["panel_classes"])) != 8:
        raise SystemExit("RC_G5_ACTIVATION_PANEL_MAP_FAILURE")
    if len(authority.get("permanent_banners", [])) != 4:
        raise SystemExit("RC_G5_ACTIVATION_BANNER_FAILURE")

    if fixture.get("status") != "SYNTHETIC_NON_AUTHORITATIVE" or fixture.get("operator_evidence") is not False:
        raise SystemExit("RC_G5_ACTIVATION_FIXTURE_AUTHORITY_FAILURE")

    home = HOME.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    source = ACTIVE_SOURCE.read_text(encoding="utf-8")
    if "load_active_projection" not in home or "c2_sequence_projection=_c2_sequence_projection" not in home:
        raise SystemExit("RC_G5_ACTIVATION_HOME_REGISTRATION_FAILURE")
    if "render_c2_sequence_evidence" not in wrapper or "LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION" not in wrapper:
        raise SystemExit("RC_G5_ACTIVATION_WRAPPER_FAILURE")
    for token in ("writes", "annotation_actions", "validation_consumption", "remote_deployment"):
        if token not in source:
            raise SystemExit("RC_G5_ACTIVATION_SOURCE_BOUNDARY_MISSING:" + token)

    forbidden_pages = (
        ROOT / "apps/research_console/pages/C2_Sequence_Evidence.py",
        ROOT / "apps/research_console/pages/RO4_Sequence_Evidence.py",
    )
    if any(path.exists() for path in forbidden_pages):
        raise SystemExit("RC_G5_ACTIVATION_UNBOUNDED_PAGE_REGISTRATION")

    if qa.get("recommendation") not in {"PENDING", "PASS"} or qa.get("blocking_issues"):
        raise SystemExit("RC_G5_ACTIVATION_QA_FAILURE")

    from apps.research_console.ro4_active_projection_source import load_active_projection
    with tempfile.TemporaryDirectory() as tmp:
        missing = load_active_projection(Path(tmp) / "missing.json", schema_root=ROOT)
    if missing.get("route_state") != "ENABLED_LOCAL_READ_ONLY" or missing.get("availability") != "NOT_EVALUATED":
        raise SystemExit("RC_G5_ACTIVATION_FAIL_CLOSED_SOURCE_FAILURE")

    print("PASS: RC-G5 route activation is exact, local, read-only, fail-closed and within operator authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
