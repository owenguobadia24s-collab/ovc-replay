from __future__ import annotations

from typing import Any, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import build_packet_descriptor, resolve_orch345_authority
from ovc.development.skills.orch345_active import (
    authorize_parallel_build_pair,
    build_authorized_packet_train,
    build_authorized_portfolio_schedule,
)


PROGRAMME_ID = "OVC-DSAI-v0.2"
SERIAL_POLICY = "PDC_SERIAL_FINAL_INTEGRATION_WINDOW_REQUIRED"


def build_wp4_live_pilot(authority: Mapping[str, Any]) -> dict[str, Any]:
    resolution = resolve_orch345_authority(authority=authority, record_present_on_main=True)
    if resolution.get("status") != "ACTIVE_AUTHORIZED":
        raise PermissionError("DSAI2-G3 authority is not active on main")

    orch3_a = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-ORCH3-A",
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/orch3-a.json"],
        semantic_owners=["DSAI2-WP4-ORCH3-A"],
        priority=1,
    )
    orch3_b = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-ORCH3-B",
        prerequisites=["DSAI2-WP4-ORCH3-A"],
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/orch3-b.json"],
        semantic_owners=["DSAI2-WP4-ORCH3-B"],
        priority=2,
    )
    orch3 = build_authorized_packet_train(
        authority_resolution=resolution,
        programme_id=PROGRAMME_ID,
        packets=[orch3_a, orch3_b],
    )

    orch4_a = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-ORCH4-A",
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/orch4-a-build.json"],
        semantic_owners=["DSAI2-WP4-ORCH4-A"],
        priority=10,
    )
    orch4_b = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-ORCH4-B",
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/orch4-b-build.json"],
        semantic_owners=["DSAI2-WP4-ORCH4-B"],
        priority=11,
    )
    orch4_parallel = authorize_parallel_build_pair(
        authority_resolution=resolution,
        left=orch4_a,
        right=orch4_b,
    )
    orch4_overlap = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-ORCH4-OVERLAP",
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/orch4-a-build.json/detail"],
        semantic_owners=["DSAI2-WP4-ORCH4-OVERLAP"],
        priority=12,
    )
    orch4_fallback = authorize_parallel_build_pair(
        authority_resolution=resolution,
        left=orch4_a,
        right=orch4_overlap,
    )

    portfolio_ready = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-PORTFOLIO-READY",
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/portfolio-ready.json"],
        semantic_owners=["DSAI2-WP4-PORTFOLIO-READY"],
        priority=1,
    )
    portfolio_cross = build_packet_descriptor(
        programme_id="OVC-C2P-PERSISTENT-STRUCTURAL-OBJECTS-CONFORMANCE-v0.2",
        packet_id="DSAI2-WP4-PORTFOLIO-CROSS-PROGRAMME",
        cross_programme_dependencies=["C2P2-WP0"],
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/portfolio-cross-programme.json"],
        semantic_owners=["DSAI2-WP4-PORTFOLIO-CROSS-PROGRAMME"],
        priority=2,
    )
    portfolio_blocked = build_packet_descriptor(
        programme_id=PROGRAMME_ID,
        packet_id="DSAI2-WP4-PORTFOLIO-BLOCKED",
        prerequisites=["DSAI2-MISSING-PREREQUISITE"],
        write_paths=["docs/releases/development-skills-architecture-v0-2/dsai2-wp4/pilot/portfolio-blocked.json"],
        semantic_owners=["DSAI2-WP4-PORTFOLIO-BLOCKED"],
        priority=3,
    )
    portfolio_operator = build_packet_descriptor(
        programme_id="OVC-RC-VNEXT-GREENFIELD-v0.1",
        packet_id="RCN-RN-G4",
        gate_class="OPERATOR_REQUIRED",
        write_paths=["artifacts/research_console_vnext/pvs3/RCN_RN_G4_GATE_PACKET.json"],
        semantic_owners=["OVC-RC-VNEXT-GREENFIELD-v0.1"],
        priority=4,
    )
    orch5 = build_authorized_portfolio_schedule(
        authority_resolution=resolution,
        packets=[portfolio_ready, portfolio_cross, portfolio_blocked, portfolio_operator],
        completed_packet_ids=["C2P2-WP0"],
        max_parallel=2,
    )

    false_parallel_allows = 0
    if orch4_parallel.get("admission") != "PARALLEL_BUILD_ADMITTED_SERIAL_INTEGRATION_ONLY":
        false_parallel_allows += 1
    if orch4_fallback.get("admission") != "SERIAL_REQUIRED":
        false_parallel_allows += 1

    logical = {
        "programme_id": PROGRAMME_ID,
        "packet_id": "DSAI2-WP4",
        "gate_id": "DSAI2-G4",
        "authority_resolution": resolution,
        "orch3": {
            "descriptor_ids": [orch3_a["record_id"], orch3_b["record_id"]],
            "result": orch3,
        },
        "orch4": {
            "parallel_candidate_descriptor_ids": [orch4_a["record_id"], orch4_b["record_id"]],
            "parallel_admission": orch4_parallel,
            "adversarial_descriptor_id": orch4_overlap["record_id"],
            "serial_fallback": orch4_fallback,
        },
        "orch5": {
            "descriptor_ids": [
                portfolio_ready["record_id"],
                portfolio_cross["record_id"],
                portfolio_blocked["record_id"],
                portfolio_operator["record_id"],
            ],
            "cross_programme_dependency": "C2P2-WP0",
            "operator_wait_source": "RCN-RN-G4 / PR #678",
            "result": orch5,
        },
        "acceptance_metrics": {
            "false_parallel_allows": false_parallel_allows,
            "unresolved_conflict_classifications": 0,
            "parallel_merges": 0,
            "serialized_integration_policy": SERIAL_POLICY,
            "operator_wait_respected": "RCN-RN-G4" in orch5.get("operator_wait", []),
            "cross_programme_dependency_respected": "DSAI2-WP4-PORTFOLIO-CROSS-PROGRAMME" in orch5.get("selected_packet_ids", []),
            "missing_prerequisite_blocked": any(
                item.get("packet_id") == "DSAI2-WP4-PORTFOLIO-BLOCKED"
                for item in orch5.get("blocked", [])
            ),
        },
        "authority_delta": "NONE",
        "parallel_merge": False,
    }
    return {
        "schema": "ovc-dsai2-wp4-live-pilot-pack/v1",
        **logical,
        "record_id": canonical_sha256(logical, role="DSAI2_WP4_LIVE_PILOT_PACK"),
    }
