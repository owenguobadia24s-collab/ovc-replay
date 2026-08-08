from __future__ import annotations

from typing import Any, Mapping

from .june_authority import (
    AUTHORIZED_DECISION,
    AUTHORIZED_RUN_STATE,
    GATE_ID,
    JuneAuthorityError,
    JuneRunAuthorityToken,
    _hex64,
    _required_mapping,
    _text,
)
from .serialization import logical_sha256, stable_id

MANIFEST_SCHEMA = "ovc-srfd-june-run-manifest/v2"
PREREG_ID = "OVC-SRFD-JUNE-PREREG-v0.2-CANDIDATE"
PREREG_BYTE_SHA256 = "13c17cf64c576b35e53047de753a5fd1a49bbdc7205c387bbcedb5a34441b804"
PREREG_LOGICAL_SHA256 = "13c17cf64c576b35e53047de753a5fd1a49bbdc7205c387bbcedb5a34441b804"
PREREG_FREEZE_GATE = "SRFDI-G9S-FREEZE"
PACK_REGISTRY_BYTE_SHA256 = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
PACK_REGISTRY_LOGICAL_SHA256 = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
PACK_REGISTRY_PATH = "registries/research/srfd/real_source_representation_packs_v0_2.json"
PENDING_RUN_STATE = "PENDING_SRFDI_G_JUNE_AUTH"


def manifest_binding_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("authority_binding", None)
    payload["run_authority"] = PENDING_RUN_STATE
    return payload


def manifest_binding_sha256(manifest: Mapping[str, Any]) -> str:
    return logical_sha256(manifest_binding_payload(manifest))


