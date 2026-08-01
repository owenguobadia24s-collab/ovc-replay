from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from apps.research_console.ro4_projection_source import route_registration  # noqa: E402
from ovc.research_operations.v0_4.console_projection import (  # noqa: E402
    REQUIRED_BANNERS,
    ROUTE_STATE,
    build_console_projection,
    validate_console_projection,
    verify_projection_schema_binding,
)

BASE = ROOT / "docs/releases/research-operations-foundation-v0-4"
FIXTURE = ROOT / "fixtures/research_operations/v0_4/RO4_WP5_CONSOLE_PROJECTION_FIXTURE_v0_1.json"
REGISTRY = ROOT / "registries/research_operations/v0_4/RO4_WP5_PROJECTION_REGISTRY_v0_1.yaml"
REQUIRED = [
    ROOT / "contracts/research_operations/v0_4/RO4_DISABLED_CONSOLE_PROJECTION_CONTRACT_v0_1.md",
    ROOT / "src/ovc/research_operations/v0_4/console_projection.py",
    ROOT / "apps/research_console/ro4_projection_source.py",
    ROOT / "tests/research_operations/v0_4/test_ro4_g5_console_projection.py",
    FIXTURE,
    REGISTRY,
    BASE / "ro4-wp5/RO4_WP5_IMPLEMENTATION_PACKET.json",
    BASE / "ro4-g5/RO4_G5_QA_PACKET.json",
    BASE / "ro4-g5/RO4_G5_GATE_PACKET.json",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise SystemExit("MISSING_RO4_G5_FILES:" + ",".join(missing))

    binding = verify_projection_schema_binding(ROOT)
    if binding["git_blob_sha"] != "83bcf57c0374411dfdf02a61483b529b46f333c7":
        raise SystemExit("RO4_G5_SCHEMA_BINDING_FAILURE")

    fixture = load(FIXTURE)
    if fixture.get("status") != "SYNTHETIC_NON_AUTHORITATIVE" or fixture.get("operator_evidence") is not False:
        raise SystemExit("RO4_G5_FIXTURE_AUTHORITY_FAILURE")
    projection = build_console_projection(
        source_commit=fixture["source_commit"],
        source_release_refs=fixture["source_release_refs"],
        panels=fixture["panels"],
        schema_root=ROOT,
    )
    validate_console_projection(projection, schema_root=ROOT)
    if projection["route_state"] != ROUTE_STATE or projection["writes"] != "NONE":
        raise SystemExit("RO4_G5_ROUTE_OR_WRITE_BOUNDARY_FAILURE")
    if tuple(projection["authority_banners"]) != REQUIRED_BANNERS:
        raise SystemExit("RO4_G5_BANNER_FAILURE")
    if route_registration() is not None:
        raise SystemExit("RO4_G5_ROUTE_REGISTRATION_MUST_BE_ABSENT")

    registry_text = REGISTRY.read_text(encoding="utf-8")
    required_tokens = (
        "route_state: DISABLED_PENDING_RC_G5",
        "page_registered: false",
        "navigation_registered: false",
        "writes: NONE",
        "remote_deployment: DENIED",
        "percentage: DENIED",
        "ratio: DENIED",
        "heatmap: DENIED",
        "silent_sampling: DENIED",
        "validation: LOCKED_UNCONSUMED_DENY_BEFORE_RESOLUTION",
    )
    for token in required_tokens:
        if token not in registry_text:
            raise SystemExit("RO4_G5_REGISTRY_TOKEN_MISSING:" + token)

    gate = load(BASE / "ro4-g5/RO4_G5_GATE_PACKET.json")
    if gate.get("operator_decision_required") is not False or gate.get("auto_ratifiable") is not True:
        raise SystemExit("RO4_G5_GATE_AUTHORITY_CLASS_FAILURE")
    if gate.get("proposed_authority_delta") != "DISABLED_LOCAL_READ_ONLY_PRESENTATION_ADAPTERS":
        raise SystemExit("RO4_G5_AUTHORITY_DELTA_FAILURE")
    if gate.get("status") not in {
        "QA_REVIEW_PENDING_CI",
        "APPROVED_PENDING_FINAL_HEAD_CI",
        "APPROVED_PENDING_MERGE",
        "COMPLETED",
    }:
        raise SystemExit("RO4_G5_GATE_STATUS_FAILURE")

    qa = load(BASE / "ro4-g5/RO4_G5_QA_PACKET.json")
    if qa.get("blocking_issues"):
        raise SystemExit("RO4_G5_BLOCKING_QA_ISSUE")

    forbidden_paths = [
        ROOT / "apps/research_console/pages/C2_Sequence_Evidence.py",
        ROOT / "apps/research_console/pages/RO4_Sequence_Evidence.py",
    ]
    if any(path.exists() for path in forbidden_paths):
        raise SystemExit("RO4_G5_CONSOLE_PAGE_ACTIVATED_PRE_RC_G5")

    print("PASS: RO4-G5 adapter is deterministic, schema-bound, read-only and disabled pending RC-G5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
