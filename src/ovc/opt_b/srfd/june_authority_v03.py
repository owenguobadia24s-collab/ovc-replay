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

MANIFEST_SCHEMA = "ovc-srfd-june-run-manifest/v3"
PREREG_ID = "OVC-SRFD-JUNE-PREREG-v0.3-CANDIDATE"
PREREG_PATH = "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_3.json"
PREREG_LOGICAL_SHA256 = "acb27ff21d4df6da6ea72972bda7a6ee1ce28a7f06827b949f55d8b03ec04bb5"
PREREG_FREEZE_GATE = "SRFDI-G9C-FREEZE"
PREREG_FREEZE_MERGE_COMMIT = "249afca5984022b7e9cbbd414bf2a74a2a255d1a"
SEGMENTATION_REGISTRY_PATH = "registries/research/srfd/segmentation_boundary_packs_v0_3.json"
SEGMENTATION_REGISTRY_LOGICAL_SHA256 = "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0"
REPRESENTATION_PACK_REGISTRY_PATH = "registries/research/srfd/real_source_representation_packs_v0_2.json"
REPRESENTATION_PACK_REGISTRY_LOGICAL_SHA256 = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
SOURCE_BINDING_SHA256 = "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7"
POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
ELIGIBLE_RECORD_COUNT = 8598
ELIGIBLE_RECORD_IDS_SHA256 = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
EXCLUSION_LEDGER_SHA256 = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
PENDING_RUN_STATE = "PENDING_SRFDI_G_JUNE_AUTH"

EXPECTED_SEGMENTATION_METHODS = [
    "C2E_CAUSAL_ADAPTER",
    "RUN_CHANGE_SEGMENTATION",
    "DIRECTIONAL_CHANGE",
    "PELT_REFERENCE",
    "NULL_BOUNDARY_CONTROL",
]
EXPECTED_SEGMENTATION_EXECUTE = ["RUN_CHANGE_SEGMENTATION", "NULL_BOUNDARY_CONTROL"]
EXPECTED_SEGMENTATION_NONEXECUTED = ["C2E_CAUSAL_ADAPTER", "DIRECTIONAL_CHANGE", "PELT_REFERENCE"]


def manifest_binding_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("authority_binding", None)
    payload["run_authority"] = PENDING_RUN_STATE
    return payload


def manifest_binding_sha256(manifest: Mapping[str, Any]) -> str:
    return logical_sha256(manifest_binding_payload(manifest))


