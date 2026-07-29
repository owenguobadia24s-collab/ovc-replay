from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.research_operations.v0_3 import (
    DOWNSTREAM_AUTHORITY_BANNER,
    LIVE_ROUTE_STATE,
    ProjectionContractError,
    ProjectionDenied,
    build_c1_console_projection,
    build_c1_fact_projection,
    build_c1_lineage_trace,
    build_downstream_trace_projection,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "fixtures/research_operations/v0_3/wp4_c1_lineage_projection_fixture.json"
SCHEMA_ROOT = ROOT / "schemas/research_operations/v0_3"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class RO3WP4LineageAdapterTests(unittest.TestCase):
    def build_valid(self, fixture: dict | None = None):
        source = deepcopy(fixture or FIXTURE)
        lineage = build_c1_lineage_trace(
            release_context=source["release_context"],
            c1_record=source["c1_record"],
        )
        fact = build_c1_fact_projection(
            release_context=source["release_context"],
            c1_record=source["c1_record"],
            formula_evidence=source["formula_evidence"],
            lineage_trace=lineage,
        )
        downstream = build_downstream_trace_projection(
            c1_record_id=source["c1_record"]["record_id"],
            child_references=source["child_references"],
        )
        console = build_c1_console_projection(
            release_context=source["release_context"],
            fact_projection=fact,
            computability_projection=source["computability_projection"],
            assurance_projection=source["assurance_projection"],
            lineage_trace=lineage,
            downstream_trace=downstream,
        )
        return lineage, fact, downstream, console

    def test_valid_source_bound_projection_is_disabled_read_only_and_separated(self) -> None:
        lineage, fact, downstream, console = self.build_valid()
        self.assertEqual(lineage["status"], "COMPLETE")
        self.assertEqual(lineage["authority"], "READ_ONLY_TRACE")
        self.assertEqual(fact["primitive_id"], "C1-WICK-BALANCE.v0.1")
        self.assertEqual(
            fact["output"],
            "-0.1428571428571428571428571428571429",
        )
        self.assertEqual(downstream["banner"], DOWNSTREAM_AUTHORITY_BANNER)
        self.assertEqual(downstream["c2_authority"], "UNCHANGED")
        self.assertEqual(downstream["pattern_discovery_authority"], "UNCHANGED")
        self.assertEqual(console["route_state"], LIVE_ROUTE_STATE)
        self.assertFalse(console["route_enabled"])
        self.assertEqual(console["live_consumption_authority"], "NONE_PENDING_RC_G4")
        self.assertEqual(console["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertTrue(console["read_only"])
        self.assertEqual(console["writes"], "NONE")
        self.assertNotEqual(
            console["panels"]["fact"]["panel_id"],
            console["panels"]["downstream_trace"]["panel_id"],
        )
        self.assertEqual(
            console["panel_separation"]["null_reason_and_c2_transition_compact_corender"],
            "DENIED",
        )

    def test_deterministic_identity_survives_mapping_and_child_order(self) -> None:
        original = deepcopy(FIXTURE)
        second_child = deepcopy(original["child_references"][0])
        second_child["child_id"] = "c2-state:fixture-read-only"
        second_child["child_type"] = "C2_STATE"
        original["child_references"].append(second_child)
        first = self.build_valid(original)

        reordered = deepcopy(original)
        reordered["release_context"] = dict(reversed(list(reordered["release_context"].items())))
        reordered["c1_record"] = dict(reversed(list(reordered["c1_record"].items())))
        reordered["formula_evidence"] = dict(reversed(list(reordered["formula_evidence"].items())))
        reordered["child_references"] = list(reversed(reordered["child_references"]))
        second = self.build_valid(reordered)
        self.assertEqual(first[0]["logical_sha256"], second[0]["logical_sha256"])
        self.assertEqual(first[1]["logical_sha256"], second[1]["logical_sha256"])
        self.assertEqual(first[2]["logical_sha256"], second[2]["logical_sha256"])
        self.assertEqual(first[3]["logical_sha256"], second[3]["logical_sha256"])

    def test_validation_is_denied_before_path_object_or_record_resolution(self) -> None:
        context = {"role": "VALIDATION"}
        with self.assertRaisesRegex(
            ProjectionDenied,
            "VALIDATION_DENY_BEFORE_PATH_OBJECT_OR_RECORD_RESOLUTION",
        ):
            build_c1_lineage_trace(release_context=context, c1_record={"paths": ["forbidden"]})

    def test_unknown_role_release_clock_side_and_instrument_fail_closed(self) -> None:
        for mutation in (
            lambda item: item["release_context"].update(role="UNKNOWN"),
            lambda item: item["release_context"].update(c1_release_id="UNAUTHORISED"),
            lambda item: item["release_context"].update(clock="H1"),
            lambda item: item["release_context"].update(side="MID"),
            lambda item: item["c1_record"].update(instrument="XAUUSD"),
        ):
            case = deepcopy(FIXTURE)
            mutation(case)
            with self.assertRaises((ProjectionDenied, ProjectionContractError)):
                build_c1_lineage_trace(
                    release_context=case["release_context"],
                    c1_record=case["c1_record"],
                )

    def test_missing_lineage_is_explicitly_blocking(self) -> None:
        case = deepcopy(FIXTURE)
        case["c1_record"]["source_lineage"]["parent_m1_bar_ids"] = []
        with self.assertRaisesRegex(ProjectionContractError, "source lineage is incomplete"):
            build_c1_lineage_trace(
                release_context=case["release_context"],
                c1_record=case["c1_record"],
            )

    def test_write_capability_is_rejected_recursively(self) -> None:
        lineage, fact, downstream, _ = self.build_valid()
        computability = deepcopy(FIXTURE["computability_projection"])
        computability["nested"] = {"selector_write": True}
        with self.assertRaisesRegex(ProjectionDenied, "READ_ONLY_PROJECTION_REQUIRED"):
            build_c1_console_projection(
                release_context=FIXTURE["release_context"],
                fact_projection=fact,
                computability_projection=computability,
                assurance_projection=FIXTURE["assurance_projection"],
                lineage_trace=lineage,
                downstream_trace=downstream,
            )

    def test_c1_null_and_c2_transition_cannot_share_fact_card(self) -> None:
        case = deepcopy(FIXTURE)
        case["formula_evidence"]["c2_transition"] = "FORBIDDEN"
        lineage = build_c1_lineage_trace(
            release_context=case["release_context"],
            c1_record=case["c1_record"],
        )
        with self.assertRaisesRegex(ProjectionDenied, "FACT_PANEL_MIXED_WITH_DOWNSTREAM_AUTHORITY"):
            build_c1_fact_projection(
                release_context=case["release_context"],
                c1_record=case["c1_record"],
                formula_evidence=case["formula_evidence"],
                lineage_trace=lineage,
            )

    def test_downstream_trace_rejects_scoring_tuning_and_null_reason(self) -> None:
        for forbidden in ("severity", "confidence", "score", "recommended_action", "null_reason"):
            reference = deepcopy(FIXTURE["child_references"][0])
            reference[forbidden] = "FORBIDDEN"
            with self.assertRaisesRegex(ProjectionDenied, "DOWNSTREAM_TRACE_PROHIBITED_PRESENTATION"):
                build_downstream_trace_projection(
                    c1_record_id=FIXTURE["c1_record"]["record_id"],
                    child_references=[reference],
                )

    def test_missing_downstream_refs_remain_trace_not_available(self) -> None:
        projection = build_downstream_trace_projection(
            c1_record_id=FIXTURE["c1_record"]["record_id"],
            child_references=[],
        )
        self.assertEqual(projection["status"], "TRACE_NOT_AVAILABLE")
        self.assertEqual(projection["child_references"], [])
        self.assertEqual(projection["banner"], DOWNSTREAM_AUTHORITY_BANNER)

    def test_stale_projection_is_visible_and_route_remains_disabled(self) -> None:
        case = deepcopy(FIXTURE)
        case["release_context"]["represented_commit"] = "stale-commit"
        _, _, _, console = self.build_valid(case)
        self.assertEqual(console["status"], "STALE_PROJECTION")
        self.assertFalse(console["route_enabled"])
        self.assertEqual(console["route_state"], "DISABLED_PENDING_RC_G4")

    def test_route_enable_attempt_before_rc_g4_is_blocked(self) -> None:
        case = deepcopy(FIXTURE)
        case["release_context"]["route_enabled"] = True
        with self.assertRaisesRegex(ProjectionDenied, "READ_ONLY_PROJECTION_REQUIRED"):
            self.build_valid(case)

    def test_projection_schemas_are_present_and_fail_closed(self) -> None:
        expected = {
            "c1_lineage_trace_v0_1.schema.json": "ovc-ro3-c1-lineage-trace/v1",
            "c1_formula_evidence_card_v0_1.schema.json": "ovc-ro3-c1-formula-evidence-card/v1",
            "downstream_trace_projection_v0_1.schema.json": "ovc-ro3-downstream-trace-projection/v1",
            "c1_console_projection_v0_1.schema.json": "ovc-ro3-c1-console-projection/v1",
        }
        for filename, schema_id in expected.items():
            schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
            self.assertFalse(schema["additionalProperties"])
            self.assertIn(schema_id, json.dumps(schema, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
