from __future__ import annotations

V10_TOKEN = "SRFD.JUNE.AUTH.ba38ee329eba42c169420bb328956777b3604de4db35308fa306a9bda8711927"
V10_BINDING = "e9f32060bb6f966db3a643192731bca1c13ed61e885c18e3cafda7e42b65a5ce"
V10_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_45_WP10_V10_START_AUTHORIZED.json"
V09_ROUTE = "BLOCKED_CAPACITY_EXTERNAL_BYTES_PRESERVED"
V11_TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
V11_BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"
V11_READY_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json"
V11_BLOCKED_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json"
V11_ENV_SUPERSEDED_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_50_WP10_V11_ENV_SUPERSEDED.json"
V11_ENV_V2 = "e08aaf02871d23979b47f2ce928b2098d775eab3e483ff3602db2794afa13eef"
V11_HARDENING_V2 = "445d4bb6646ad61b045b3cb0bd51078be194c7423277b23df52f8bc85b88d0d8"


def assert_lawful_v10_pointer(testcase, pointer: dict) -> bool:
    """Accept exact lawful WP10 v1.0/v1.1 lineage, including env-profile supersession."""
    if pointer.get("authoritative_state") == V11_ENV_SUPERSEDED_STATE:
        testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
        testcase.assertEqual("READY", pointer["status"])
        testcase.assertEqual("SRFDI-G10", pointer["current_gate"])
        testcase.assertEqual("SRFDI-WP10-v1.1-ENVIRONMENT-SUPERSESSION", pointer["active_packet"])
        testcase.assertEqual("DENIED", pointer["provider_fetch"])
        testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
        testcase.assertEqual("NONE", pointer["scientific_promotion"])
        testcase.assertEqual("NONE", pointer["selector_family_semantic_publication"])
        testcase.assertEqual("NONE", pointer["probability_risk_exposure_execution"])
        testcase.assertEqual(V09_ROUTE, pointer["wp10_v0_9_execution_route"])
        testcase.assertEqual("BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED", pointer["wp10_v1_0_execution_route"])
        testcase.assertEqual(V11_TOKEN, pointer["superseded_v1_1_authority_token_id"])
        testcase.assertEqual(V11_BINDING, pointer["supersed_v1_1_1_run_binding_sha256"])
        testcase.assertFalse(pointer["superseded_v1_1_authority_token_consumed"])
        testcase.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE", pointer["superseded_v1_1_authority_token_state"])
        testcase.assertIsNone(pointer["fresh_authority_token_id"])
        testcase.assertFalse(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual("NONE_PENDING_POST_MERGE_REGENERATION", pointer["fresh_authority_token_state"])
        testcase.assertEqual(V11_ENV_V2, pointer["v1_1_execution_environment_profile_sha256"])
        testcase.assertEqual(V11_HARDENING_V2, pointer["v1_1_hardening_rehearsal_sha256"])
        testcase.assertEqual("SRFDI-WP10-v1.1-FRESH-AUTHORITY-REGENERATION", pointer["next_packet"])
        testcase.assertEqual("FRESH_AUTHORITY_REGENERATION_BOUNDARY", pointer["stop_at"])
        testcase.assertFalse(pointer["operator_decision_required"])
        return True

    if pointer.get("active_packet") == "SRFDI-WP10-v1.1" or pointer.get("fresh_authority_token_id") == V11_TOKEN:
        testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
        testcase.assertIn(pointer["status"], {"READY", "BLOCKED"})
        testcase.assertEqual("SRFDI-G10", pointer["current_gate"])
        testcase.assertEqual("DENIED", pointer["provider_fetch"])
        testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
        testcase.assertEqual("NONE", pointer["scientific_promotion"])
        testcase.assertEqual("NONE", pointer["selector_family_semantic_publication"])
        testcase.assertEqual("NONE", pointer["probability_risk_exposure_execution"])
        testcase.assertEqual(V09_ROUTE, pointer["wp10_v0_9_execution_route"])
        testcase.assertEqual("BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED", pointer["wp10_v1_0_execution_route"])
        testcase.assertEqual(V11_TOKEN, pointer["fresh_authority_token_id"])
        testcase.assertEqual(V11_BINDING, pointer["run_binding_sha256"])
        testcase.assertFalse(pointer["fresh_authority_token_consumed"])
        if pointer["status"] == "READY":
            testcase.assertEqual(V11_READY_STATE, pointer["authoritative_state"])
            testcase.assertEqual("AUTHORIZED_UNCONSUMED_PENDING_EXACT_PREFLIGHT", pointer["wp10_v1_1_execution_route"])
            testcase.assertEqual("SRFDI-WP10-v1.1-PREFLIGHT-AND-RUN", pointer["next_packet"])
            testcase.assertEqual("AUTHORIZED_UNCONSUMED", pointer["fresh_authority_token_state"])
            testcase.assertEqual("HARD_BLOCKER_OR_SRFDI_G11_OPERATOR_SCIENTIFIC_DISPOSITION", pointer["stop_at"])
        else:
            testcase.assertEqual(V11_BLOCKED_STATE, pointer["authoritative_state"])
            testcase.assertEqual("BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT_TOKEN_UNCONSUMED", pointer["wp10_v1_1_execution_route"])
            testcase.assertEqual("SRFDI-WP10-v1.1-ENVIRONMENT-REMEDIATION-OR-SUPERSESSION", pointer["next_packet"])
            testcase.assertEqual("AUTHORIZED_UNCONSUMED_BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT", pointer["fresh_authority_token_state"])
            testcase.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH_DEPENDENCY_INVENTORY", pointer["failure_reason"])
            testcase.assertEqual("HARD_BLOCKER", pointer["stop_at"])
            testcase.assertTrue(pointer["operator_decision_required"])
        return True

    route = pointer.get("wp10_v1_0_execution_route")
    state = pointer.get("authoritative_state")
    if not route and state != V10_STATE:
        return False
    testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
    testcase.assertIn(pointer["status"], {
        "RUN_START_AUTHORIZED_PREFLIGHT_PASS", "RUNNING", "QA_REVIEW",
        "APPROVED", "APPROVED_PENDING_MERGE", "COMPLETED", "BLOCKED",
    })
    testcase.assertIn(pointer.get("current_gate"), {"SRFDI-G10", "SRFDI-G11", None})
    testcase.assertEqual("DENIED", pointer["provider_fetch"])
    testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
    testcase.assertEqual("NONE", pointer["scientific_promotion"])
    testcase.assertEqual("NONE", pointer["selector_family_semantic_publication"])
    testcase.assertEqual("NONE", pointer["probability_risk_exposure_execution"])
    testcase.assertEqual(V09_ROUTE, pointer["wp10_v0_9_execution_route"])
    testcase.assertEqual(V10_TOKEN, pointer["fresh_authority_token_id"])
    testcase.assertEqual(V10_BINDING, pointer["run_binding_sha256"])
    if pointer["status"] == "RUN_START_AUTHORIZED_PREFLIGHT_PASS":
        testcase.assertEqual(V10_STATE, pointer["authoritative_state"])
        testcase.assertEqual("SRFDI-WP10-v1.0", pointer["next_packet"])
        testcase.assertFalse(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual("AUTHORIZED_UNCONSUMED", pointer["fresh_authority_token_state"])
        testcase.assertIsNone(pointer["run_id"])
        testcase.assertEqual(0, pointer["run_completed_unit_count"])
        testcase.assertEqual(2020, pointer["run_remaining_unit_count"])
    elif pointer["status"] in {"RUNNING", "QA_REVIEW", "APPROVED", "APPROVED_PENDING_MERGE", "COMPLETED", "BLOCKED"}:
        testcase.assertTrue(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", pointer["fresh_authority_token_state"])
    return True
