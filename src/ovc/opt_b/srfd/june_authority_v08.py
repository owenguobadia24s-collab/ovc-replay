from __future__ import annotations

from typing import Any, Mapping

from .serialization import logical_sha256, stable_id
from .wp10_execution_resilience import RunBinding

PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v0.7"
GATE_ID = "SRFDI-G-JUNE-AUTH"
BASELINE_MAIN = "b1c481fd0d8d4ea476ebfbaab65b06b3d9d2c694"
STANDING_DELEGATION_MERGE = "682fdbf6893d37446926011d461157fbce5cf8f2"
RUNNER_IMPLEMENTATION_BINDING_SHA256 = "82a4817d006b73d3f4ac8232f3a3bf6cfbaa39b179ebc4f25ce4a8efec6c416a"
RUN_BINDING_SHA256 = "25f1c18d39898b5f2b5e9511245ecfd2615eb420205e68f9f1e8c7fe7f929fb9"
EXPECTED_TOKEN = "SRFD.JUNE.AUTH.7b9799d46cb6b3953fa9e96fb8309fbdeb0afe6dd53bfdcd16dec9cb85728ad0"
V07_TOKEN = "SRFD.JUNE.AUTH.baad8aa9752b789cea06f41c3bc134e86711a257f1219d04b4034a664a8f1ef5"
V06_TOKEN = "SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168"
V04_TOKEN = "SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686"
V05_TOKEN = "SRFD.JUNE.AUTH.eaa5a6e46365f673b796d4a966e600833f7528659b8528dc5f1ed27fd7cb5a1a"
V07_SUPERSESSION_SHA256 = "472341ea24166c51b304912cb9bb3646b95f6f81993ad77e92ce8d2c8c226ada"
DECISION_SHA256 = "0cd69e6d27f0f91d68dbd6308a0a4317ea84a79196f2c652528db683723b83a5"
ENVELOPE_SHA256 = "cf070fc765b410664f6ef6d65bdc3f8fd73ac3d773714b2de7446243cd797947"

POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
ELIGIBLE_IDS_SHA256 = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
SCIENTIFIC_MANIFEST_SHA256 = "6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb"
PREREGISTRATION_SHA256 = "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3"
REPRESENTATION_PACK_SHA256 = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
SEGMENTATION_PACK_SHA256 = "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0"
STABILITY_PACK_SHA256 = "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b"
SOURCE_BINDING_SHA256 = "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7"
CAPACITY_GRID_SHA256 = "68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866"
SOURCE_REVERIFY_SHA256 = "125ca24400390f36db0e79e7685f19e9b4fd506e299becf7c34b3123958f362c"


class RunnerBoundJuneAuthorityError(ValueError):
    pass


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise RunnerBoundJuneAuthorityError(detail)


def implementation_binding() -> dict[str, Any]:
    return {
        "schema": "ovc-srfd-wp10-v07-runner-implementation-binding/v1",
        "merge_commit_git_sha": BASELINE_MAIN,
        "construction_base_main": "9d42780d80bffe2326130d9c2f1fce357d249500",
        "runtime_blobs": {
            "existing_resilience": "073772c33f39afc63d8194d34e798aa3dbc9b61b",
            "durable_execution": "f1afc8b23a229aacf15da8f0d53fda70b46ae1c9",
            "contract_runtime": "1a140e544cfd7d74a90c980198eb1abe0186e1ec",
            "family_runtime": "63453b7ff88d8351eaeeeb1d2fbfe8189f76795b",
            "analysis_runtime": "4dd3e64b1041031e49cb81ddffe012e642f42b28",
            "production_runner": "47fbf10aeb7ba41ee91cd8638650522401fad82a",
        },
        "runtime_paths": {
            "existing_resilience": "src/ovc/opt_b/srfd/wp10_execution_resilience.py",
            "durable_execution": "src/ovc/opt_b/srfd/wp10_durable_execution.py",
            "contract_runtime": "src/ovc/opt_b/srfd/wp10_v07_contract.py",
            "family_runtime": "src/ovc/opt_b/srfd/wp10_v07_family.py",
            "analysis_runtime": "src/ovc/opt_b/srfd/wp10_v07_analysis.py",
            "production_runner": "src/ovc/opt_b/srfd/wp10_v07_runner.py",
        },
        "remediation_contract": "contracts/opt_b/srfd/SRFDI_WP10_V07_RUNNER_REMEDIATION_CONTRACT_v0_1.md",
        "remediation_profile": "registries/research/srfd/wp10_v07_runner_remediation_profile_v0_1.json",
        "exact_head_assurance": {
            "pr_number": 504,
            "tested_head_sha": "88bf3524e8e69daf46749ebd43b797fc84c29abe",
            "pr_repository_suite": "PASS",
            "pr_ovc_tiered_profile_compatibility": "PASS",
            "unresolved_review_threads": 0,
            "merge_commit": BASELINE_MAIN,
            "main_push_repository_suite": "PASS",
        },
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }


def build_run_binding() -> RunBinding:
    return RunBinding(
        programme_id=PROGRAMME_ID,
        packet_id=PACKET_ID,
        population_id=POPULATION_ID,
        eligible_ids_sha256=ELIGIBLE_IDS_SHA256,
        scientific_manifest_sha256=SCIENTIFIC_MANIFEST_SHA256,
        preregistration_sha256=PREREGISTRATION_SHA256,
        representation_pack_sha256=REPRESENTATION_PACK_SHA256,
        segmentation_pack_sha256=SEGMENTATION_PACK_SHA256,
        stability_pack_sha256=STABILITY_PACK_SHA256,
        source_binding_sha256=SOURCE_BINDING_SHA256,
        capacity_grid_sha256=CAPACITY_GRID_SHA256,
        implementation_commit=RUNNER_IMPLEMENTATION_BINDING_SHA256,
    )


def token_payload(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": decision["decision_id"],
        "decision_logical_sha256": logical_sha256(decision),
        "authority_envelope_logical_sha256": logical_sha256(envelope),
        "run_binding_sha256": RUN_BINDING_SHA256,
        "runner_implementation_binding_sha256": RUNNER_IMPLEMENTATION_BINDING_SHA256,
        "scientific_manifest_logical_sha256": SCIENTIFIC_MANIFEST_SHA256,
        "scientific_manifest_binding_sha256": "2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29",
        "capacity_backend_freeze_merge": "fcf8f2e84111c5c0920cb28816f95b00a9168d81",
        "capacity_catalog_grid_hash": CAPACITY_GRID_SHA256,
        "population_id": POPULATION_ID,
        "source_release_id": "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9",
        "prior_v0_4_token_id": V04_TOKEN,
        "prior_v0_4_token_state": "CONSUMED_NOT_REUSABLE",
        "attempted_v0_5_token_id": V05_TOKEN,
        "attempted_v0_5_token_state": "NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE",
        "prior_v0_6_token_id": V06_TOKEN,
        "prior_v0_6_token_state": "CONSUMED_NOT_REUSABLE",
        "prior_v0_7_token_id": V07_TOKEN,
        "prior_v0_7_token_state": "SUPERSEDED_UNUSED_UNCONSUMED",
    }


