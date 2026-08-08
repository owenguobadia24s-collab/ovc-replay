from __future__ import annotations

from copy import deepcopy
import unittest

from ovc.opt_b.srfd import source_adapter as legacy_adapter
from ovc.opt_b.srfd import source_adapter_v02
from ovc.opt_b.srfd import june_authority_v02
from ovc.opt_b.srfd.june_authority import JuneAuthorityError
from ovc.opt_b.srfd.serialization import logical_sha256

SOURCE_MANIFEST = "1" * 64
OUTPUT_MANIFEST = "2" * 64
SOURCE_RECORD_HASHES = "3" * 64
DEPENDENCY_HASH = "4" * 64
ELIGIBLE_HASH = "5" * 64
CONTEXT_HASH = "6" * 64
EXCLUSION_HASH = "7" * 64


def binding() -> legacy_adapter.C2SourceBinding:
    return legacy_adapter.C2SourceBinding(
        source_release_id="PD-JUNE-FM.RUN.fixture",
        source_commit="source-commit",
        source_slice_id="RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1",
        source_manifest_sha256=SOURCE_MANIFEST,
        output_manifest_sha256=OUTPUT_MANIFEST,
        active_c2_model_release_id="OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        benchmark_start_inclusive_utc="2026-06-01T00:00:00Z",
        benchmark_end_exclusive_utc="2026-07-01T00:00:00Z",
        context_start_utc="2026-05-30T00:00:00Z",
        context_end_exclusive_utc="2026-07-03T00:00:00Z",
    )


def c1() -> dict[str, object]:
    return {
        "c1_record_id": "C1.1",
        "first_valid_time": "2026-06-10T00:15:00Z",
        "open_time": "2026-06-10T00:00:00Z",
        "close_time": "2026-06-10T00:15:00Z",
        "clock": "15M",
        "side": "BID",
        "source_slice_id": binding().source_slice_id,
        "source_manifest_sha256": SOURCE_MANIFEST,
        "eligibility_class": "TARGET_JUNE",
        "target_eligible": True,
        "operation_mode": "TIME_GATED_REPLAY",
        "role": "DISCOVERY",
    }


def c2() -> dict[str, object]:
    return {
        "active_c2_model_release_id": binding().active_c2_model_release_id,
        "axes": {
            "LOCATION": {"status": "EVALUATED", "value": "MID_REGION"},
            "MOTION": {"status": "EVALUATED", "value": "UP_STALL"},
            "ORGANISATION": {"status": "EVALUATED", "value": "FORMING"},
            "INTERACTION": {"status": "EVALUATED", "value": "APPROACHING"},
            "QUALITY": {"status": "EVALUATED", "value": "DEGRADED", "reason_code": "RELATION_EXCLUDED"},
        },
        "c1_manifest_id": "C1.MANIFEST",
        "c1_release_id": "C1.RELEASE",
        "c2_state_id": "C2.1",
        "clock": "15M",
        "container_ids": [],
        "continuity": "CONTIGUOUS",
        "eligibility_class": "TARGET_JUNE",
        "evaluation_scope_id": "GBPUSD-15M-LOCAL-v0.1",
        "first_valid_time": "2026-06-10T00:15:00Z",
        "level_ids": [],
        "live_prospective_append": "DENIED",
        "operation_mode": "TIME_GATED_REPLAY",
        "opt_a_manifest_id": "A.MANIFEST",
        "opt_a_release_id": "A.RELEASE",
        "parameter_pack_id": "C2.PACK",
        "parent_c1_record_id": "C1.1",
        "parent_opt_a_bar_id": "BAR.1",
        "persistence": {},
        "relation_set_id": "REL.1",
        "release_membership": False,
        "role": "DISCOVERY",
        "side": "BID",
        "source_slice_id": binding().source_slice_id,
        "target_eligible": True,
    }


def pending_manifest(implementation_commit: str = "impl-head") -> dict[str, object]:
    return {
        "schema": june_authority_v02.MANIFEST_SCHEMA,
        "programme_id": "OVC-SRFD-BENCHMARK-v0.1",
        "preregistration_id": june_authority_v02.PREREG_ID,
        "preregistration_byte_sha256": june_authority_v02.PREREG_BYTE_SHA256,
        "preregistration_logical_sha256": june_authority_v02.PREREG_LOGICAL_SHA256,
        "prerequisite_gate": june_authority_v02.PREREG_FREEZE_GATE,
        "representation_pack_registry": {
            "path": june_authority_v02.PACK_REGISTRY_PATH,
            "byte_sha256": june_authority_v02.PACK_REGISTRY_BYTE_SHA256,
            "logical_sha256": june_authority_v02.PACK_REGISTRY_LOGICAL_SHA256,
        },
        "run_authority_gate": june_authority_v02.GATE_ID,
        "run_authority": june_authority_v02.PENDING_RUN_STATE,
        "source_binding": {
            "source_release_id": "PD-JUNE-FM.RUN.fixture",
            "source_commit": "source-commit",
            "source_slice_id": "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1",
            "source_manifest_sha256": SOURCE_MANIFEST,
            "output_manifest_sha256": OUTPUT_MANIFEST,
            "source_record_hashes_sha256": SOURCE_RECORD_HASHES,
            "source_binding_sha256": "8" * 64,
            "provider_fetch": "FORBIDDEN",
            "upstream_mutation": "FORBIDDEN",
        },
        "population_binding": {
            "population_id": "SRFD.POP.fixture",
            "source_record_count": 2,
            "eligible_record_count": 1,
            "context_record_count": 1,
            "eligible_record_ids_sha256": ELIGIBLE_HASH,
            "context_record_ids_sha256": CONTEXT_HASH,
            "exclusion_count": 0,
            "exclusion_ledger_sha256": EXCLUSION_HASH,
            "historical_8598_reference": "MATCHED_EXACT_COUNT_AND_ID_HASH_NOW_BOUND",
        },
        "implementation_commit": implementation_commit,
        "dependency_manifest_hash": DEPENDENCY_HASH,
        "required_before_run_authority": {
            "source": {"exact_release_and_hash_binding": "PASS", "provider_fetch": "FORBIDDEN", "upstream_mutation": "FORBIDDEN"},
            "representation": {"pack_registry_hash_match": "PASS", "post_freeze_feature_selection": "FORBIDDEN"},
            "validation_2025": "LOCKED_UNCONSUMED",
            "selector_change": "NONE",
            "scientific_promotion": "NONE",
            "publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
        },
        "validation_2025": "LOCKED_UNCONSUMED",
        "selector_change": "NONE",
        "scientific_promotion": "NONE",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }


