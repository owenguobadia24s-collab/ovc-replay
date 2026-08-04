from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.horizons import (
    CrossClockMapping,
    HorizonContractError,
    HorizonDefinition,
    assert_causal_store_record,
    build_benchmark_envelope,
    build_discrepancy_record,
    compact_membership_summary,
    default_horizon_templates,
    evaluate_horizon,
    horizon_from_mapping,
    require_cross_clock_mapping,
    typed_time_from_mapping,
    validate_history_capacity_metadata,
)
from ovc.opt_b.c2_vnext.observation import build_population, default_gbpusd_calendar

ROOT = Path(__file__).resolve().parents[4]


def evidence(start: str, end: str, side: str = "BID", **extra):
    return {
        "interval_start": start,
        "interval_end": end,
        "side": side,
        "source_record_id": f"SRC:{side}:{start}",
        "opt_a_release_id": "OPT-A.SYNTHETIC.v1",
        "opt_a_record_id": f"A:{side}:{start}",
        "c1_release_id": "C1.SYNTHETIC.v1",
        "c1_record_id": f"C1:{side}:{start}",
        **extra,
    }


def continuous_observations(count: int = 8):
    rows = []
    for index in range(count):
        start_minute = index * 15
        start_hour, start_remainder = divmod(start_minute, 60)
        end_minute = (index + 1) * 15
        end_hour, end_remainder = divmod(end_minute, 60)
        start = f"2026-01-05T{start_hour:02d}:{start_remainder:02d}:00Z"
        end = f"2026-01-05T{end_hour:02d}:{end_remainder:02d}:00Z"
        rows.append(evidence(start, end))
    return build_population(
        "2026-01-05T00:00:00Z",
        f"2026-01-05T{(count * 15) // 60:02d}:{(count * 15) % 60:02d}:00Z",
        instrument="GBPUSD",
        calendar=default_gbpusd_calendar(),
        evidence_rows=rows,
        sides=("BID",),
    )["observations"]


def definition(
    kind: str,
    *,
    horizon_id: str | None = None,
    count: int | None = None,
    semantic_type: str = "OBSERVATION_COUNT",
    unit: str = "OBSERVATION",
    parameters: dict | None = None,
    consumer_classes: tuple[str, ...] | None = None,
    causal_class: str | None = None,
    continuity_policy: str | None = None,
    benchmark_only: bool = False,
):
    causal_by_kind = {
        "CURRENT": "CAUSAL_CURRENT",
        "TRANSITION": "CAUSAL_BACKWARD",
        "TRAILING_COUNT": "CAUSAL_BACKWARD",
        "PAIRED_COMPARISON": "CAUSAL_BACKWARD",
        "CONFIRMATION_DELAY": "CAUSAL_BACKWARD",
        "RUN_LENGTH": "CAUSAL_BACKWARD",
        "AGE": "CAUSAL_AS_OF",
        "AS_OF_PARENT": "CAUSAL_AS_OF",
        "EVENT_RELATIVE_VARIABLE": "CAUSAL_EVENT_CLOSED",
        "FORWARD_OUTCOME": "RETROSPECTIVE_ONLY",
    }
    consumers_by_kind = {
        "CURRENT": ("C2_MEASUREMENT",),
        "TRANSITION": ("C2_TRANSITION",),
        "TRAILING_COUNT": ("C2_MEASUREMENT",),
        "PAIRED_COMPARISON": ("C2_MEASUREMENT",),
        "CONFIRMATION_DELAY": ("C2_LEVEL",),
        "RUN_LENGTH": ("C2_MEASUREMENT",),
        "AGE": ("C2_LEVEL",),
        "AS_OF_PARENT": ("C2_PARENT_CONTEXT",),
        "EVENT_RELATIVE_VARIABLE": ("RESEARCH_CAUSAL_READ",),
        "FORWARD_OUTCOME": ("RESEARCH_BENCHMARK",),
    }
    continuity_by_kind = {
        "CURRENT": "EXPLICIT_RESET_AWARE",
        "AGE": "EXPLICIT_RESET_AWARE",
        "AS_OF_PARENT": "NOT_APPLICABLE",
    }
    return HorizonDefinition(
        horizon_id=horizon_id or f"HORIZON.TEST.{kind}",
        kind=kind,
        semantic_type=semantic_type,
        unit=unit,
        grain="15M_C2_OBSERVATION",
        source_basis="SYNTHETIC_TEST",
        applicability_scope=("GBPUSD", "BID"),
        consumer_classes=consumer_classes or consumers_by_kind[kind],
        causal_class=causal_class or causal_by_kind[kind],
        continuity_policy=continuity_policy or continuity_by_kind.get(kind, "SAME_CONTINUITY_SEGMENT"),
        first_valid_rule="CURRENT_OR_FINAL_MEMBER_FIRST_VALID",
        version="r1",
        maturity="SHADOW_EXPERIMENT",
        clock_id="LATTICE.15M.UTC_0000.v1",
        count=count,
        parameters=parameters or {},
        template=False,
        benchmark_only=benchmark_only,
        canonical=False,
    )


