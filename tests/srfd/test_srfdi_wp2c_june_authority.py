from __future__ import annotations

from copy import deepcopy
import unittest

from ovc.opt_b.srfd.june_authority import (
    AUTHORIZED_RUN_STATE,
    JuneAuthorityError,
    guard_bounded_june_run,
    manifest_binding_sha256,
    verify_june_run_authority,
)
from ovc.opt_b.srfd.orchestration import OrchestrationError, authority_guard
from ovc.opt_b.srfd.serialization import logical_sha256


IMPLEMENTATION = "abc123"
DEPENDENCY_HASH = "d" * 64


def manifest() -> dict[str, object]:
    return {
        "schema": "ovc-srfdi-june-run-manifest-template/v1",
        "programme_id": "OVC-SRFD-BENCHMARK-v0.1",
        "packet_origin": "SRFDI-WP9",
        "authority_state": "AUTHORIZED_BOUNDED_RUN_ONLY",
        "preregistration": {
            "path": "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_1.json",
            "freeze_gate": "SRFDI-G9",
            "byte_sha256": "76a18f79596772343f398256582dab9c37e219d01345c606204230c554599792",
            "logical_sha256": "a832daad99b6df49199eced0c35632b15974f86b58a8e6481350294a87d3d32e",
        },
        "run_authority": AUTHORIZED_RUN_STATE,
        "run_authority_gate": "SRFDI-G-JUNE-AUTH",
        "validation_2025": "LOCKED_UNCONSUMED",
        "selector_change": "NONE",
        "scientific_promotion": "NONE",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
        "required_before_run_authority": {
            "source": {
                "provider_fetch": "FORBIDDEN",
                "upstream_mutation": "FORBIDDEN",
                "source_release_id": "PD-JUNE-FM.RUN.fixture",
                "source_commit": "fedc20ab",
                "source_hashes": ["1" * 64, "2" * 64],
            },
            "population": {
                "eligible_record_count": 8598,
                "eligible_record_ids_sha256": "3" * 64,
                "exclusion_count": 0,
                "exclusion_ledger_sha256": "4" * 64,
                "population_id": "SRFD.POP.fixture",
            },
            "code": {
                "implementation_commit": IMPLEMENTATION,
                "dependency_manifest_sha256": DEPENDENCY_HASH,
            },
            "qa": {
                "exact_preregistration_hash": "REQUIRED_MATCH",
                "pre_run_checks": "REQUIRED_PASS",
                "retrospective_isolation": "REQUIRED_PASS",
            },
            "rollback": {
                "checkpoint_resume": "BYTE_AND_LOGICAL_EQUIVALENCE_REQUIRED",
                "safe_cancellation": "REQUIRED",
                "upstream_mutation": "FORBIDDEN",
            },
            "candidate_sets": {"representation_ids": ["SRFDI-R1"]},
            "capacity": {"max_wall_seconds": 14400},
            "period": {
                "benchmark_start_inclusive_utc": "2026-06-01T00:00:00Z",
                "benchmark_end_exclusive_utc": "2026-07-01T00:00:00Z",
            },
        },
    }


def decision_for(value: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "ovc-srfdi-g-june-auth-decision/v1",
        "gate_id": "SRFDI-G-JUNE-AUTH",
        "decision_id": "SRFDI-G-JUNE-AUTH.OPERATOR.fixture",
        "decision": "AUTHORIZE_JUNE",
        "authorized_manifest_sha256": manifest_binding_sha256(value),
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


def authorized_pair() -> tuple[dict[str, object], dict[str, object]]:
    value = manifest()
    decision = decision_for(value)
    value["authority_binding"] = {
        "gate_id": "SRFDI-G-JUNE-AUTH",
        "decision_id": decision["decision_id"],
        "decision_logical_sha256": logical_sha256(decision),
        "authorized_manifest_sha256": manifest_binding_sha256(value),
    }
    return decision, value


class SRFDIWP2CJuneAuthorityTests(unittest.TestCase):
    def test_no_operator_decision_never_authorizes_june(self) -> None:
        with self.assertRaisesRegex(JuneAuthorityError, "AUTH_JUNE_NOT_AUTHORISED"):
            verify_june_run_authority(None, manifest(), expected_implementation_commit=IMPLEMENTATION)

    def test_exact_synthetic_authority_pair_can_emit_token_without_granting_real_authority(self) -> None:
        decision, value = authorized_pair()
        token = verify_june_run_authority(decision, value, expected_implementation_commit=IMPLEMENTATION)
        self.assertEqual(AUTHORIZED_RUN_STATE, token.authority_state)
        self.assertEqual("SRFD.POP.fixture", token.population_id)
        self.assertEqual("PD-JUNE-FM.RUN.fixture", token.source_release_id)
        guard_bounded_june_run(token, value)

    def test_manifest_and_decision_are_mutually_hash_bound(self) -> None:
        decision, value = authorized_pair()
        tampered = deepcopy(value)
        tampered["required_before_run_authority"]["population"]["eligible_record_count"] = 8597
        with self.assertRaisesRegex(JuneAuthorityError, "AUTH_JUNE_NOT_AUTHORISED"):
            verify_june_run_authority(decision, tampered, expected_implementation_commit=IMPLEMENTATION)

    def test_source_population_prereg_code_and_dependency_tampering_fail_closed(self) -> None:
        decision, value = authorized_pair()
        cases = []
        wrong_prereg = deepcopy(value)
        wrong_prereg["preregistration"]["logical_sha256"] = "0" * 64
        cases.append(wrong_prereg)
        wrong_source = deepcopy(value)
        wrong_source["required_before_run_authority"]["source"]["source_hashes"] = []
        cases.append(wrong_source)
        wrong_population = deepcopy(value)
        wrong_population["required_before_run_authority"]["population"]["eligible_record_ids_sha256"] = None
        cases.append(wrong_population)
        wrong_dependency = deepcopy(value)
        wrong_dependency["required_before_run_authority"]["code"]["dependency_manifest_sha256"] = "bad"
        cases.append(wrong_dependency)
        for item in cases:
            with self.subTest(item=item):
                with self.assertRaises(JuneAuthorityError):
                    verify_june_run_authority(decision, item, expected_implementation_commit=IMPLEMENTATION)
        with self.assertRaisesRegex(JuneAuthorityError, "implementation commit mismatch"):
            verify_june_run_authority(decision, value, expected_implementation_commit="other")

    def test_reserved_authority_changes_are_rejected(self) -> None:
        decision, value = authorized_pair()
        changed = deepcopy(decision)
        changed["authority_effect"]["selector_change"] = "AUTHORIZED"
        value2 = deepcopy(value)
        value2["authority_binding"]["decision_logical_sha256"] = logical_sha256(changed)
        with self.assertRaisesRegex(JuneAuthorityError, "AUTH_SCOPE_EXPANSION"):
            verify_june_run_authority(changed, value2, expected_implementation_commit=IMPLEMENTATION)

    def test_default_fixture_orchestration_guard_remains_denied(self) -> None:
        with self.assertRaisesRegex(OrchestrationError, "AUTH_JUNE_NOT_AUTHORISED"):
            authority_guard("june_market_benchmark")
        with self.assertRaisesRegex(JuneAuthorityError, "AUTH_JUNE_NOT_AUTHORISED"):
            guard_bounded_june_run(None, manifest())


if __name__ == "__main__":
    unittest.main()