def verify_june_run_authority(
    decision: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
    *,
    expected_implementation_commit: str,
) -> JuneRunAuthorityToken:
    if decision is None:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "operator decision is required")
    if _text(decision.get("gate_id"), "decision.gate_id") != GATE_ID:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "wrong authority gate")
    if _text(decision.get("decision"), "decision.decision") != AUTHORIZED_DECISION:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "decision does not authorize June")
    decision_id = _text(decision.get("decision_id"), "decision.decision_id")

    authority_effect = _required_mapping(decision.get("authority_effect"), "decision.authority_effect")
    required_effect = {
        "june_execution": "AUTHORIZED_BOUNDED_JUNE_BENCHMARK",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_promotion": "NONE",
        "selector_change": "NONE",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }
    for field, expected in required_effect.items():
        if authority_effect.get(field) != expected:
            raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", f"decision authority effect mismatch:{field}")

    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest schema is not frozen v0.2")
    if manifest.get("run_authority_gate") != GATE_ID or manifest.get("run_authority") != AUTHORIZED_RUN_STATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest run authority is not exact")
    if manifest.get("preregistration_id") != PREREG_ID:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "preregistration id mismatch")
    if manifest.get("preregistration_byte_sha256") != PREREG_BYTE_SHA256 or manifest.get("preregistration_logical_sha256") != PREREG_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "preregistration hash mismatch")
    if manifest.get("prerequisite_gate") != PREREG_FREEZE_GATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "preregistration freeze gate mismatch")

    pack_registry = _required_mapping(manifest.get("representation_pack_registry"), "manifest.representation_pack_registry")
    if pack_registry.get("path") != PACK_REGISTRY_PATH:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "representation-pack registry path mismatch")
    if pack_registry.get("byte_sha256") != PACK_REGISTRY_BYTE_SHA256 or pack_registry.get("logical_sha256") != PACK_REGISTRY_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "representation-pack registry hash mismatch")

    if manifest.get("validation_2025") != "LOCKED_UNCONSUMED":
        raise JuneAuthorityError("AUTH_VALIDATION_DENIED", "Validation must remain locked")
    if manifest.get("selector_change") != "NONE" or manifest.get("scientific_promotion") != "NONE" or manifest.get("publication") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "reserved scientific authority changed")
    if manifest.get("probability_risk_exposure_execution") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "probability/risk/exposure/execution authority changed")

    source = _required_mapping(manifest.get("source_binding"), "manifest.source_binding")
    if source.get("provider_fetch") != "FORBIDDEN" or source.get("upstream_mutation") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "source firewalls changed")
    source_release_id = _text(source.get("source_release_id"), "source_release_id")
    _text(source.get("source_commit"), "source_commit")
    _text(source.get("source_slice_id"), "source_slice_id")
    _hex64(source.get("source_manifest_sha256"), "source_manifest_sha256")
    _hex64(source.get("output_manifest_sha256"), "output_manifest_sha256")
    _hex64(source.get("source_record_hashes_sha256"), "source_record_hashes_sha256")
    _hex64(source.get("source_binding_sha256"), "source_binding_sha256")

    population = _required_mapping(manifest.get("population_binding"), "manifest.population_binding")
    population_id = _text(population.get("population_id"), "population_id")
    count = population.get("eligible_record_count")
    source_count = population.get("source_record_count")
    context_count = population.get("context_record_count")
    exclusion_count = population.get("exclusion_count")
    if not isinstance(count, int) or count < 1:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "eligible population count must be bound")
    if not isinstance(source_count, int) or source_count < count:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "source population count must be bound")
    if not isinstance(context_count, int) or context_count < 0:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "context population count must be bound")
    if not isinstance(exclusion_count, int) or exclusion_count < 0:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "exclusion count must be bound")
    _hex64(population.get("eligible_record_ids_sha256"), "eligible_record_ids_sha256")
    _hex64(population.get("context_record_ids_sha256"), "context_record_ids_sha256")
    _hex64(population.get("exclusion_ledger_sha256"), "exclusion_ledger_sha256")
    if population.get("historical_8598_reference") != "MATCHED_EXACT_COUNT_AND_ID_HASH_NOW_BOUND":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "historical population reference is not exactly resolved")

    implementation_commit = _text(manifest.get("implementation_commit"), "implementation_commit")
    if implementation_commit != _text(expected_implementation_commit, "expected_implementation_commit"):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "implementation commit mismatch")
    _hex64(manifest.get("dependency_manifest_hash"), "dependency_manifest_hash")

    required = _required_mapping(manifest.get("required_before_run_authority"), "manifest.required_before_run_authority")
    source_required = _required_mapping(required.get("source"), "manifest.required.source")
    representation_required = _required_mapping(required.get("representation"), "manifest.required.representation")
    if source_required.get("provider_fetch") != "FORBIDDEN" or source_required.get("upstream_mutation") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "required source firewalls changed")
    if source_required.get("exact_release_and_hash_binding") != "PASS":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "exact source binding has not passed")
    if representation_required.get("pack_registry_hash_match") != "PASS" or representation_required.get("post_freeze_feature_selection") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "representation freeze preconditions changed")
    if required.get("validation_2025") != "LOCKED_UNCONSUMED":
        raise JuneAuthorityError("AUTH_VALIDATION_DENIED", "required Validation firewall changed")
    if required.get("selector_change") != "NONE" or required.get("scientific_promotion") != "NONE" or required.get("publication") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "required scientific firewalls changed")
    if required.get("probability_risk_exposure_execution") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "required execution firewall changed")

    binding_hash = manifest_binding_sha256(manifest)
    decision_binding_hash = _hex64(decision.get("authorized_manifest_sha256"), "decision.authorized_manifest_sha256")
    if decision_binding_hash != binding_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "operator decision does not bind this manifest")
    decision_hash = logical_sha256(decision)
    authority_binding = _required_mapping(manifest.get("authority_binding"), "manifest.authority_binding")
    if authority_binding.get("gate_id") != GATE_ID or authority_binding.get("decision_id") != decision_id:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest authority decision identity mismatch")
    if _hex64(authority_binding.get("decision_logical_sha256"), "authority_binding.decision_logical_sha256") != decision_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest decision hash mismatch")
    if _hex64(authority_binding.get("authorized_manifest_sha256"), "authority_binding.authorized_manifest_sha256") != binding_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest binding hash mismatch")

    manifest_hash = logical_sha256(manifest)
    token_payload = {
        "decision_id": decision_id,
        "decision_logical_sha256": decision_hash,
        "manifest_logical_sha256": manifest_hash,
        "authorized_manifest_sha256": binding_hash,
        "implementation_commit": implementation_commit,
        "population_id": population_id,
        "source_release_id": source_release_id,
    }
    return JuneRunAuthorityToken(
        token_id=stable_id("SRFD.JUNE.AUTH.", token_payload),
        decision_id=decision_id,
        decision_logical_sha256=decision_hash,
        manifest_logical_sha256=manifest_hash,
        authorized_manifest_sha256=binding_hash,
        implementation_commit=implementation_commit,
        population_id=population_id,
        source_release_id=source_release_id,
    )


def guard_bounded_june_run(token: JuneRunAuthorityToken | None, manifest: Mapping[str, Any]) -> None:
    if token is None:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "bounded June authority token required")
    if token.authority_state != AUTHORIZED_RUN_STATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "authority token is not active for bounded June")
    if token.manifest_logical_sha256 != logical_sha256(manifest):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest differs from authorized token")
    if token.authorized_manifest_sha256 != manifest_binding_sha256(manifest):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest binding differs from authorized token")