class HorizonFoundationTests(unittest.TestCase):
    def test_typed_time_requires_full_semantics_and_bare_number_fails(self):
        with self.assertRaisesRegex(HorizonContractError, "BARE_TIME_VALUE_INVALID"):
            typed_time_from_mapping(6)  # type: ignore[arg-type]
        value = typed_time_from_mapping({
            "semantic_type": "OBSERVATION_COUNT",
            "value": 6,
            "unit": "OBSERVATION",
            "grain": "2H_C2_OBSERVATION",
            "version": "r1",
            "source_basis": "TEST",
            "applicability_scope": ["GBPUSD", "BID", "MOTION"],
        })
        self.assertEqual(6, value.value)
        self.assertTrue(value.typed_value_id.startswith("C2.TYPED_TIME."))

    def test_registry_has_exact_horizon_kinds_and_no_canonical_numeric_profile(self):
        templates = default_horizon_templates()
        self.assertEqual(
            {"CURRENT", "TRANSITION", "TRAILING_COUNT", "PAIRED_COMPARISON", "CONFIRMATION_DELAY", "RUN_LENGTH", "AGE", "AS_OF_PARENT", "EVENT_RELATIVE_VARIABLE", "FORWARD_OUTCOME"},
            {item.kind for item in templates},
        )
        self.assertTrue(all(not item.canonical for item in templates))
        self.assertTrue(next(item for item in templates if item.kind == "TRAILING_COUNT").template)
        self.assertTrue(next(item for item in templates if item.kind == "FORWARD_OUTCOME").benchmark_only)

    def test_current_transition_trailing_and_paired_memberships(self):
        observations = continuous_observations(8)
        current_id = observations[-1]["observation_id"]
        current = evaluate_horizon(definition("CURRENT"), observations, as_of_observation_id=current_id, consumer_class="C2_MEASUREMENT")
        transition = evaluate_horizon(definition("TRANSITION"), observations, as_of_observation_id=current_id, consumer_class="C2_TRANSITION")
        trailing = evaluate_horizon(definition("TRAILING_COUNT", count=4), observations, as_of_observation_id=current_id, consumer_class="C2_MEASUREMENT")
        paired = evaluate_horizon(definition("PAIRED_COMPARISON", parameters={"left_count": 2, "right_count": 2}), observations, as_of_observation_id=current_id, consumer_class="C2_MEASUREMENT")
        self.assertEqual(1, len(current["member_observation_ids"]))
        self.assertEqual(2, len(transition["member_observation_ids"]))
        self.assertEqual(4, len(trailing["member_observation_ids"]))
        self.assertEqual(2, len(paired["metadata"]["left_observation_ids"]))
        self.assertEqual(2, len(paired["metadata"]["right_observation_ids"]))
        for record in (current, transition, trailing, paired):
            self.assertEqual("COMPUTABLE", record["status"])
            assert_causal_store_record(record)

    def test_warmup_capacity_gap_and_closure_fail_closed_without_silent_skip(self):
        observations = continuous_observations(2)
        warmup = evaluate_horizon(definition("TRAILING_COUNT", count=4), observations, as_of_observation_id=observations[-1]["observation_id"], consumer_class="C2_MEASUREMENT")
        self.assertEqual("WARM_UP_INSUFFICIENT", warmup["reason"])
        capacity = evaluate_horizon(definition("TRAILING_COUNT", count=4), continuous_observations(6), as_of_observation_id=continuous_observations(6)[-1]["observation_id"], consumer_class="C2_MEASUREMENT", history_capacity=2)
        self.assertEqual("HISTORY_CAPACITY_INSUFFICIENT", capacity["reason"])
        rows = [
            evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z"),
            evidence("2026-01-05T00:30:00Z", "2026-01-05T00:45:00Z"),
        ]
        gapped = build_population("2026-01-05T00:00:00Z", "2026-01-05T00:45:00Z", instrument="GBPUSD", calendar=default_gbpusd_calendar(), evidence_rows=rows, sides=("BID",))["observations"]
        gap_record = evaluate_horizon(definition("TRAILING_COUNT", count=2), gapped, as_of_observation_id=gapped[-1]["observation_id"], consumer_class="C2_MEASUREMENT")
        self.assertEqual("GAP_OR_RESET", gap_record["reason"])
        synthetic = copy.deepcopy(continuous_observations(3))
        synthetic[-2]["projection_eligibility"]["eligible"] = False
        synthetic[-2]["continuity"] = {"status": "CLOSURE_BOUNDARY", "segment_id": None}
        synthetic[-1]["continuity"] = {"status": "SEGMENT_START", "segment_id": "SEGMENT.NEW"}
        closure_record = evaluate_horizon(definition("TRAILING_COUNT", count=2), synthetic, as_of_observation_id=synthetic[-1]["observation_id"], consumer_class="C2_MEASUREMENT")
        self.assertEqual("CLOSURE_BOUNDARY", closure_record["reason"])
        self.assertEqual([], closure_record["member_observation_ids"])

    def test_confirmation_run_age_parent_and_event_semantics_are_separate(self):
        observations = continuous_observations(6)
        current_id = observations[-1]["observation_id"]
        anchor_id = observations[-4]["observation_id"]
        confirmation = evaluate_horizon(definition("CONFIRMATION_DELAY", count=2), observations, as_of_observation_id=current_id, consumer_class="C2_LEVEL", anchor_observation_id=anchor_id)
        not_met = evaluate_horizon(definition("CONFIRMATION_DELAY", count=4), observations, as_of_observation_id=current_id, consumer_class="C2_LEVEL", anchor_observation_id=anchor_id)
        predicates = {item["observation_id"]: index >= 3 for index, item in enumerate(observations)}
        run = evaluate_horizon(definition("RUN_LENGTH"), observations, as_of_observation_id=current_id, consumer_class="C2_MEASUREMENT", predicates=predicates)
        age_count = evaluate_horizon(definition("AGE"), observations, as_of_observation_id=current_id, consumer_class="C2_LEVEL", anchor_observation_id=anchor_id)
        age_duration = evaluate_horizon(definition("AGE", semantic_type="CALENDAR_DURATION", unit="MINUTE"), observations, as_of_observation_id=current_id, consumer_class="C2_LEVEL", anchor_observation_id=anchor_id)
        parent = evaluate_horizon(definition("AS_OF_PARENT"), observations, as_of_observation_id=current_id, consumer_class="C2_PARENT_CONTEXT", parent={"parent_id": "PARENT.1", "first_valid_time": observations[-3]["first_valid_time"]})
        parent_future = evaluate_horizon(definition("AS_OF_PARENT"), observations, as_of_observation_id=current_id, consumer_class="C2_PARENT_CONTEXT", parent={"parent_id": "PARENT.FUTURE", "first_valid_time": "2026-01-05T03:00:00Z"})
        event = evaluate_horizon(definition("EVENT_RELATIVE_VARIABLE"), observations, as_of_observation_id=current_id, consumer_class="RESEARCH_CAUSAL_READ", event={"event_id": "EVENT.1", "first_valid_time": observations[-4]["first_valid_time"], "start_observation_id": anchor_id, "end_first_valid_time": observations[-1]["first_valid_time"]})
        event_future = evaluate_horizon(definition("EVENT_RELATIVE_VARIABLE"), observations, as_of_observation_id=current_id, consumer_class="RESEARCH_CAUSAL_READ", event={"event_id": "EVENT.FUTURE", "first_valid_time": "2026-01-05T03:00:00Z", "start_observation_id": anchor_id})
        self.assertEqual("COMPUTABLE", confirmation["status"])
        self.assertEqual("CONFIRMATION_DELAY_NOT_MET", not_met["reason"])
        self.assertEqual(3, run["metadata"]["run_length"])
        self.assertEqual(3, age_count["metadata"]["age"]["value"])
        self.assertEqual(45.0, age_duration["metadata"]["age"]["value"])
        self.assertEqual("PARENT.1", parent["metadata"]["parent_id"])
        self.assertEqual("PARENT_NOT_AVAILABLE_AS_OF", parent_future["reason"])
        self.assertEqual(4, len(event["member_observation_ids"]))
        self.assertEqual("EVENT_NOT_AVAILABLE_AS_OF", event_future["reason"])

    def test_forward_outcome_is_benchmark_only_and_causal_store_guard_blocks_it(self):
        observations = continuous_observations(8)
        as_of = observations[3]["observation_id"]
        forward = definition("FORWARD_OUTCOME", count=2, benchmark_only=True)
        with self.assertRaisesRegex(HorizonContractError, "CONSUMER_NOT_ALLOWED|RETROSPECTIVE_ONLY"):
            evaluate_horizon(forward, observations, as_of_observation_id=as_of, consumer_class="C2_MEASUREMENT", benchmark_mode=True)
        membership = evaluate_horizon(forward, observations, as_of_observation_id=as_of, consumer_class="RESEARCH_BENCHMARK", benchmark_mode=True)
        self.assertEqual("BENCHMARK_ONLY", membership["status"])
        self.assertFalse(membership["causal_store_eligible"])
        self.assertGreater(membership["available_at"], membership["as_of_first_valid_time"])
        envelope = build_benchmark_envelope(membership, source_population_id="POP.SYNTHETIC", method_id="CEAR-ER1.METHOD.FORWARD_OUTCOME_LABEL", comparator_id="COMPARATOR.SYNTHETIC")
        self.assertTrue(envelope["benchmark_only"])
        with self.assertRaisesRegex(HorizonContractError, "CAUSAL_STORE"):
            assert_causal_store_record(membership)
        with self.assertRaisesRegex(HorizonContractError, "CAUSAL_STORE"):
            assert_causal_store_record(envelope)

    def test_cross_clock_mapping_is_explicit_and_never_automatic(self):
        with self.assertRaisesRegex(HorizonContractError, "AUTOMATIC_CROSS_CLOCK_EQUIVALENCE_DENIED"):
            CrossClockMapping("MAP.BAD", "H1", "H2", "ELAPSED_DURATION", "REGISTERED_SHADOW", "TEST", automatic_equivalence=True)
        with self.assertRaisesRegex(HorizonContractError, "CLOCK_MAPPING_REQUIRED"):
            require_cross_clock_mapping("H1", "H2", [])
        mapping = CrossClockMapping("MAP.1", "H1", "H2", "STRUCTURAL_DEPTH", "REGISTERED_SHADOW", "P2-Q2")
        with self.assertRaisesRegex(HorizonContractError, "CLOCK_MAPPING_NOT_APPROVED"):
            require_cross_clock_mapping("H1", "H2", [mapping])
        self.assertEqual(mapping, require_cross_clock_mapping("H1", "H2", [mapping], allow_shadow=True))

    def test_history_capacity_is_metadata_not_measurement_horizon(self):
        value = validate_history_capacity_metadata({"capacity": 64, "is_measurement_horizon": False, "selection_effect": "NONE"})
        self.assertEqual(64, value["capacity"])
        with self.assertRaisesRegex(HorizonContractError, "HISTORY_CAPACITY_IS_NOT_HORIZON"):
            validate_history_capacity_metadata({"capacity": 64, "is_measurement_horizon": True, "selection_effect": "NONE"})
        with self.assertRaisesRegex(HorizonContractError, "HORIZON_KIND"):
            HorizonDefinition("HISTORY.BAD", "HISTORY_CAPACITY", "OBSERVATION_COUNT", "OBSERVATION", "15M", "TEST", ("GBPUSD",), ("C2_MEASUREMENT",), "CAUSAL_BACKWARD", "SAME_CONTINUITY_SEGMENT", "CURRENT", "r1")

    def test_motion_and_organisation_discrepancies_are_separately_reproducible(self):
        motion = build_discrepancy_record(domain="MOTION", declared={"detail": 8, "parent": 6}, implemented={"behavior": "PREVIOUS_CLOSE_TRANSITION"}, redesign_candidate={"candidate_counts": [4, 8, 16], "canonical": False}, source_refs=["legacy-contract", "legacy-code"])
        organisation = build_discrepancy_record(domain="ORGANISATION", declared={"detail": 16, "parent": 12}, implemented={"behavior": "CURRENT_BAR_RANGE"}, redesign_candidate={"selection": "NONE"}, source_refs=["legacy-contract", "legacy-code"])
        self.assertNotEqual(motion["discrepancy_id"], organisation["discrepancy_id"])
        self.assertNotEqual(motion["reproduction_sha256"], organisation["reproduction_sha256"])
        self.assertFalse(motion["canonical_numeric_selection"])
        self.assertFalse(organisation["automatic_reconciliation"])
        again = build_discrepancy_record(domain="MOTION", declared={"detail": 8, "parent": 6}, implemented={"behavior": "PREVIOUS_CLOSE_TRANSITION"}, redesign_candidate={"candidate_counts": [4, 8, 16], "canonical": False}, source_refs=["legacy-contract", "legacy-code"])
        self.assertEqual(motion, again)

    def test_definition_mapping_and_membership_summary_are_deterministic(self):
        source = definition("TRAILING_COUNT", count=3).to_dict()
        rebuilt = horizon_from_mapping(source)
        self.assertEqual(source, rebuilt.to_dict())
        observations = continuous_observations(4)
        records = [
            evaluate_horizon(rebuilt, observations, as_of_observation_id=observations[-1]["observation_id"], consumer_class="C2_MEASUREMENT"),
            evaluate_horizon(definition("TRAILING_COUNT", count=8), observations, as_of_observation_id=observations[-1]["observation_id"], consumer_class="C2_MEASUREMENT"),
        ]
        first = compact_membership_summary(records)
        second = compact_membership_summary(copy.deepcopy(records))
        self.assertEqual(first, second)
        self.assertEqual({"COMPUTABLE": 1, "NOT_COMPUTABLE": 1}, first["status_counts"])

    def test_repository_contract_schema_registries_ledgers_and_fixture_are_complete(self):
        contract = (ROOT / "contracts/opt_b/c2/C2_HORIZON_AND_DISCREPANCY_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for decision in [f"P2-D{n}" for n in range(1, 12)] + [f"P2-Q{n}" for n in range(1, 5)]:
            self.assertIn(decision, contract)
        self.assertIn("exact original P2-D11 label is unavailable", contract)
        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_HORIZON_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertEqual(6, len(schema["schemas"]))
        self.assertIn("CENTERED_WINDOW", schema["prohibited_definition_kinds"])
        for value in schema["schemas"].values():
            self.assertFalse(value["additionalProperties"])
        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_HORIZON_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual("NONE", registry["canonical_numeric_selection"])
        self.assertEqual(10, len(registry["templates"]))
        self.assertTrue(all(item["canonical"] is False for item in registry["templates"] + registry["candidate_definitions"]))
        reasons = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_HORIZON_REASON_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertIn("HISTORY_CAPACITY_IS_NOT_HORIZON", {item["reason"] for item in reasons["reasons"]})
        ledgers = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_HORIZON_GOVERNANCE_LEDGERS_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual({"MOTION", "ORGANISATION"}, {item["domain"] for item in ledgers["discrepancy_ledger"]})
        self.assertTrue(all(item["automatic_equivalence"] is False for item in ledgers["cross_clock_mapping_ledger"]))
        er1 = json.loads((ROOT / "registries/opt_b/c2/vnext/CEAR_ER1_SOURCE_AND_METHOD_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertFalse(er1["completeness"]["exact_external_bibliography_imported"])
        self.assertEqual("SOURCE_PACKET_BYTES_UNAVAILABLE_AND_NO_SILENT_RECONSTRUCTION", er1["completeness"]["reason"])
        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/horizon_foundation_cases_v0_1.json").read_text(encoding="utf-8"))
        required_cases = {"TRAILING_WARM_UP", "TRAILING_GAP_RESET", "TRAILING_CLOSURE", "CONFIRMATION_DELAY_MET", "RUN_LENGTH", "AGE_OBSERVATION_COUNT", "AS_OF_PARENT_FUTURE", "CROSS_CLOCK_MAPPING_REQUIRED", "FORWARD_OUTCOME_CAUSAL_CONSUMER_BLOCK", "MOTION_DISCREPANCY", "ORGANISATION_DISCREPANCY"}
        self.assertTrue(required_cases.issubset({item["case_id"] for item in fixture["cases"]}))
        self.assertFalse(fixture["market_data"])


if __name__ == "__main__":
    unittest.main()
