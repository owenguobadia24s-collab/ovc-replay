from __future__ import annotations

V10_TOKEN = "SRFD.JUNE.AUTH.ba38ee329eba42c169420bb328956777b3604de4db35308fa306a9bda8711927"
V10_BINDING = "e9f32060bb6f966db3a643192731bca1c13ed61e885c18e3cafda7e42b65a5ce"
V10_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_45_WP10_V10_START_AUTHORIZED.json"
V09_ROUTE = "BLOCKED_CAPACITY_EXTERNAL_BYTES_PRESERVED"
V11_TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
V11_BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"
V11_ENV_SUPERSEDED_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_50_WP10_V11_ENV_SUPERSEDED.json"
V11_ENV_V2 = "e08aaf02871d23979b47f2ce928b2098d775eab3e483ff3602db2794afa13eef"
V11_HARDENING_V2 = "445d4bb6646ad61b045b3cb0bd51078be194c7423277b23df52f8bc85b88d0d8"
V11_R3_TOKEN = "SRFD.JUNE.AUTH.7c464be44edb1f295efcf55481443a012176429ce6cc9689ce3f1e113b61c1e5"
V11_R3_BINDING = "735b49e435a71ee6129be75e182d4b4bfeda073f7d75e912b6ab711bc6420967"
V11_R3_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_51_WP10_V11_R3_AUTHORIZED.json"
V11_G10_STATE = "registries/implementation/srfd/OVC_SRFDI_STATE_v0_52_WP10_V11_R3_G10_COMPLETED.json"
V11_R3_RUN = "SRFD.RUN.55601cfe14d85173c767315be04c8b6c333dc8c07103a8064733086c26606dbf"


def assert_lawful_v10_pointer(testcase, pointer: dict) -> bool:
    """Accept exact lawful WP10 v1.0/v1.1 lineage through G10 completion."""
    if pointer.get("authoritative_state") == V11_G10_STATE:
        testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
        testcase.assertEqual("READY", pointer["status"])
        testcase.assertEqual("SRFDI-G11", pointer["current_gate"])
        testcase.assertEqual("SRFDI-WP11", pointer["active_packet"])
        testcase.assertEqual("DENIED", pointer["provider_fetch"])
        testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
        testcase.assertEqual("NONE", pointer["scientific_promotion"])
        testcase.assertEqual("NONE", pointer["selector_family_semantic_publication"])
        testcase.assertEqual("NONE", pointer["probability_risk_exposure_execution"])
        testcase.assertEqual(V09_ROUTE, pointer["wp10_v0_9_execution_route"])
        testcase.assertEqual("BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED", pointer["wp10_v1_0_execution_route"])
        testcase.assertEqual(V11_R3_TOKEN, pointer["fresh_authority_token_id"])
        testcase.assertTrue(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", pointer["fresh_authority_token_state"])
        testcase.assertEqual(V11_R3_RUN, pointer["fresh_run_id"])
        testcase.assertEqual(V11_R3_BINDING, pointer["run_binding_sha256"])
        testcase.assertEqual("COMPLETED_G10_PASS", pointer["wp10_v1_1_execution_route"])
        testcase.assertEqual(V11_TOKEN, pointer["superseded_v1_1_authority_token_id"])
        testcase.assertEqual(V11_BINDING, pointer["superseded_v1_1_run_binding_sha256"])
        testcase.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE", pointer["superseded_v1_1_authority_token_state"])
        testcase.assertEqual(V11_ENV_V2, pointer["v1_1_execution_environment_profile_sha256"])
        testcase.assertEqual(V11_HARDENING_V2, pointer["v1_1_hardening_rehearsal_sha256"])
        testcase.assertEqual("SRFDI-WP11", pointer["next_packet"])
        testcase.assertTrue(pointer["science_execution_started"])
        testcase.assertTrue(pointer["science_execution_complete"])
        return True
    if pointer.get("authoritative_state") == V11_R3_STATE:
        testcase.assertEqual("READY", pointer["status"])
        testcase.assertEqual(V11_R3_TOKEN, pointer["fresh_authority_token_id"])
        testcase.assertFalse(pointer["fresh_authority_token_consumed"])
        testcase.assertEqual(V11_R3_BINDING, pointer["run_binding_sha256"])
        testcase.assertFalse(pointer["science_execution_started"])
        return True
    if pointer.get("authoritative_state") == V11_ENV_SUPERSEDED_STATE:
        testcase.assertEqual("READY", pointer["status"])
        testcase.assertEqual(V11_TOKEN, pointer["superseded_v1_1_authority_token_id"])
        testcase.assertEqual(V11_BINDING, pointer["superseded_v1_1_run_binding_sha256"])
        testcase.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE", pointer["superseded_v1_1_authority_token_state"])
        return True
    route = pointer.get("wp10_v1_0_execution_route")
    if not route and pointer.get("authoritative_state") != V10_STATE:
        return False
    testcase.assertEqual("OVC-SRFD-BENCHMARK-v0.1", pointer["programme_id"])
    testcase.assertEqual("DENIED", pointer["provider_fetch"])
    testcase.assertEqual("LOCKED_UNCONSUMED", pointer["validation_2025"])
    testcase.assertEqual("NONE", pointer["scientific_promotion"])
    return True