class SRFDIWP2DV02BindingTests(unittest.TestCase):
    def test_v02_preserves_accepted_evaluated_reason_without_reclassification(self) -> None:
        row = c2()
        parents = legacy_adapter.build_c1_parent_index([c1()], binding())
        with self.assertRaisesRegex(legacy_adapter.SourceAdapterError, "evaluated axis cannot carry reason"):
            legacy_adapter.adapt_c2_state(row, binding(), c1_parent_index=parents)
        adapted = source_adapter_v02.adapt_c2_state(row, binding(), c1_parent_index=parents)
        quality = adapted["native_c2"]["axes"]["QUALITY"]
        self.assertEqual("EVALUATED", quality["status"])
        self.assertEqual("DEGRADED", quality["value"])
        self.assertEqual("RELATION_EXCLUDED", quality["reason_code"])
        self.assertEqual("EVALUABLE", adapted["computability_status"])
        self.assertEqual(logical_sha256(row), adapted["source_logical_sha256"])

    def test_v02_population_is_order_independent_and_reason_is_audited(self) -> None:
        first = source_adapter_v02.bind_source_population([c2()], [c1()], binding())
        second = source_adapter_v02.bind_source_population(reversed([c2()]), reversed([c1()]), binding())
        self.assertEqual(first["population_id"], second["population_id"])
        self.assertEqual(1, first["eligible_record_count"])
        self.assertEqual(1, first["accepted_evaluated_reason_code_occurrences"])
        self.assertEqual({"EVALUABLE": 1}, first["computability_counts_within_eligible_population"])

    def test_v02_authority_verifier_requires_exact_frozen_prereg_and_pack_registry(self) -> None:
        pending = pending_manifest()
        binding_hash = june_authority_v02.manifest_binding_sha256(pending)
        decision = {
            "gate_id": june_authority_v02.GATE_ID,
            "decision": june_authority_v02.AUTHORIZED_DECISION,
            "decision_id": "SRFDI-G-JUNE-AUTH.OPERATOR.TEST",
            "authorized_manifest_sha256": binding_hash,
            "authority_effect": {
                "june_execution": "AUTHORIZED_BOUNDED_JUNE_BENCHMARK",
                "provider_fetch": "DENIED",
                "validation_2025": "LOCKED_UNCONSUMED",
                "scientific_promotion": "NONE",
                "selector_change": "NONE",
                "publication": "NONE",
                "probability_risk_exposure_execution": "NONE",
            },
        }
        authorized = deepcopy(pending)
        authorized["run_authority"] = june_authority_v02.AUTHORIZED_RUN_STATE
        decision_hash = logical_sha256(decision)
        authorized["authority_binding"] = {
            "gate_id": june_authority_v02.GATE_ID,
            "decision_id": decision["decision_id"],
            "decision_logical_sha256": decision_hash,
            "authorized_manifest_sha256": binding_hash,
        }
        token = june_authority_v02.verify_june_run_authority(decision, authorized, expected_implementation_commit="impl-head")
        june_authority_v02.guard_bounded_june_run(token, authorized)
        self.assertEqual("SRFD.POP.fixture", token.population_id)

        bad = deepcopy(authorized)
        bad["representation_pack_registry"]["logical_sha256"] = "0" * 64
        with self.assertRaisesRegex(JuneAuthorityError, "representation-pack registry hash mismatch"):
            june_authority_v02.verify_june_run_authority(decision, bad, expected_implementation_commit="impl-head")

    def test_v02_candidate_never_authorizes_without_operator_decision(self) -> None:
        with self.assertRaisesRegex(JuneAuthorityError, "operator decision is required"):
            june_authority_v02.verify_june_run_authority(None, pending_manifest(), expected_implementation_commit="impl-head")
        with self.assertRaisesRegex(JuneAuthorityError, "bounded June authority token required"):
            june_authority_v02.guard_bounded_june_run(None, pending_manifest())


if __name__ == "__main__":
    unittest.main()
