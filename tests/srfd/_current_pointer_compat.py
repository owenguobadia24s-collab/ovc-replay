from __future__ import annotations

V10_TOKEN = "SRFD.JUNE.AUTH.ba38ee329eba42c169420bb328956777b3604de4db35308fa306a9bda8711927"
V10_BINDING = "e9f32060bb6f966db3a643192731bca1c13ed61e885c18e3cafda7e42b65a5ce"
V10_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_45_WP10_V10_START_AUTHORIZED.json"
V09_ROUTE = "BLOCKED_CAPACITY_EXTERNAL_BYTES_PRESERVED"
V11_TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
V11_BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"
V11_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json"


def assert_lawful_v10_pointer(testcase, pointer: dict) -> bool:
    """Accept the exact lawful WP10 v1.0 lineage or its exact v1.1 authority-ready successor."""
    if pointer.get("active_packet") == "SRFDI-WP10-v1.1" or pointer.get("fresh_authority_token_id") == V11_TOKEN:
        testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
        testcase.assertEqual("READY", pointer["status"])
        testcase.assertEqual("SRFDI-G10", pointer["current_gate"])
        testcase.assertEqual(V11_STATE, pointer["authoritative_state"])
        testcase.assertEqual("DENIED", pointer["provider_fetch"])
        testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
        testcase.assertEqual("NONE", pointer["scientific_promotion"])
        testcase.assertEqual("NONE", pointer["selector_family_semantic_publication"])
        testcase.assertEqual("NONE", pointer["probability_risk_exposure_execution"])
        testcase.assertEqual(V09_ROUTE, pointer["wp10_v0_9_execution_route"])
        testcase.assertEqual("BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED", pointer["wp10_v1_0_execution_route"])
        testcase.assertEqual("AUTHORIZED_UNCONSUMED_PENDING_EXACT_PREFLIGHT", pointer["wp10_v1_1_execution_route"])
        testcase.assertEqual(V11_TOKEN, pointer["fresh_authority_token_id"])
        testcase.assertEqual(V11_BINDING, pointer["run_binding_sha256"])
        testcase.assertEqual("SRFDI-WP10-v1.1-PREFLIGHT-AND-RUN", pointer["next_packet"])
        testcase.assertFalse(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual("AUTHORIZED_UNCONSUMED", pointer["fresh_authority_token_state"])
        testcase.assertEqual("HARD_BLOCKER_OR_SRFDI_G11_OPERATOR_SCIENTIFIC_DISPOSITION", pointer["stop_at"])
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
