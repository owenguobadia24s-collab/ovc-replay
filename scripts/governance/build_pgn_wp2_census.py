#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis.migration import build_migration_record, discover_programme_state_paths, logical_sha256


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {
    "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json",
    "registries/implementation/system_atlas_v0_1/ATLAS_PROGRAMME_STATE_v0_1.json",
    "registries/implementation/dias_v0_1/DIASI_PROGRAMME_STATE_v0_1.json",
}
NATIVE_STATE_SCHEMAS = {"ovc-native-programme-state/v1"}
EXPECTED_TARGETS = {
    "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1": "MARKET_TRANSLATION",
    "OVC-C2E-NEUTRAL-EPISODE-v0.1": "MARKET_TRANSLATION",
    "OVC-CLOCK-CONTINUITY-REVIEW-v0.1": "MARKET_TRANSLATION",
    "OVC-DEV-ACCEL-v0.1": "DEVELOPMENT_INFRASTRUCTURE",
    "OVC-MTA-v0.2": "RESEARCH_EVIDENCE",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4": "RESEARCH_EVIDENCE",
    "PD-JUNE-FULL-MONTH-MDR": "RESEARCH_EVIDENCE",
}
GROUPS = [
    {
        "group_id": "PGN-G3-R1-MARKET-TRANSLATION",
        "grouping_basis": "PROGRAMME_CLASS",
        "programme_class": "MARKET_TRANSLATION",
        "candidate_ids": [
            "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1",
            "OVC-C2E-NEUTRAL-EPISODE-v0.1",
            "OVC-CLOCK-CONTINUITY-REVIEW-v0.1",
        ],
    },
    {
        "group_id": "PGN-G3-R2-RESEARCH-EVIDENCE",
        "grouping_basis": "PROGRAMME_CLASS",
        "programme_class": "RESEARCH_EVIDENCE",
        "candidate_ids": [
            "OVC-MTA-v0.2",
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
            "PD-JUNE-FULL-MONTH-MDR",
        ],
    },
    {
        "group_id": "PGN-G3-R3-DEVELOPMENT-INFRASTRUCTURE",
        "grouping_basis": "PROGRAMME_CLASS",
        "programme_class": "DEVELOPMENT_INFRASTRUCTURE",
        "candidate_ids": ["OVC-DEV-ACCEL-v0.1"],
    },
]


def _is_native_programme_state(record: dict[str, Any]) -> bool:
    return record["source"].get("schema") in NATIVE_STATE_SCHEMAS


