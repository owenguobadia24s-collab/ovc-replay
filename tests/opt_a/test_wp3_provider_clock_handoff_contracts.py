from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "opt_a" / "wp3"
SCHEMAS = ROOT / "schemas" / "opt_a"
REGISTRY = ROOT / "registries" / "implementation" / "OPT_A_WP3_CONTRACT_REGISTRY.yaml"
SELECTORS = ROOT / "registries" / "releases" / "OPT_A_ACTIVE_SELECTORS.yaml"

SCHEMA_FILES = {
    "provider": "opt_a_provider_intake_record_v0_2.json",
    "source": "opt_a_source_object_identity_v0_2.json",
    "bar": "opt_a_observation_bar_v0_2.json",
    "reconciliation": "opt_a_reconciliation_record_v0_2.json",
    "handoff": "opt_a_to_opt_b_handoff_v0_2.json",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class WP3ProviderClockHandoffContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = load_json(FIXTURES / "PROVIDER_INTAKE_SAMPLE.json")
        cls.sources = load_json(FIXTURES / "SOURCE_OBJECT_SAMPLE.json")
        cls.clock = load_json(FIXTURES / "CLOCK_BOUNDARY_SAMPLE.json")
        cls.reconciliation = load_json(FIXTURES / "RECONCILIATION_SAMPLE.json")
        cls.handoff = load_json(FIXTURES / "HANDOFF_SAMPLE.json")
        cls.manifest = load_json(FIXTURES / "FIXTURE_MANIFEST.json")

    def test_all_machine_readable_schemas_parse_and_have_exact_ids(self) -> None:
        expected = {
            "provider": "ovc-opt-a-provider-intake-record/v2",
            "source": "ovc-opt-a-source-object-identity/v2",
            "bar": "ovc-opt-a-observation-bar/v2",
            "reconciliation": "ovc-opt-a-h1-reconciliation/v2",
            "handoff": "ovc-opt-a-to-opt-b-handoff/v2",
        }
        for key, filename in SCHEMA_FILES.items():
            schema = load_json(SCHEMAS / filename)
            self.assertEqual("object", schema["type"])
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(expected[key], schema["properties"]["schema"]["const"])

    def test_fixture_manifest_is_synthetic_and_files_exist(self) -> None:
        self.assertIs(self.manifest["synthetic"], True)
        self.assertEqual("NONE", self.manifest["market_authority"])
        self.assertEqual("DENIED", self.manifest["release_parent"])
        self.assertEqual("DENIED", self.manifest["selector_input"])
        for relative in self.manifest["files"]:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            load_json(path)

    def test_provider_fixture_covers_exact_four_native_source_families(self) -> None:
        records = self.provider["records"]
        families = {(record["native_timeframe"], record["price_side"]) for record in records}
        self.assertEqual({("M1", "BID"), ("M1", "ASK"), ("H1", "BID"), ("H1", "ASK")}, families)
        self.assertEqual(4, len(records))

    def test_provider_records_are_synthetic_non_authoritative_and_monthly(self) -> None:
        for record in self.provider["records"]:
            self.assertIs(record["synthetic"], True)
            self.assertEqual("DUKASCOPY", record["provider"])
            self.assertEqual("GBPUSD", record["instrument_id"])
            self.assertEqual("UTC", record["partition"]["timezone"])
            self.assertEqual("NONE", record["authority"]["market"])
            self.assertEqual("DENIED", record["authority"]["discovery_seed"])
            self.assertEqual("DENIED", record["authority"]["selector_input"])
            start = utc(record["partition"]["interval_start"])
            end = utc(record["partition"]["interval_end"])
            self.assertEqual((2021, 1, 1), (start.year, start.month, start.day))
            self.assertEqual((2021, 2, 1), (end.year, end.month, end.day))

    def test_source_object_identities_are_unique_and_role_bound(self) -> None:
        records = self.sources["records"]
        ids = [record["source_object_id"] for record in records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(4, len(ids))
        for record in records:
            self.assertTrue(record["source_object_id"].startswith("SRC.DUKASCOPY.GBPUSD."))
            self.assertEqual("DISCOVERY", record["research_role"])
            self.assertEqual("OPT-A.GBPUSD.DISCOVERY.2021_2023.v2", record["target_release_id"])
            self.assertNotIn("OPT-A.GBPUSD.2026H1.v1", record["source_object_id"])
            self.assertEqual("DENIED_UNTIL_FREEZE", record["authority"]["release_parent"])

    def test_a_l_clock_is_contiguous_fixed_utc_and_two_hours_each(self) -> None:
        boundaries = self.clock["a_l_boundaries"]
        self.assertEqual(list("ABCDEFGHIJKL"), [item["label"] for item in boundaries])
        self.assertEqual(12, len(boundaries))
        for index, item in enumerate(boundaries):
            start = utc(item["interval_start"])
            end = utc(item["interval_end"])
            self.assertEqual(7200, int((end - start).total_seconds()))
            if index:
                self.assertEqual(boundaries[index - 1]["interval_end"], item["interval_start"])
        self.assertEqual("2021-01-04T00:00:00Z", boundaries[0]["interval_start"])
        self.assertEqual("2021-01-05T00:00:00Z", boundaries[-1]["interval_end"])

    def test_exact_parent_counts_are_frozen(self) -> None:
        counts = {name: rule["expected_parent_count"] for name, rule in self.clock["bucket_rules"].items()}
        self.assertEqual(15, counts["M15_M1_DERIVED"])
        self.assertEqual(60, counts["H1_M1_DERIVED"])
        self.assertEqual(120, counts["H2_M1_CHAIN_DERIVED"])
        self.assertEqual(240, counts["H4_M1_CHAIN_DERIVED"])
        self.assertEqual(1440, counts["D1_M1_CHAIN_DERIVED"])

    def test_complete_bucket_requires_exact_timestamp_set(self) -> None:
        complete = next(case for case in self.clock["cases"] if case["case_id"] == "CLOCK-COMPLETE-M15")
        self.assertEqual(15, complete["expected_parent_count"])
        self.assertEqual(complete["expected_timestamps"], complete["actual_timestamps"])
        self.assertEqual("PASS", complete["qa_state"])

    def test_incomplete_bucket_is_quarantined_without_fill(self) -> None:
        incomplete = next(case for case in self.clock["cases"] if case["case_id"] == "CLOCK-INCOMPLETE-M15")
        self.assertEqual(14, incomplete["actual_parent_count"])
        self.assertEqual("QUARANTINE", incomplete["qa_state"])
        self.assertIn("EXPECTED_TIMESTAMP_MISSING", incomplete["reason_codes"])
        self.assertIn("INCOMPLETE_BUCKET", incomplete["reason_codes"])

    def test_provider_native_and_m1_derived_h1_are_distinct(self) -> None:
        case = next(case for case in self.clock["cases"] if case["case_id"] == "CLOCK-H1-IDENTITIES-DISTINCT")
        self.assertEqual(["H1_M1_DERIVED", "H1_PROVIDER_NATIVE"], case["identities"])
        self.assertEqual("PROHIBITED", case["substitution"])

    def test_reconciliation_preserves_match_and_mismatch_without_substitution(self) -> None:
        records = self.reconciliation["records"]
        self.assertEqual({"MATCH_EXACT", "OHLC_MISMATCH"}, {record["price_result"] for record in records})
        for record in records:
            self.assertEqual("PROHIBITED", record["authority"]["substitution"])
            self.assertEqual("NONE", record["authority"]["market"])
            self.assertIn(record["qa_state"], {"PASS", "WARN"})

    def test_handoff_fixture_is_draft_and_cannot_drive_opt_b(self) -> None:
        self.assertIs(self.handoff["synthetic"], True)
        self.assertEqual("DRAFT", self.handoff["lifecycle_state"])
        self.assertEqual("NONE", self.handoff["authority_state"])
        self.assertEqual("NONE", self.handoff["selector_state"])
        self.assertIn("OPT_B_REPLAY", self.handoff["downstream_prohibitions"])
        self.assertIn("SELECTOR_ACTIVATION", self.handoff["downstream_prohibitions"])
        self.assertIsNone(self.handoff["remote_verification_receipt_id"])

    def test_handoff_schema_binds_release_manifest_inventory_and_commit(self) -> None:
        schema = load_json(SCHEMAS / SCHEMA_FILES["handoff"])
        required = set(schema["required"])
        for field in (
            "release_id",
            "manifest_id",
            "source_commit",
            "release_manifest_sha256",
            "workspace_inventory_sha256",
            "contract_ids",
            "selector_state",
        ):
            self.assertIn(field, required)

    def test_validation_handoff_requires_non_default_consumption_state(self) -> None:
        schema = load_json(SCHEMAS / SCHEMA_FILES["handoff"])
        validation_rule = schema["allOf"][1]
        allowed = validation_rule["then"]["properties"]["validation_consumption_state"]["enum"]
        self.assertIn("LOCKED_UNCONSUMED", allowed)
        self.assertNotIn("NOT_APPLICABLE", allowed)

    def test_wp3_registry_freezes_role_split_and_all_selectors_none(self) -> None:
        text = REGISTRY.read_text(encoding="utf-8")
        for release_id in (
            "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
            "OPT-A.GBPUSD.VALIDATION.2025.v2",
        ):
            self.assertIn(release_id, text)
        self.assertEqual(3, text.count("selector: NONE"))
        self.assertIn("consumption_state: LOCKED_UNCONSUMED", text)
        self.assertIn("provider_execution: DENIED_UNTIL_A2_G0", text)
        self.assertIn("active_handoff: NONE", text)

    def test_wp1_selector_set_remains_inactive(self) -> None:
        text = SELECTORS.read_text(encoding="utf-8")
        self.assertIn("state: NONE", text)
        self.assertEqual(3, text.count("selector_state: NONE"))
        self.assertNotIn("selector_state: ACTIVE", text)
        self.assertIn("historical_v1_reactivation: PROHIBITED", text)

    def test_wp3_fixture_tree_contains_json_only(self) -> None:
        files = [path for path in FIXTURES.rglob("*") if path.is_file()]
        self.assertGreaterEqual(len(files), 6)
        self.assertTrue(all(path.suffix == ".json" for path in files))


if __name__ == "__main__":
    unittest.main()
