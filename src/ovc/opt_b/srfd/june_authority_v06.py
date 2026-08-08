from __future__ import annotations

from typing import Any, Mapping

from .serialization import logical_sha256, stable_id

GATE_ID = "SRFDI-G-JUNE-AUTH"
AUTHORIZED_DECISION = "AUTHORIZE_JUNE"
DELEGATED_AUTHORITY = "DELEGATED_STANDING_OPERATOR_AUTHORITY"
BASELINE_MAIN = "cea693980a69fb2211172bcac28065867ccc6401"
STANDING_DELEGATION_MERGE = "682fdbf6893d37446926011d461157fbce5cf8f2"
SFC_TERMINAL_MERGE = BASELINE_MAIN
SFC_INTERLOCK_RELEASE = "RELEASED_FOR_FUTURE_SEPARATELY_GOVERNED_SRFD_PREPARATION_ONLY"
G10A_CLOSEOUT_MERGE = "52840ed3828d17b88b0ef0c9228c2061620f63c3"
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
SOURCE_ARTIFACT_REVERIFICATION_HASH = "125ca24400390f36db0e79e7685f19e9b4fd506e299becf7c34b3123958f362c"
POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
ELIGIBLE_IDS_HASH = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
PRIOR_V04_TOKEN = "SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686"
ATTEMPTED_V05_TOKEN = "SRFD.JUNE.AUTH.eaa5a6e46365f673b796d4a966e600833f7528659b8528dc5f1ed27fd7cb5a1a"
EXPECTED_TOKEN = "SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168"


class FreshJuneAuthorityError(ValueError):
    pass


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise FreshJuneAuthorityError(detail)


def token_payload(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": decision["decision_id"],
        "decision_logical_sha256": logical_sha256(decision),
        "authority_envelope_logical_sha256": logical_sha256(envelope),
        "scientific_manifest_logical_sha256": envelope["scientific_manifest"]["logical_sha256"],
        "scientific_manifest_binding_sha256": envelope["scientific_manifest"]["binding_sha256"],
        "capacity_backend_freeze_merge": envelope["implementation_binding"]["capacity_backend_freeze_merge"],
        "capacity_catalog_grid_hash": envelope["implementation_binding"]["capacity_catalog_grid_hash"],
        "population_id": envelope["source_population_binding"]["population_id"],
        "source_release_id": envelope["source_population_binding"]["source_release_id"],
        "sfc_terminal_merge": envelope["sfc_interlock_release"]["terminal_merge"],
        "prior_v0_4_token_id": PRIOR_V04_TOKEN,
        "prior_v0_4_token_state": "CONSUMED_NOT_REUSABLE",
        "attempted_v0_5_token_id": ATTEMPTED_V05_TOKEN,
        "attempted_v0_5_token_state": "NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE",
    }


