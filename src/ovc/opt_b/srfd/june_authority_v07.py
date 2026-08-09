from __future__ import annotations

from typing import Any, Mapping

from .serialization import logical_sha256, stable_id
from .wp10_execution_resilience import RunBinding

GATE_ID = "SRFDI-G-JUNE-AUTH"
PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v0.7"
AUTHORIZED_DECISION = "AUTHORIZE_JUNE_RUN_SCOPED"
DELEGATED_AUTHORITY = "DELEGATED_STANDING_OPERATOR_AUTHORITY"
BASELINE_MAIN = "d7098fa322257a95acfdfc5af0eb8279cdb9964a"
STANDING_DELEGATION_MERGE = "682fdbf6893d37446926011d461157fbce5cf8f2"
RESILIENCE_MODULE_BLOB = "073772c33f39afc63d8194d34e798aa3dbc9b61b"
RESILIENCE_BINDING_SHA256 = "d6b7d2181c932d8498be450814d1bf56ff544a9d2e74835a7bd4a3b1ea3c907b"
RUN_BINDING_SHA256 = "f2efdf3fb46d357211fa73b050ec75e7f13590582e0ed1b4791ff9e3a6665740"
EXPECTED_TOKEN = "SRFD.JUNE.AUTH.baad8aa9752b789cea06f41c3bc134e86711a257f1219d04b4034a664a8f1ef5"

CAPACITY_FREEZE_MERGE = "fcf8f2e84111c5c0920cb28816f95b00a9168d81"
CAPACITY_GRID_HASH = "68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866"
SCIENTIFIC_MANIFEST_HASH = "6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb"
SCIENTIFIC_MANIFEST_BINDING_HASH = "2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29"
PREREG_V04_HASH = "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3"
REP_PACK_HASH = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
SEGMENTATION_HASH = "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0"
STABILITY_HASH = "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b"
SOURCE_BINDING_HASH = "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7"
SOURCE_RECORD_HASHES = "1dc5fc46a872380409c42e5450d09e6426f3f1f7aaa82f2334bf998b03b88840"
SOURCE_REVERIFY_HASH = "125ca24400390f36db0e79e7685f19e9b4fd506e299becf7c34b3123958f362c"
POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
ELIGIBLE_IDS_HASH = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
PRIOR_V04_TOKEN = "SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686"
ATTEMPTED_V05_TOKEN = "SRFD.JUNE.AUTH.eaa5a6e46365f673b796d4a966e600833f7528659b8528dc5f1ed27fd7cb5a1a"
PRIOR_V06_TOKEN = "SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168"


class FreshJuneRunScopedAuthorityError(ValueError):
    pass


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise FreshJuneRunScopedAuthorityError(detail)


def implementation_binding() -> dict[str, str]:
    return {
        "merge_commit_git_sha": BASELINE_MAIN,
        "module_path": "src/ovc/opt_b/srfd/wp10_execution_resilience.py",
        "module_git_blob_sha": RESILIENCE_MODULE_BLOB,
        "resilience_profile": "registries/research/srfd/wp10_execution_resilience_profile_v0_1.json",
        "resilience_contract": "contracts/opt_b/srfd/SRFDI_WP10_EXECUTION_RESILIENCE_SUPERSESSION_CONTRACT_v0_1.md",
    }


def build_run_binding() -> RunBinding:
    return RunBinding(
        programme_id=PROGRAMME_ID,
        packet_id=PACKET_ID,
        population_id=POPULATION_ID,
        eligible_ids_sha256=ELIGIBLE_IDS_HASH,
        scientific_manifest_sha256=SCIENTIFIC_MANIFEST_HASH,
        preregistration_sha256=PREREG_V04_HASH,
        representation_pack_sha256=REP_PACK_HASH,
        segmentation_pack_sha256=SEGMENTATION_HASH,
        stability_pack_sha256=STABILITY_HASH,
        source_binding_sha256=SOURCE_BINDING_HASH,
        capacity_grid_sha256=CAPACITY_GRID_HASH,
        implementation_commit=RESILIENCE_BINDING_SHA256,
    )


