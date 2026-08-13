from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import (
    BootstrapValidationError,
    load_json,
    validate_instance,
    validate_schema,
)
from ovc.programme_genesis.grt_v0_2.debt import (
    B0_MEMBERSHIP_SHA256,
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    baseline_membership_sha256,
    classify_debt_transition,
    compare_debt_extent,
    finding_id,
    make_finding,
    make_lineage,
    propose_debt_floor,
    validate_baseline_member_record,
    validate_baseline_members,
    validate_debt_baseline,
    validate_debt_floor,
    validate_lineage,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "registries/governance/grt_v0_2/baseline"
SCHEMAS = ROOT / "schemas/governance/grt_v0_2"
DOCS = ROOT / "docs/programmes/grt-v0-2/wp2"
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/wp2/debt_mechanics_fixture.json"


def rows() -> list[dict]:
    return [
        json.loads(line)
        for line in (BASE / "GRT_B0_BASELINE_MEMBERS_v0_1.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]


class GRT2WP2BaselineTests(unittest.TestCase):
    def test_wp2_schemas_are_bootstrap_valid(self) -> None:
        for name in (
            "baseline_member_record.schema.json",
            "grt_debt_baseline.schema.json",
            "grt_finding_record.schema.json",
            "lineage.schema.json",
            "debt_floor.schema.json",
        ):
            validate_schema(load_json(SCHEMAS / name))

    def test_exact_b0_population(self) -> None:
        data = rows()
        schema = load_json(SCHEMAS / "baseline_member_record.schema.json")
        self.assertEqual(len(data), 569)
        for row in data:
            validate_baseline_member_record(row, schema)
        validate_baseline_members(data)
        self.assertEqual(baseline_membership_sha256(data), B0_MEMBERSHIP_SHA256)
        self.assertEqual(len({row["original_GRT_anomaly"] for row in data}), 569)
        self.assertEqual(len({row["payload_hash"] for row in data}), 569)
        self.assertEqual([row["ordinal"] for row in data], list(range(1, 570)))

    def test_baseline_is_source_bound_and_unmapped_until_wp3a(self) -> None:
        data = rows()
        baseline = load_json(BASE / "GRT_DEBT_BASELINE_B0.json")
        validate_debt_baseline(
            baseline,
            data,
            load_json(SCHEMAS / "grt_debt_baseline.schema.json"),
        )
        self.assertEqual(baseline["source_commit"], B0_SOURCE_COMMIT)
        self.assertEqual(baseline["source_tree_hash"], B0_SOURCE_TREE)
        self.assertEqual(baseline["source_topology_sha256"], B0_TOPOLOGY_SHA256)
        self.assertEqual(
            baseline["constitution_mapping_status"],
            "PENDING_WP3_ARTIFACT_GRAPH",
        )
        self.assertTrue(
            all(row["mapping_status"] == "PENDING_WP3_ARTIFACT_GRAPH" for row in data)
        )
        self.assertTrue(all(row["mapped_finding_id"] is None for row in data))
        self.assertTrue(all(row["disposition"] is None for row in data))
        self.assertTrue(all(row["lineage_refs"] == [] for row in data))
        self.assertTrue(
            all(any(json.loads(row["original_subject_locator"]).values()) for row in data)
        )

    def test_finding_identity_is_exact_and_noise_free(self) -> None:
        params = load_json(FIXTURE)["finding"]
        expected_projection = {
            "constitution_rule_id": params["rule_id"],
            "subject_artifact_id": params["subject_artifact_id"],
            "relation_role": params["relation_role"],
            "relevant_counterparty_identity": params["counterparty_identity"],
        }
        expected = "GRT.FIND." + canonical_sha256(expected_projection)[:24]
        self.assertEqual(
            finding_id(
                params["rule_id"],
                params["subject_artifact_id"],
                params["relation_role"],
                params["counterparty_identity"],
            ),
            expected,
        )
        finding = make_finding(
            rule_id=params["rule_id"],
            subject_artifact_id=params["subject_artifact_id"],
            relation_role=params["relation_role"],
            counterparty_identity=params["counterparty_identity"],
            debt_extent=params["debt_extent"],
            first_seen_tree=params["first_seen_tree"],
            applicability_evidence=["A", "A"],
            violation_evidence=["V"],
        )
        validate_instance(finding, load_json(SCHEMAS / "grt_finding_record.schema.json"))
        self.assertEqual(finding["finding_id"], expected)
        self.assertNotIn("message", finding)
        self.assertNotIn("timestamp", finding)
        self.assertNotIn("pull_request", finding)
        self.assertNotIn("branch", finding)

    def test_extent_comparator_and_admission_matrix(self) -> None:
        fixture = load_json(FIXTURE)
        for case in fixture["extent_cases"]:
            self.assertEqual(
                compare_debt_extent(case["previous"], case["current"]),
                case["expected"],
            )
        for case in fixture["admission_cases"]:
            actual = classify_debt_transition(
                predecessor_state=case["predecessor_state"],
                candidate_state=case["candidate_state"],
                extent_result=case.get("extent_result"),
                related_identity=case.get("related_identity", True),
            )
            self.assertEqual(list(actual), case["expected"])

    def test_lineage_is_deterministic_and_fail_closed(self) -> None:
        first = make_finding(
            rule_id="GRT-R001",
            subject_artifact_id="repo://A",
            relation_role="PRIMARY",
            debt_extent={"count": 1},
            first_seen_tree="1" * 40,
        )["finding_id"]
        second = make_finding(
            rule_id="GRT-R001",
            subject_artifact_id="repo://B",
            relation_role="PRIMARY",
            debt_extent={"count": 1},
            first_seen_tree="2" * 40,
        )["finding_id"]
        lineage = make_lineage([first], [second], "MOVE", ["proof:1"])
        validate_lineage(lineage)
        validate_instance(lineage, load_json(SCHEMAS / "lineage.schema.json"))
        self.assertEqual(lineage, make_lineage([first], [second], "MOVE", ["proof:1"]))
        bad = dict(lineage)
        bad["canonical_hash"] = "0" * 64
        with self.assertRaisesRegex(BootstrapValidationError, "LINEAGE_HASH_MISMATCH"):
            validate_lineage(bad)
        with self.assertRaisesRegex(BootstrapValidationError, "LINEAGE_KIND_INVALID"):
            make_lineage([first], [second], "SILENT_RECLASSIFICATION", ["proof:1"])

    def test_debt_floor_mechanics_are_monotonic_but_generation_zero_is_not_committed(self) -> None:
        constitution = load_json(
            ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json"
        )
        first = propose_debt_floor(
            generation=0,
            predecessor_commit="1" * 40,
            predecessor_tree="2" * 40,
            constitution_hash=constitution["canonical_hash"],
            open_grandfathered_findings=["F1", "F2"],
        )
        validate_debt_floor(first)
        validate_instance(first, load_json(SCHEMAS / "debt_floor.schema.json"))
        second = propose_debt_floor(
            generation=1,
            predecessor_commit="3" * 40,
            predecessor_tree="4" * 40,
            constitution_hash=constitution["canonical_hash"],
            open_grandfathered_findings=["F2"],
            previous_floor=first,
            permanently_resolved_finding_ids=["F1"],
        )
        validate_debt_floor(second)
        with self.assertRaisesRegex(BootstrapValidationError, "GRANDFATHERED_SET_GREW"):
            propose_debt_floor(
                generation=2,
                predecessor_commit="5" * 40,
                predecessor_tree="6" * 40,
                constitution_hash=constitution["canonical_hash"],
                open_grandfathered_findings=["F1", "F2"],
                previous_floor=second,
            )
        self.assertFalse((BASE / "GRT_DEBT_FLOOR_G0.json").exists())

    def test_migration_and_current_status_do_not_overclaim_pre_wp3a(self) -> None:
        migration = load_json(BASE / "GRT_B0_TO_V0_2_MIGRATION_v0_1.json")
        status = load_json(DOCS / "GRT2_WP2_CURRENT_CLASSIFICATION_STATUS.json")
        self.assertEqual(migration["member_count"], 569)
        self.assertEqual(migration["mapped_count"], 0)
        self.assertEqual(migration["pending_count"], 569)
        self.assertTrue(migration["zero_mapping_claim_prohibited"])
        self.assertEqual(status["raw_warning_count"], 601)
        self.assertFalse(status["classification_complete"])
        self.assertEqual(
            status["classification_status"],
            "NOT_EVALUABLE_UNTIL_WP3A_V0_2_SCANNER_AND_ARTIFACT_GRAPH",
        )
        self.assertTrue(status["empty_ledgers_are_not_zero_debt_evidence"])
        self.assertTrue(status["zero_transition_debt_claim_prohibited"])
        self.assertEqual(
            (BASE / "GRT_LATE_PREEXISTING_FINDINGS.jsonl").read_text(encoding="utf-8"),
            "",
        )
        self.assertEqual(
            (BASE / "GRT_PRE_G3_TRANSITION_DEBT.jsonl").read_text(encoding="utf-8"),
            "",
        )
        self.assertFalse(
            (ROOT / ".github/workflows/grt2-wp2-materialise-records-temp.yml").exists()
        )


if __name__ == "__main__":
    unittest.main()