def reconstruct_token(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    payload = token_payload(decision, envelope)
    return {
        "schema": "ovc-srfd-june-run-authority-token/v8-runner-bound",
        "token_id": stable_id("SRFD.JUNE.AUTH.", payload),
        **payload,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_cardinality": "ONE_RUN_ID",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "reserved_authority": "NONE",
    }


def verify_runner_bound_june_authority(
    decision: Mapping[str, Any],
    envelope: Mapping[str, Any],
    token: Mapping[str, Any],
    source_reverification: Mapping[str, Any],
    supersession: Mapping[str, Any],
) -> dict[str, Any]:
    _require(logical_sha256(implementation_binding()) == RUNNER_IMPLEMENTATION_BINDING_SHA256, "runner implementation binding drift")
    _require(build_run_binding().logical_hash == RUN_BINDING_SHA256, "run binding drift")
    _require(logical_sha256(decision) == DECISION_SHA256, "decision drift")
    _require(logical_sha256(envelope) == ENVELOPE_SHA256, "envelope drift")
    _require(logical_sha256(supersession) == V07_SUPERSESSION_SHA256, "v0.7 supersession drift")
    _require(logical_sha256(source_reverification) == SOURCE_REVERIFY_SHA256, "source reverification drift")
    _require(source_reverification.get("all_exact") is True, "source artifacts not exact")
    _require(source_reverification.get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(source_reverification.get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")

    _require(decision.get("gate_id") == GATE_ID, "wrong gate")
    _require(decision.get("decision") == "AUTHORIZE_JUNE_RUN_SCOPED", "June run not authorized")
    _require(decision.get("decision_authority") == "DELEGATED_STANDING_OPERATOR_AUTHORITY", "wrong authority")
    _require(decision.get("baseline_main") == BASELINE_MAIN, "baseline main mismatch")
    _require(decision.get("standing_delegation", {}).get("merge_commit") == STANDING_DELEGATION_MERGE, "standing delegation mismatch")
    _require(decision.get("prerequisites", {}).get("prior_v0_7_token_state") == "SUPERSEDED_UNUSED_UNCONSUMED", "v0.7 token not superseded unused")
    _require(decision.get("runner_precondition", {}).get("implementation_binding_sha256") == RUNNER_IMPLEMENTATION_BINDING_SHA256, "runner binding mismatch")
    assurance = decision.get("runner_precondition", {}).get("exact_head_assurance", {})
    _require(assurance.get("pr_number") == 504, "wrong runner assurance PR")
    _require(assurance.get("repository_suite") == "PASS", "repository suite not passed")
    _require(assurance.get("ovc_tiered_profile_compatibility") == "PASS", "tiered compatibility not passed")
    _require(assurance.get("main_push_repository_suite") == "PASS", "merged-head suite not passed")
    _require(assurance.get("unresolved_review_threads") == 0, "review threads unresolved")

    _require(envelope.get("baseline_main") == BASELINE_MAIN, "envelope baseline mismatch")
    _require(envelope.get("run_binding") == build_run_binding().to_dict(), "envelope RunBinding drift")
    _require(envelope.get("run_binding_sha256") == RUN_BINDING_SHA256, "envelope run hash mismatch")
    _require(envelope.get("implementation_binding", {}).get("runner_implementation_binding_sha256") == RUNNER_IMPLEMENTATION_BINDING_SHA256, "envelope runner binding mismatch")
    _require(envelope.get("source_population_binding", {}).get("eligible_record_count") == 8598, "population count drift")
    _require(envelope.get("source_population_binding", {}).get("population_id") == POPULATION_ID, "population identity drift")
    _require(envelope.get("firewalls", {}).get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(envelope.get("firewalls", {}).get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")

    _require(supersession.get("superseded_token_id") == V07_TOKEN, "wrong superseded token")
    _require(supersession.get("superseded_token_consumed") is False, "v0.7 token consumption history changed")
    _require(supersession.get("superseded_token_new_state") == "SUPERSEDED_UNUSED_UNCONSUMED", "wrong v0.7 disposition")

    reconstructed = reconstruct_token(decision, envelope)
    _require(dict(token) == reconstructed, "v0.8 token reconstruction mismatch")
    _require(token.get("token_id") == EXPECTED_TOKEN, "unexpected v0.8 token identity")
    _require(token.get("run_binding_sha256") == RUN_BINDING_SHA256, "token run binding mismatch")
    _require(token.get("state") == "AUTHORIZED_UNCONSUMED" and token.get("single_use") is True, "token is not fresh single-use")
    return reconstructed