def token_payload(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": decision["decision_id"],
        "decision_logical_sha256": logical_sha256(decision),
        "authority_envelope_logical_sha256": logical_sha256(envelope),
        "run_binding_sha256": RUN_BINDING_SHA256,
        "execution_resilience_binding_sha256": RESILIENCE_BINDING_SHA256,
        "scientific_manifest_logical_sha256": SCIENTIFIC_MANIFEST_HASH,
        "scientific_manifest_binding_sha256": SCIENTIFIC_MANIFEST_BINDING_HASH,
        "capacity_backend_freeze_merge": CAPACITY_FREEZE_MERGE,
        "capacity_catalog_grid_hash": CAPACITY_GRID_HASH,
        "population_id": POPULATION_ID,
        "source_release_id": "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9",
        "prior_v0_4_token_id": PRIOR_V04_TOKEN,
        "prior_v0_4_token_state": "CONSUMED_NOT_REUSABLE",
        "attempted_v0_5_token_id": ATTEMPTED_V05_TOKEN,
        "attempted_v0_5_token_state": "NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE",
        "prior_v0_6_token_id": PRIOR_V06_TOKEN,
        "prior_v0_6_token_state": "CONSUMED_NOT_REUSABLE",
    }


def reconstruct_token(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    payload = token_payload(decision, envelope)
    return {
        "schema": "ovc-srfd-june-run-authority-token/v7-run-scoped",
        "token_id": stable_id("SRFD.JUNE.AUTH.", payload),
        **payload,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_cardinality": "ONE_RUN_ID",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "reserved_authority": "NONE",
    }


def verify_fresh_june_run_scoped_authority(
    decision: Mapping[str, Any],
    envelope: Mapping[str, Any],
    token: Mapping[str, Any],
    source_reverification: Mapping[str, Any],
) -> dict[str, Any]:
    _require(decision.get("gate_id") == GATE_ID, "wrong gate")
    _require(decision.get("decision") == AUTHORIZED_DECISION, "June run not authorized")
    _require(decision.get("decision_authority") == DELEGATED_AUTHORITY, "wrong delegated authority")
    _require(decision.get("baseline_main") == BASELINE_MAIN, "baseline main mismatch")
    _require(decision.get("standing_delegation", {}).get("merge_commit") == STANDING_DELEGATION_MERGE, "standing delegation mismatch")

    impl = implementation_binding()
    _require(logical_sha256(impl) == RESILIENCE_BINDING_SHA256, "resilience implementation binding drift")
    _require(build_run_binding().logical_hash == RUN_BINDING_SHA256, "run binding drift")
    resilience = decision.get("resilience_precondition", {})
    _require(resilience.get("execution_resilience_merge") == BASELINE_MAIN, "resilience merge mismatch")
    _require(resilience.get("implementation_binding_sha256") == RESILIENCE_BINDING_SHA256, "resilience binding mismatch")
    _require(resilience.get("implementation_git_blob_sha") == RESILIENCE_MODULE_BLOB, "resilience module blob mismatch")
    _require(resilience.get("run_binding_sha256") == RUN_BINDING_SHA256, "decision run binding mismatch")
    assurance = resilience.get("exact_head_assurance", {})
    _require(assurance.get("pr_number") == 489, "wrong resilience assurance PR")
    _require(assurance.get("repository_suite") == "PASS", "repository assurance not passed")
    _require(assurance.get("ovc_tiered_profile_compatibility") == "PASS", "OVC assurance not passed")
    _require(assurance.get("unresolved_review_threads") == 0, "review threads unresolved")

    prereq = decision.get("prerequisites", {})
    expected = {
        "capacity_backend_freeze_merge": CAPACITY_FREEZE_MERGE,
        "capacity_catalog_grid_hash": CAPACITY_GRID_HASH,
        "scientific_manifest_logical_sha256": SCIENTIFIC_MANIFEST_HASH,
        "scientific_manifest_binding_sha256": SCIENTIFIC_MANIFEST_BINDING_HASH,
        "preregistration_v0_4_logical_sha256": PREREG_V04_HASH,
        "representation_pack_registry_logical_sha256": REP_PACK_HASH,
        "segmentation_registry_logical_sha256": SEGMENTATION_HASH,
        "stability_metric_registry_logical_sha256": STABILITY_HASH,
        "source_binding_sha256": SOURCE_BINDING_HASH,
        "source_record_hashes_sha256": SOURCE_RECORD_HASHES,
        "source_artifact_reverification_logical_sha256": SOURCE_REVERIFY_HASH,
        "population_id": POPULATION_ID,
        "eligible_record_count": 8598,
        "eligible_record_ids_sha256": ELIGIBLE_IDS_HASH,
        "comparability_domain_count": 36,
        "exact_pair_opportunity_count": 35380668,
        "family_configuration_count": 1944,
        "prior_v0_4_token_id": PRIOR_V04_TOKEN,
        "prior_v0_4_token_state": "CONSUMED_NOT_REUSABLE",
        "attempted_v0_5_token_id": ATTEMPTED_V05_TOKEN,
        "attempted_v0_5_token_state": "NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE",
        "prior_v0_6_token_id": PRIOR_V06_TOKEN,
        "prior_v0_6_token_state": "CONSUMED_NOT_REUSABLE",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
    }
    for key, value in expected.items():
        _require(prereq.get(key) == value, f"prerequisite mismatch:{key}")
    _require(prereq.get("source_artifact_reverification_mode") == "REUSE_IMMUTABLE_ACCEPTED_VERIFICATION_NO_PROVIDER_FETCH", "source reverification mode mismatch")

    _require(logical_sha256(source_reverification) == SOURCE_REVERIFY_HASH, "source reverification drift")
    _require(source_reverification.get("all_exact") is True, "source artifacts not exact")
    _require(source_reverification.get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(source_reverification.get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")

    _require(envelope.get("baseline_main") == BASELINE_MAIN, "envelope baseline mismatch")
    _require(envelope.get("run_binding_sha256") == RUN_BINDING_SHA256, "envelope run binding mismatch")
    _require(envelope.get("run_binding") == build_run_binding().to_dict(), "envelope RunBinding drift")
    _require(envelope.get("implementation_binding", {}).get("execution_resilience_binding_sha256") == RESILIENCE_BINDING_SHA256, "envelope implementation binding drift")
    _require(envelope.get("implementation_binding", {}).get("execution_resilience") == impl, "envelope implementation identity drift")
    source = envelope.get("source_population_binding", {})
    _require(source.get("source_record_count") == 9420 and source.get("eligible_record_count") == 8598, "population count drift")
    _require(source.get("population_id") == POPULATION_ID and source.get("eligible_record_ids_sha256") == ELIGIBLE_IDS_HASH, "population identity drift")
    _require(source.get("provider_fetch") == "FORBIDDEN" and source.get("upstream_mutation") == "FORBIDDEN", "source firewall widened")
    _require(envelope.get("firewalls", {}).get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(envelope.get("firewalls", {}).get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")

    reconstructed = reconstruct_token(decision, envelope)
    _require(dict(token) == reconstructed, "v0.7 token reconstruction mismatch")
    _require(token.get("token_id") == EXPECTED_TOKEN, "unexpected v0.7 token identity")
    _require(token.get("token_id") not in {PRIOR_V04_TOKEN, ATTEMPTED_V05_TOKEN, PRIOR_V06_TOKEN}, "prior token identity reused")
    _require(token.get("state") == "AUTHORIZED_UNCONSUMED" and token.get("single_use") is True, "v0.7 token not single-use unconsumed")
    _require(token.get("run_binding_sha256") == RUN_BINDING_SHA256, "token does not bind exact run")
    return reconstructed