def reconstruct_token(decision: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    payload = token_payload(decision, envelope)
    return {
        "schema": "ovc-srfd-june-run-authority-token/v6",
        "token_id": stable_id("SRFD.JUNE.AUTH.", payload),
        **payload,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "reserved_authority": "NONE",
    }


def verify_fresh_june_authority(
    decision: Mapping[str, Any],
    envelope: Mapping[str, Any],
    token: Mapping[str, Any],
    source_reverification: Mapping[str, Any],
    sfc_pointer: Mapping[str, Any],
) -> dict[str, Any]:
    _require(decision.get("gate_id") == GATE_ID, "wrong gate")
    _require(decision.get("decision") == AUTHORIZED_DECISION, "June not authorized")
    _require(decision.get("decision_authority") == DELEGATED_AUTHORITY, "wrong delegated authority")
    _require(decision.get("baseline_main") == BASELINE_MAIN, "baseline main mismatch")
    standing = decision.get("standing_delegation", {})
    _require(standing.get("merge_commit") == STANDING_DELEGATION_MERGE, "standing delegation mismatch")

    _require(sfc_pointer.get("status") == "COMPLETED", "SFC not terminal")
    _require(sfc_pointer.get("programme_disposition") == "PRESERVED", "SFC disposition mismatch")
    _require(sfc_pointer.get("srfd_june_authority_interlock") == SFC_INTERLOCK_RELEASE, "SFC interlock not released")
    _require(sfc_pointer.get("validation_2025") == "LOCKED_UNCONSUMED", "SFC Validation boundary widened")
    release = decision.get("sfc_interlock_release", {})
    _require(release.get("terminal_merge") == SFC_TERMINAL_MERGE, "SFC terminal merge mismatch")
    _require(release.get("state") == SFC_INTERLOCK_RELEASE, "SFC release state mismatch")

    prereq = decision.get("prerequisites", {})
    expected = {
        "g10a_freeze_closeout_merge": G10A_CLOSEOUT_MERGE,
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
        "source_artifact_reverification_logical_sha256": SOURCE_ARTIFACT_REVERIFICATION_HASH,
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
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
    }
    for key, value in expected.items():
        _require(prereq.get(key) == value, f"prerequisite mismatch:{key}")

    _require(logical_sha256(source_reverification) == SOURCE_ARTIFACT_REVERIFICATION_HASH, "source artifact reverification drift")
    _require(source_reverification.get("all_exact") is True, "source artifacts not exact")
    _require(source_reverification.get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(source_reverification.get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")
    _require(len(source_reverification.get("artifacts", {})) == 6, "source artifact count mismatch")

    effect = decision.get("authority_effect", {})
    _require(effect.get("june_execution") == "AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", "run scope mismatch")
    for key in (
        "scientific_parameter_or_method_change",
        "family_representation_semantic_promotion",
        "selector_activation_or_replacement",
        "canonical_or_r2_publication",
        "probability_risk_exposure_execution",
    ):
        _require(effect.get(key) == "NONE", f"reserved authority widened:{key}")
    _require(effect.get("provider_fetch") == "DENIED", "provider fetch widened")
    _require(effect.get("validation_2025") == "LOCKED_UNCONSUMED", "Validation widened")

    _require(envelope.get("schema") == "ovc-srfd-june-run-authority-envelope/v6", "wrong envelope schema")
    _require(envelope.get("baseline_main") == BASELINE_MAIN, "envelope baseline mismatch")
    _require(envelope.get("run_authority") == "AUTHORIZED_BY_DELEGATED_SRFDI_G_JUNE_AUTH", "wrong run authority")
    _require(envelope["scientific_manifest"]["logical_sha256"] == SCIENTIFIC_MANIFEST_HASH, "scientific manifest drift")
    _require(envelope["scientific_manifest"]["binding_sha256"] == SCIENTIFIC_MANIFEST_BINDING_HASH, "scientific manifest binding drift")
    _require(envelope["scientific_manifest"]["scientific_semantics"] == "UNCHANGED_V0_4", "scientific semantics changed")
    _require(envelope["implementation_binding"]["capacity_backend_freeze_merge"] == CAPACITY_FREEZE_MERGE, "capacity backend drift")
    _require(envelope["implementation_binding"]["capacity_catalog_grid_hash"] == CAPACITY_GRID_HASH, "capacity grid drift")
    _require(envelope["sfc_interlock_release"]["terminal_merge"] == SFC_TERMINAL_MERGE, "SFC release envelope drift")
    _require(envelope["sfc_interlock_release"]["state"] == SFC_INTERLOCK_RELEASE, "SFC release envelope state drift")
    _require(envelope["source_artifact_reverification"]["logical_sha256"] == SOURCE_ARTIFACT_REVERIFICATION_HASH, "source reverification envelope drift")
    _require(envelope["source_artifact_reverification"]["all_exact"] is True, "source reverification not exact")
    source = envelope["source_population_binding"]
    _require(source["source_record_count"] == 9420, "source count drift")
    _require(source["source_record_hashes_sha256"] == SOURCE_RECORD_HASHES, "source rows drift")
    _require(source["population_id"] == POPULATION_ID and source["eligible_record_count"] == 8598, "population drift")
    _require(source["eligible_record_ids_sha256"] == ELIGIBLE_IDS_HASH, "eligible ids drift")
    _require(source["provider_fetch"] == "FORBIDDEN" and source["upstream_mutation"] == "FORBIDDEN", "source firewall widened")
    _require(envelope["prior_authority"] == {"v0_4_token_id": PRIOR_V04_TOKEN, "v0_4_token_state": "CONSUMED_NOT_REUSABLE", "attempted_v0_5_token_id": ATTEMPTED_V05_TOKEN, "attempted_v0_5_token_state": "NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE"}, "prior token history drift")
    capacity = envelope["capacity_binding"]
    _require(capacity == {"class":"T0_FROZEN_MEASURED","max_wall_seconds":14400,"max_peak_rss_bytes":17179869184,"max_external_bytes":10737418240,"stop_on_capacity_exceeded":True}, "capacity envelope drift")

    reconstructed = reconstruct_token(decision, envelope)
    _require(dict(token) == reconstructed, "new token reconstruction mismatch")
    _require(token["token_id"] == EXPECTED_TOKEN, "unexpected fresh token identity")
    _require(token["token_id"] not in {PRIOR_V04_TOKEN, ATTEMPTED_V05_TOKEN}, "prior token identity reused")
    _require(token["state"] == "AUTHORIZED_UNCONSUMED" and token["single_use"] is True, "new token not single-use unconsumed")
    return reconstructed
