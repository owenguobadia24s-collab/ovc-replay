from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_C2_SEQUENCE_EVIDENCE_OPERATOR_GATE_PACKET.json"
QA = ROOT / "docs/releases/research-console-v0-3/rc-g5/RC_G5_C2_SEQUENCE_EVIDENCE_QA_PACKET.json"
AUTHORITY = ROOT / "registries/research_console/RC_G5_C2_SEQUENCE_EVIDENCE_AUTHORITY_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:  # pragma: no cover
        digest = hashlib.sha1()
    digest.update(header)
    digest.update(content)
    return digest.hexdigest()


def main() -> int:
    for path in (GATE, QA, AUTHORITY):
        if not path.is_file():
            raise SystemExit("RC_G5_REQUIRED_FILE_MISSING:" + str(path.relative_to(ROOT)))

    gate = load(GATE)
    qa = load(QA)
    authority = load(AUTHORITY)

    if gate.get("classification") != "OPERATOR_REQUIRED_NOT_AUTO_RATIFIABLE":
        raise SystemExit("RC_G5_CLASSIFICATION_FAILURE")
    if gate.get("operator_decision_required") is not True or gate.get("auto_ratifiable") is not False:
        raise SystemExit("RC_G5_OPERATOR_GATE_FLAGS_FAILURE")
    if gate.get("proposed_authority_delta") != "LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION":
        raise SystemExit("RC_G5_AUTHORITY_DELTA_FAILURE")
    if gate.get("status") not in {"GATE_READY_PENDING_FINAL_HEAD_CI", "GATE_READY"}:
        raise SystemExit("RC_G5_GATE_STATUS_FAILURE")
    if gate.get("operator_decision") is not None:
        raise SystemExit("RC_G5_OPERATOR_DECISION_PREMATURE")
    if gate.get("unresolved_issues"):
        raise SystemExit("RC_G5_UNRESOLVED_ISSUES")

    if authority.get("enabled") is not False or authority.get("status") != "DISABLED_PENDING_OPERATOR_RC_G5":
        raise SystemExit("RC_G5_ROUTE_PREMATURELY_ENABLED")
    if authority.get("current_route_state") != "DISABLED_PENDING_RC_G5":
        raise SystemExit("RC_G5_ROUTE_STATE_FAILURE")
    if authority.get("writes") != "NONE" or authority.get("annotation_actions") != "NONE":
        raise SystemExit("RC_G5_WRITE_BOUNDARY_FAILURE")
    if authority.get("remote_deployment") != "DENIED":
        raise SystemExit("RC_G5_REMOTE_BOUNDARY_FAILURE")
    if authority.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("RC_G5_VALIDATION_LOCK_FAILURE")

    bindings = [
        (authority["approved_projection_schema"], "schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json"),
        (authority["approved_adapter"], "src/ovc/research_operations/v0_4/console_projection.py"),
        (authority["approved_local_source"], "apps/research_console/ro4_projection_source.py"),
        (authority["approved_projection_registry"], "registries/research_operations/v0_4/RO4_WP5_PROJECTION_REGISTRY_v0_1.yaml"),
        (authority["assurance_fixture"], "fixtures/research_operations/v0_4/RO4_WP5_CONSOLE_PROJECTION_FIXTURE_v0_1.json"),
    ]
    for binding, relative in bindings:
        path = ROOT / relative
        if binding.get("path") != relative or not path.is_file():
            raise SystemExit("RC_G5_BINDING_PATH_FAILURE:" + relative)
        if blob_sha(path) != binding.get("git_blob_sha"):
            raise SystemExit("RC_G5_BINDING_HASH_FAILURE:" + relative)

    if len(authority.get("panel_classes", [])) != 8 or len(set(authority["panel_classes"])) != 8:
        raise SystemExit("RC_G5_PANEL_MAP_FAILURE")
    if len(authority.get("permanent_banners", [])) != 4:
        raise SystemExit("RC_G5_BANNER_MAP_FAILURE")

    forbidden_pages = [
        ROOT / "apps/research_console/pages/C2_Sequence_Evidence.py",
        ROOT / "apps/research_console/pages/RO4_Sequence_Evidence.py",
    ]
    if any(path.exists() for path in forbidden_pages):
        raise SystemExit("RC_G5_ROUTE_ACTIVATED_BEFORE_OPERATOR_PASS")

    if qa.get("recommendation") != "PASS" or qa.get("blocking_issues"):
        raise SystemExit("RC_G5_QA_FAILURE")

    print("PASS: RC-G5 is consolidated, source-bound, no-write and operator-reserved with route disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