def _require_exact_frozen_science(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest schema is not frozen v0.3")

    prereg = _required_mapping(manifest.get("preregistration"), "manifest.preregistration")
    if prereg.get("id") != PREREG_ID or prereg.get("path") != PREREG_PATH:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "v0.3 preregistration identity mismatch")
    if prereg.get("logical_sha256") != PREREG_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "v0.3 preregistration hash mismatch")
    if prereg.get("freeze_gate") != PREREG_FREEZE_GATE or prereg.get("freeze_merge_commit") != PREREG_FREEZE_MERGE_COMMIT:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "v0.3 preregistration freeze binding mismatch")

    segmentation = _required_mapping(manifest.get("segmentation_registry"), "manifest.segmentation_registry")
    if segmentation.get("path") != SEGMENTATION_REGISTRY_PATH:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "segmentation registry path mismatch")
    if segmentation.get("logical_sha256") != SEGMENTATION_REGISTRY_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "segmentation registry hash mismatch")

    packs = _required_mapping(manifest.get("representation_pack_registry"), "manifest.representation_pack_registry")
    if packs.get("path") != REPRESENTATION_PACK_REGISTRY_PATH:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "representation-pack registry path mismatch")
    if packs.get("logical_sha256") != REPRESENTATION_PACK_REGISTRY_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "representation-pack registry hash mismatch")

    candidate_sets = _required_mapping(manifest.get("candidate_sets"), "manifest.candidate_sets")
    if candidate_sets.get("representation") != "INHERIT_EXACT_V0_2":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "representation grid changed")
    if candidate_sets.get("distance") != "INHERIT_EXACT_V0_2":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "distance grid changed")
    if candidate_sets.get("family") != "INHERIT_EXACT_V0_2":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "family grid changed")
    if candidate_sets.get("sensitivity") != "INHERIT_EXACT_V0_2":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "sensitivity grid changed")
    if candidate_sets.get("segmentation") != EXPECTED_SEGMENTATION_METHODS:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "declared segmentation set mismatch")
    if candidate_sets.get("segmentation_execute") != EXPECTED_SEGMENTATION_EXECUTE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "segmentation execution set mismatch")
    if candidate_sets.get("segmentation_visible_nonexecuted") != EXPECTED_SEGMENTATION_NONEXECUTED:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "segmentation nonexecution set mismatch")


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

    effect = _required_mapping(decision.get("authority_effect"), "decision.authority_effect")
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
        if effect.get(field) != expected:
            raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", f"decision authority effect mismatch:{field}")

    _require_exact_frozen_science(manifest)
    if manifest.get("run_authority_gate") != GATE_ID or manifest.get("run_authority") != AUTHORIZED_RUN_STATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest run authority is not exact")

    if manifest.get("validation_2025") != "LOCKED_UNCONSUMED":
        raise JuneAuthorityError("AUTH_VALIDATION_DENIED", "Validation must remain locked")
    if manifest.get("selector_change") != "NONE" or manifest.get("scientific_promotion") != "NONE" or manifest.get("publication") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "reserved scientific authority changed")
    if manifest.get("probability_risk_exposure_execution") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "probability/risk/exposure/execution authority changed")

    source = _required_mapping(manifest.get("source_binding"), "manifest.source_binding")
    if source.get("source_binding_sha256") != SOURCE_BINDING_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "source binding mismatch")
    if source.get("provider_fetch") != "FORBIDDEN" or source.get("upstream_mutation") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "source firewalls changed")
    source_release_id = _text(source.get("source_release_id"), "source_release_id")
    _text(source.get("source_commit"), "source_commit")
    _hex64(source.get("source_manifest_sha256"), "source_manifest_sha256")
    _hex64(source.get("output_manifest_sha256"), "output_manifest_sha256")
    _hex64(source.get("source_record_hashes_sha256"), "source_record_hashes_sha256")

    population = _required_mapping(manifest.get("population_binding"), "manifest.population_binding")
    if population.get("population_id") != POPULATION_ID:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "population identity mismatch")
    if population.get("eligible_record_count") != ELIGIBLE_RECORD_COUNT:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "eligible population count mismatch")
    if population.get("eligible_record_ids_sha256") != ELIGIBLE_RECORD_IDS_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "eligible population hash mismatch")
    if population.get("exclusion_ledger_sha256") != EXCLUSION_LEDGER_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "exclusion ledger hash mismatch")
    if population.get("membership_change") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "population membership change is not forbidden")

    implementation_commit = _text(manifest.get("implementation_commit"), "implementation_commit")
    if implementation_commit != _text(expected_implementation_commit, "expected_implementation_commit"):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "implementation commit mismatch")
    _hex64(manifest.get("dependency_manifest_hash"), "dependency_manifest_hash")

    capacity = _required_mapping(manifest.get("capacity_binding"), "manifest.capacity_binding")
    if capacity.get("capacity_class") != "T0_FROZEN_MEASURED":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "capacity class mismatch")
    if capacity.get("max_wall_seconds") != 14400 or capacity.get("max_peak_rss_bytes") != 17179869184 or capacity.get("max_external_bytes") != 10737418240:
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "T0 capacity envelope changed")
    if capacity.get("stop_on_capacity_exceeded") is not True:
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "capacity stop condition changed")

    required = _required_mapping(manifest.get("required_before_run_authority"), "manifest.required_before_run_authority")
    if required.get("exact_g9c_freeze") != "PASS":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "G9C freeze prerequisite not exact")
    if required.get("exact_v0_3_preregistration") != "PASS" or required.get("exact_segmentation_registry") != "PASS":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "v0.3 frozen scientific binding not exact")
    if required.get("source_population_binding") != "PASS_UNCHANGED":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "source/population binding changed")
    if required.get("prior_v0_2_authority_token") != "SUPERSEDED_UNUSED_UNCONSUMED":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "prior token disposition changed")

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
        "population_id": POPULATION_ID,
        "source_release_id": source_release_id,
    }
    return JuneRunAuthorityToken(
        token_id=stable_id("SRFD.JUNE.AUTH.", token_payload),
        decision_id=decision_id,
        decision_logical_sha256=decision_hash,
        manifest_logical_sha256=manifest_hash,
        authorized_manifest_sha256=binding_hash,
        implementation_commit=implementation_commit,
        population_id=POPULATION_ID,
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
