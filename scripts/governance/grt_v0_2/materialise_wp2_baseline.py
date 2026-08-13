from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis.grt_v0_2.debt import (
    B0_ID,
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    SCANNER_IDENTITY,
    baseline_member_id,
    baseline_membership_sha256,
    subject_locator_from_anomaly,
    validate_baseline_members,
    validate_debt_baseline,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_json_v1_text
from ovc.programme_genesis.grt_v0_2.wp0 import (
    build_exact_topology,
    canonical_sha256 as wp0_sha,
)

PROGRAMME_ID = "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"
WP0_COMPACT_REPRODUCTION_SHA256 = "88abf0dcb9cceeb0299d354d8a19804c6bbee3bbfdc38f8ef3847402d1c97e5f"
WP0_COMPACT_REPRODUCTION_ARTIFACT_ID = 9179376890


def _warning_rows(build: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    for item in build["read_model"].get("anomalies", []):
        if item.get("severity") == "WARNING":
            rows.append((dict(item), wp0_sha(item)))
    return sorted(rows, key=lambda pair: str(pair[0]["anomaly_id"]))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json_v1_text(value) + "\n", encoding="utf-8")


def materialise(
    repository_root: Path,
    *,
    baseline_main: str,
    workflow_run_id: int | None = None,
    workflow_run_attempt: int | None = None,
    trigger_commit: str | None = None,
) -> dict[str, Any]:
    root = repository_root.resolve()
    baseline_root = root / "registries/governance/grt_v0_2/baseline"
    docs_root = root / "docs/programmes/grt-v0-2/wp2"
    baseline_root.mkdir(parents=True, exist_ok=True)
    docs_root.mkdir(parents=True, exist_ok=True)

    b0 = build_exact_topology(root, B0_SOURCE_COMMIT, verify_determinism=True)
    b0_topology = str(
        b0["manifest"].get("topology_sha256")
        or b0["read_model"].get("topology_sha256")
        or ""
    )
    if b0["tree"] != B0_SOURCE_TREE or b0_topology != B0_TOPOLOGY_SHA256:
        raise RuntimeError("GRT2_WP2_B0_SOURCE_IDENTITY_MISMATCH")
    source_rows = _warning_rows(b0)
    if len(source_rows) != B0_MEMBER_COUNT:
        raise RuntimeError(f"GRT2_WP2_B0_COUNT_MISMATCH:{len(source_rows)}")

    records: list[dict[str, Any]] = []
    for ordinal, (anomaly, payload_hash) in enumerate(source_rows, start=1):
        records.append(
            {
                "schema": "grt-baseline-member-record/v0.2",
                "baseline_member_id": baseline_member_id(
                    str(anomaly["anomaly_id"]), payload_hash
                ),
                "ordinal": ordinal,
                "original_GRT_anomaly": anomaly["anomaly_id"],
                "original_anomaly_code": anomaly["anomaly_code"],
                "original_subject_locator": subject_locator_from_anomaly(anomaly),
                "payload_hash": payload_hash,
                "original_scanner_identity": SCANNER_IDENTITY,
                "mapped_finding_id": None,
                "mapping_status": "PENDING_WP3_ARTIFACT_GRAPH",
                "disposition": None,
                "lineage_refs": [],
            }
        )
    validate_baseline_members(records)
    if baseline_membership_sha256(records) != B0_MEMBERSHIP_SHA256:
        raise RuntimeError("GRT2_WP2_B0_MEMBERSHIP_MISMATCH")

    ledger = baseline_root / "GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"
    ledger.write_text(
        "".join(canonical_json_v1_text(record) + "\n" for record in records),
        encoding="utf-8",
    )

    baseline = {
        "schema": "grt-debt-baseline/v0.2",
        "baseline_id": B0_ID,
        "source_commit": B0_SOURCE_COMMIT,
        "source_tree_hash": B0_SOURCE_TREE,
        "scanner_id": "GRT.V0.1",
        "scanner_version": SCANNER_IDENTITY,
        "raw_warning_count": B0_MEMBER_COUNT,
        "baseline_member_ids": [record["baseline_member_id"] for record in records],
        "raw_topology_evidence_hash": WP0_COMPACT_REPRODUCTION_SHA256,
        "source_topology_sha256": B0_TOPOLOGY_SHA256,
        "constitution_mapping_status": "PENDING_WP3_ARTIFACT_GRAPH",
        "created_from_audit": True,
        "authority_effect": "NONE_HISTORICAL_BASELINE",
    }
    validate_debt_baseline(baseline, records)
    _write_json(baseline_root / "GRT_DEBT_BASELINE_B0.json", baseline)

    migration = {
        "schema": "grt-b0-to-v0-2-migration/v0.1",
        "programme_id": PROGRAMME_ID,
        "baseline_id": B0_ID,
        "source_commit": B0_SOURCE_COMMIT,
        "source_tree": B0_SOURCE_TREE,
        "source_topology_sha256": B0_TOPOLOGY_SHA256,
        "baseline_membership_sha256": B0_MEMBERSHIP_SHA256,
        "mapping_generation": "PRE_WP3_ARTIFACT_GRAPH",
        "mapping_status": "PENDING_WP3_ARTIFACT_GRAPH",
        "member_count": B0_MEMBER_COUNT,
        "mapped_count": 0,
        "pending_count": B0_MEMBER_COUNT,
        "ambiguous_count": 0,
        "unmapped_no_active_rule_count": 0,
        "entries": [
            {
                "baseline_member_id": record["baseline_member_id"],
                "original_GRT_anomaly": record["original_GRT_anomaly"],
                "mapped_finding_id": None,
                "mapping_status": "PENDING_WP3_ARTIFACT_GRAPH",
                "lineage_refs": [],
            }
            for record in records
        ],
        "zero_mapping_claim_prohibited": True,
        "authority_effect": "NONE_LINEAGE_PREPARATION_ONLY",
    }
    _write_json(baseline_root / "GRT_B0_TO_V0_2_MIGRATION_v0_1.json", migration)

    current = build_exact_topology(root, baseline_main, verify_determinism=False)
    current_rows = _warning_rows(current)
    current_topology = str(
        current["manifest"].get("topology_sha256")
        or current["read_model"].get("topology_sha256")
        or ""
    )
    (baseline_root / "GRT_LATE_PREEXISTING_FINDINGS.jsonl").write_text(
        "", encoding="utf-8"
    )
    (baseline_root / "GRT_PRE_G3_TRANSITION_DEBT.jsonl").write_text(
        "", encoding="utf-8"
    )

    status = {
        "schema": "ovc-grt2-wp2-current-classification-status/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "GRT2-WP2",
        "source_commit": baseline_main,
        "source_tree": current["tree"],
        "raw_warning_count": len(current_rows),
        "source_topology_sha256": current_topology,
        "late_discovered_register": "registries/governance/grt_v0_2/baseline/GRT_LATE_PREEXISTING_FINDINGS.jsonl",
        "transition_debt_ledger": "registries/governance/grt_v0_2/baseline/GRT_PRE_G3_TRANSITION_DEBT.jsonl",
        "late_discovered_record_count": 0,
        "transition_debt_record_count": 0,
        "classification_complete": False,
        "classification_status": "NOT_EVALUABLE_UNTIL_WP3A_V0_2_SCANNER_AND_ARTIFACT_GRAPH",
        "empty_ledgers_are_not_zero_debt_evidence": True,
        "zero_transition_debt_claim_prohibited": True,
        "authority_effect": "NONE_PRE_G2_OBSERVATION_ONLY",
    }
    _write_json(docs_root / "GRT2_WP2_CURRENT_CLASSIFICATION_STATUS.json", status)

    source_receipt = {
        "schema": "ovc-grt2-wp2-source-evidence-receipt/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "GRT2-WP2",
        "baseline_main_commit": baseline_main,
        "baseline_main_tree": current["tree"],
        "materialisation": {
            "workflow_run_id": workflow_run_id,
            "workflow_run_attempt": workflow_run_attempt,
            "trigger_commit": trigger_commit,
            "method": "EXACT_SOURCE_REPLAY_BRANCH_SCOPED_MATERIALISATION",
            "result": "PASS",
        },
        "b0": {
            "source_commit": B0_SOURCE_COMMIT,
            "source_tree": B0_SOURCE_TREE,
            "topology_sha256": B0_TOPOLOGY_SHA256,
            "raw_warning_count": B0_MEMBER_COUNT,
            "membership_sha256": B0_MEMBERSHIP_SHA256,
            "compact_reproduction_file_sha256": WP0_COMPACT_REPRODUCTION_SHA256,
            "compact_reproduction_artifact_id": WP0_COMPACT_REPRODUCTION_ARTIFACT_ID,
        },
        "current_census": {
            "source_commit": baseline_main,
            "source_tree": current["tree"],
            "topology_sha256": current_topology,
            "raw_warning_count": len(current_rows),
            "classification_status": status["classification_status"],
            "zero_transition_debt_claim_prohibited": True,
        },
        "authority_effect": "NONE_READ_ONLY_SOURCE_EVIDENCE",
    }
    _write_json(docs_root / "GRT2_WP2_SOURCE_EVIDENCE_RECEIPT.json", source_receipt)

    merge_receipt = {
        "schema": "ovc-grt2-wp1-merge-receipt/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "GRT2-WP1",
        "pull_request": 754,
        "merge_commit": "49873c6e4efdb91d839b10b89ceb5f8fe76ee78d",
        "merge_tree": "059baf176bbc342af42d4d872d3d1bc8af877992",
        "decision": "PASS",
        "authority_effect": "NONE_PRE_ENFORCEMENT",
        "next_packet": "GRT2-WP2",
    }
    _write_json(docs_root / "GRT2_WP1_MERGE_RECEIPT.json", merge_receipt)

    return {
        "schema": "ovc-grt2-wp2-materialisation-result/v1",
        "b0_member_count": len(records),
        "b0_membership_sha256": baseline_membership_sha256(records),
        "current_warning_count": len(current_rows),
        "current_topology_sha256": current_topology,
        "classification_complete": False,
        "authority_effect": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--baseline-main", required=True)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--workflow-run-attempt", type=int)
    parser.add_argument("--trigger-commit")
    args = parser.parse_args()
    result = materialise(
        Path(args.repository_root),
        baseline_main=args.baseline_main,
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
        trigger_commit=args.trigger_commit,
    )
    print(canonical_json_v1_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