def build_census(root: Path = ROOT) -> dict[str, Any]:
    paths = discover_programme_state_paths(root, exclude_paths=EXCLUDED)
    records = [build_migration_record(root, path) for path in paths]
    native_records = sorted(
        (record for record in records if _is_native_programme_state(record)),
        key=lambda record: (record["programme_id"], record["source"]["path"]),
    )
    legacy_records = [record for record in records if not _is_native_programme_state(record)]
    by_id = {record["programme_id"]: record for record in legacy_records}
    discovered_ids = set(by_id)
    if discovered_ids != set(EXPECTED_TARGETS):
        missing = sorted(set(EXPECTED_TARGETS) - discovered_ids)
        unexpected = sorted(discovered_ids - set(EXPECTED_TARGETS))
        raise ValueError(f"PGN_WP2_CENSUS_DELTA missing={missing} unexpected={unexpected}")

    dossiers: list[dict[str, Any]] = []
    for programme_id in sorted(EXPECTED_TARGETS):
        record = by_id[programme_id]
        dossiers.append(
            {
                "programme_id": programme_id,
                "candidate_class_recommendation": EXPECTED_TARGETS[programme_id],
                "classification_status": "PROPOSED_PENDING_PGN_G2A_AND_PGN_G3",
                "source": record["source"],
                "source_confidence": record["confidence"],
                "source_coverage": record["source_coverage"],
                "current_preserved_values": record["preserved_values"],
                "unresolved_native_fields": record["unresolved_fields"],
                "migration_uncertainty": record["migration_uncertainty"],
                "candidate_constructed": False,
                "authority_effect": "NONE",
            }
        )

    census: dict[str, Any] = {
        "schema": "ovc-pgn-portfolio-census/v1",
        "programme_id": "OVC-PG-NATIVE-PORTFOLIO-v0.2",
        "packet_id": "PGN-WP2",
        "gate_id": "PGN-G2",
        "baseline_commit": "c9e3881232c9499bb7f47d439b33b9c1c43aaa78",
        "status": "CENSUS_COMPLETE_PENDING_PGN_G2A",
        "authority_effect": "NONE",
        "adoption_target_count": len(dossiers),
        "adoption_targets": dossiers,
        "existing_native_programmes": [
            {
                "programme_id": "OVC-PG-v0.2",
                "classification": "CONSTITUTIONAL_GOVERNANCE",
                "disposition": "ALREADY_NATIVE_EXCLUDED_FROM_CONVERSION",
            },
            *[
                {
                    "programme_id": record["programme_id"],
                    "classification": "NATIVE_PROGRAMME_STATE",
                    "disposition": "ALREADY_NATIVE_EXCLUDED_FROM_CONVERSION",
                }
                for record in native_records
            ],
        ],
        "current_governance_programmes": [
            {
                "programme_id": "OVC-PG-NATIVE-PORTFOLIO-v0.2",
                "classification": "CONSTITUTIONAL_GOVERNANCE",
                "disposition": "CURRENT_RATIFIED_PROGRAMME_NOT_A_LEGACY_CONVERSION_TARGET",
            }
        ],
        "non_admitted_objects": [
            {
                "object_id": "PCCR-G0-PREPARATION",
                "path": "registries/research_operations/planned_closure_continuity/PCCR_G0_PREPARATION_STATE_v0_1.json",
                "classification": "NOT_ADMITTED_PROPOSAL_PREPARATION",
                "candidate_constructed": False,
                "authority_effect": "NONE",
            }
        ],
        "surprise_ledger": [
            {
                "finding_id": "PGN-WP2-SURPRISE-001",
                "finding": "PCCR_PREPARATION_EXISTS_BUT_IS_NOT_ADMITTED",
                "disposition_recommendation": "EXCLUDE_FROM_NATIVE_CONVERSION_POPULATION_PENDING_SEPARATE_ADMISSION",
                "operator_acknowledgement_required": True,
            },
            {
                "finding_id": "PGN-WP2-SURPRISE-002",
                "finding": "PGN_CURRENT_PROGRAMME_STATE_USES_NON_DISCOVERABLE_PORTFOLIO_LEDGER_PATH",
                "disposition_recommendation": "PRESERVE_SEPARATE_FROM_LEGACY_MIGRATION_CENSUS",
                "operator_acknowledgement_required": True,
            },
        ],
        "proposed_review_groups": [
            {
                **group,
                "candidate_count": len(group["candidate_ids"]),
                "maximum_allowed": 3,
                "acknowledgement_required_before_next_group": True,
                "adoption_effect": "NONE",
            }
            for group in GROUPS
        ],
        "candidate_construction_authority": "DENIED_PENDING_PGN_G2A",
        "native_adoption_authority": "DENIED_PENDING_PGN_G3",
        "cross_programme_edge_authority": "DENIED_PENDING_PGN_G5",
        "blockers": [],
        "next_action": "OPERATOR_REVIEW_AND_ACKNOWLEDGE_OR_ADJUST_CENSUS_AT_PGN_G2A",
        "rollback": "Discard and deterministically rebuild this evidence from source programme states; do not construct candidates before PGN-G2A.",
    }
    census["census_sha256"] = logical_sha256(census)
    return census


def main() -> int:
    print(json.dumps(build_census(), sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
