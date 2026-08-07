from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.market_grammar.episode_ledger import C2LedgerInput
from ovc.opt_b.market_grammar.revised_c2_adapter import (
    ADAPTER_ID,
    EmpiricalBinding,
    RevisedC2AdapterError,
    adapt_revised_c2_row,
    adapt_revised_c2_rows,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/market_grammar/ei_wp1/revised_c2_adapter_cases.json"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MG_EI_JUNE_PROGRAMME_STATE_v0_1.jsonc"
REGISTRY = ROOT / "registries/opt_b/market_grammar/MG_EI_WP1_IMPLEMENTATION_REGISTRY_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/market_grammar/mg_ei_wp1_revised_c2_source_row_v0_1.schema.json"
QA = ROOT / "docs/releases/market-grammar-empirical-integration-june-v0-1/ei-wp1/EI_WP1_QA_PACKET.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


class RevisedC2AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load(FIXTURE)
        cls.binding = EmpiricalBinding.from_mapping(cls.fixture["binding"])
        cls.rows = cls.fixture["rows"]

    def test_valid_rows_map_to_exact_c2ledger_contract(self) -> None:
        result = adapt_revised_c2_rows(self.rows, binding=self.binding, build_cutoff=self.fixture["build_cutoff"])
        self.assertEqual(ADAPTER_ID, result["adapter_id"])
        self.assertEqual("SHADOW_EXPERIMENT", result["authority_state"])
        self.assertFalse(result["canonical"])
        self.assertFalse(result["published"])
        self.assertEqual("NONE", result["promotion_authority"])
        self.assertEqual(3, result["record_count"])
        for item in result["records"]:
            C2LedgerInput.from_mapping(item)
            self.assertEqual("C2AR.INTEGRATED.SHADOW.PACKAGE.v1", item["source_release_id"])
            self.assertEqual("GBPUSD", item["instrument_id"])
            self.assertEqual("15M", item["clock_id"])
            self.assertEqual("GBPUSD-15M-LOCAL-v0.1", item["scope_id"])

    def test_five_axis_state_key_is_categorical_and_measurement_free(self) -> None:
        item = adapt_revised_c2_row(self.rows[0], binding=self.binding)
        self.assertEqual(
            "LOCATION=EVALUATED:LOWER_REGION|MOTION=EVALUATED:UP_STALL|ORGANISATION=EVALUATED:FORMING|INTERACTION=EVALUATED:APPROACHING|QUALITY=EVALUATED:COMPLETE",
            item["state_key"],
        )
        self.assertNotIn("0.25", item["state_key"])
        self.assertNotIn("machine", json.dumps(item).lower())
        self.assertNotIn("path", json.dumps(item).lower())
        self.assertEqual("NONE", item["transition_kind"])
        self.assertEqual("EVALUABLE", item["computability_status"])
        self.assertIsNone(item["not_evaluable_reason"])

    def test_computability_precedence_preserves_all_negative_axis_evidence(self) -> None:
        item = adapt_revised_c2_row(self.rows[1], binding=self.binding)
        self.assertEqual("NOT_EVALUABLE", item["computability_status"])
        self.assertEqual("AXIS_CHANGE", item["transition_kind"])
        reason = item["not_evaluable_reason"]
        self.assertIn("MOTION:NOT_EVALUATED:NO_CONTIGUOUS_PRIOR_STATE", reason)
        self.assertIn("INTERACTION:NOT_EVALUABLE:AMBIGUOUS_BOUNDARY", reason)
        self.assertNotIn("NEUTRAL", reason)

    def test_reset_and_parent_context_are_passed_without_semantic_completion(self) -> None:
        item = adapt_revised_c2_row(self.rows[2], binding=self.binding)
        self.assertEqual("EI.WP1.2H.ASK.001", item["parent_record_id"])
        self.assertEqual("SOURCE_CONTINUITY_GAP", item["reset_reason"])
        self.assertEqual("AXIS_CHANGE", item["transition_kind"])
        self.assertNotEqual("COMPLETION", item["transition_kind"])

    def test_order_runtime_metadata_and_measurements_do_not_change_adapted_identity(self) -> None:
        first = adapt_revised_c2_rows(self.rows, binding=self.binding, build_cutoff=self.fixture["build_cutoff"])
        mutated = copy.deepcopy(list(reversed(self.rows)))
        for index, row in enumerate(mutated):
            row["diagnostic_metadata"] = {"machine_name": f"different-{index}", "local_path": f"/tmp/{index}"}
            for axis in row["axes"].values():
                if axis.get("measurement") is not None:
                    axis["measurement"] = "999999"
        second = adapt_revised_c2_rows(mutated, binding=self.binding, build_cutoff=self.fixture["build_cutoff"])
        self.assertEqual(first["logical_sha256"], second["logical_sha256"])
        self.assertEqual(first["records"], second["records"])

    def test_binding_hashes_fail_closed(self) -> None:
        bad = dict(self.fixture["binding"])
        bad["binding_sha256"] = "0" * 64
        with self.assertRaisesRegex(RevisedC2AdapterError, "BINDING_SHA256_MISMATCH"):
            EmpiricalBinding.from_mapping(bad)
        bad = dict(self.fixture["binding"])
        bad["logical_population_sha256"] = "0" * 64
        with self.assertRaisesRegex(RevisedC2AdapterError, "LOGICAL_POPULATION_SHA256_MISMATCH"):
            EmpiricalBinding.from_mapping(bad)

    def test_forbidden_future_outcome_family_and_grammar_fields_fail_closed(self) -> None:
        for field in ("outcome", "future_path", "family_id", "grammar_id", "probability", "risk", "exposure", "execution"):
            row = copy.deepcopy(self.rows[0])
            row[field] = "FORBIDDEN"
            with self.subTest(field=field), self.assertRaisesRegex(RevisedC2AdapterError, "FORBIDDEN_SOURCE_FIELDS"):
                adapt_revised_c2_row(row, binding=self.binding)

    def test_unknown_fields_and_wrong_scope_fail_closed(self) -> None:
        row = copy.deepcopy(self.rows[0]); row["mystery"] = 1
        with self.assertRaisesRegex(RevisedC2AdapterError, "UNKNOWN_SOURCE_FIELDS"):
            adapt_revised_c2_row(row, binding=self.binding)
        for field, value, marker in (
            ("instrument_id", "EURUSD", "INSTRUMENT_SCOPE_MISMATCH"),
            ("side", "MID", "SIDE_SCOPE_MISMATCH"),
            ("clock_id", "2H_A_L", "CLOCK_SCOPE_MISMATCH"),
            ("evaluation_scope_id", "GBPUSD-15M-OTHER", "EVALUATION_SCOPE_MISMATCH"),
            ("source_release_id", "OTHER", "ROW_SOURCE_RELEASE_ID_MISMATCH"),
        ):
            row = copy.deepcopy(self.rows[0]); row[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(RevisedC2AdapterError, marker):
                adapt_revised_c2_row(row, binding=self.binding)

    def test_parent_reset_and_axis_missingness_rules_fail_closed(self) -> None:
        row = copy.deepcopy(self.rows[0]); row["parent_clock_id"] = "15M"
        with self.assertRaisesRegex(RevisedC2AdapterError, "PARENT_CLOCK_SCOPE_MISMATCH"):
            adapt_revised_c2_row(row, binding=self.binding)
        row = copy.deepcopy(self.rows[0]); row["continuity_status"] = "GAP_RESET"; row["reset_reason"] = None
        with self.assertRaisesRegex(RevisedC2AdapterError, "RESET_CONTINUITY_REQUIRES_REASON"):
            adapt_revised_c2_row(row, binding=self.binding)
        row = copy.deepcopy(self.rows[0]); row["axes"]["LOCATION"]["status"] = "NOT_EVALUABLE"; row["axes"]["LOCATION"]["reason_code"] = None
        with self.assertRaisesRegex(RevisedC2AdapterError, "NON_EVALUATED_AXIS_REQUIRES_REASON"):
            adapt_revised_c2_row(row, binding=self.binding)
        row = copy.deepcopy(self.rows[0]); del row["axes"]["QUALITY"]
        with self.assertRaisesRegex(RevisedC2AdapterError, "AXIS_SET_MISMATCH"):
            adapt_revised_c2_row(row, binding=self.binding)

    def test_cutoff_duplicates_and_timestamp_ambiguity_fail_closed(self) -> None:
        with self.assertRaisesRegex(RevisedC2AdapterError, "SOURCE_ROW_EXCEEDS_BUILD_CUTOFF"):
            adapt_revised_c2_rows(self.rows, binding=self.binding, build_cutoff="2026-06-01T00:30:00Z")
        duplicate = [copy.deepcopy(self.rows[0]), copy.deepcopy(self.rows[0])]
        with self.assertRaisesRegex(RevisedC2AdapterError, "DUPLICATE_RECORD_ID"):
            adapt_revised_c2_rows(duplicate, binding=self.binding, build_cutoff=self.fixture["build_cutoff"])
        ambiguous = [copy.deepcopy(self.rows[0]), copy.deepcopy(self.rows[1])]
        ambiguous[1]["first_valid_time"] = ambiguous[0]["first_valid_time"]
        with self.assertRaisesRegex(RevisedC2AdapterError, "DUPLICATE_FIRST_VALID_TIME_WITHIN_EXACT_SCOPE"):
            adapt_revised_c2_rows(ambiguous, binding=self.binding, build_cutoff=self.fixture["build_cutoff"])

    def test_schema_registry_qa_and_programme_state_are_read_only(self) -> None:
        schema = load(SCHEMA); registry = load(REGISTRY); qa = load(QA); state = load(STATE)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(registry["selector_controls"])
        self.assertFalse(registry["canonical_controls"])
        self.assertFalse(registry["promotion_controls"])
        self.assertFalse(registry["publication_controls"])
        self.assertEqual("NONE", registry["promotion_authority"])
        self.assertEqual([], qa["blockers"])
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["EI-WP0"]["status"])
        self.assertIn(packets["EI-WP1"]["status"], {"RUNNING", "IMPLEMENTED", "QA_REVIEW", "APPROVED", "COMPLETED"})
        self.assertIn(packets["EI-WP2"]["status"], {"RUNNING", "IMPLEMENTED", "QA_REVIEW", "APPROVED", "COMPLETED"})


if __name__ == "__main__":
    unittest.main()
