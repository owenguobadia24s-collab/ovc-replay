from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .serialization import logical_sha256, stable_id

PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v1.0"
V09_PACKET_ID = "SRFDI-WP10-v0.9"
V09_RUN_ID = "SRFD.RUN.25ca319a998d72fb01e0dceff2d455f7abf71a4e6419987246529407467e51e5"
V09_TOKEN_ID = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
V09_RUN_BINDING_SHA256 = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"
FROZEN_POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
T1_EXTERNAL_ARTIFACT_LIMIT_BYTES = 24 * 1024 * 1024 * 1024

SCIENCE_BINDING = {
    "population_id": FROZEN_POPULATION_ID,
    "eligible_ids_sha256": "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e",
    "scientific_manifest_sha256": "6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb",
    "preregistration_sha256": "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3",
    "representation_pack_sha256": "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0",
    "segmentation_pack_sha256": "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0",
    "stability_pack_sha256": "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b",
    "source_binding_sha256": "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7",
    "capacity_grid_sha256": "68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866",
}
SCIENCE_IDENTITY_SHA256 = logical_sha256(SCIENCE_BINDING)


class WP10V10InterfaceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _hex64(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise WP10V10InterfaceError("V10_BINDING_INVALID", field)
    return text


@dataclass(frozen=True)
class RunBindingV10:
    programme_id: str
    packet_id: str
    population_id: str
    eligible_ids_sha256: str
    scientific_manifest_sha256: str
    preregistration_sha256: str
    representation_pack_sha256: str
    segmentation_pack_sha256: str
    stability_pack_sha256: str
    source_binding_sha256: str
    capacity_grid_sha256: str
    science_identity_sha256: str
    capacity_envelope_sha256: str
    storage_binding_sha256: str
    execution_binding_sha256: str

    def to_dict(self) -> dict[str, str]:
        out = {name: str(getattr(self, name)).strip() for name in self.__dataclass_fields__}
        for name in (
            "eligible_ids_sha256", "scientific_manifest_sha256", "preregistration_sha256",
            "representation_pack_sha256", "segmentation_pack_sha256", "stability_pack_sha256",
            "source_binding_sha256", "capacity_grid_sha256", "science_identity_sha256",
            "capacity_envelope_sha256", "storage_binding_sha256", "execution_binding_sha256",
        ):
            out[name] = _hex64(out[name], name)
        if out["programme_id"] != PROGRAMME_ID or out["packet_id"] != PACKET_ID or out["population_id"] != FROZEN_POPULATION_ID:
            raise WP10V10InterfaceError("V10_IDENTITY_DRIFT", f"{out['programme_id']}:{out['packet_id']}:{out['population_id']}")
        return out

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())


def verify_science_unchanged(binding: RunBindingV10) -> None:
    actual = binding.to_dict()
    for key, expected in SCIENCE_BINDING.items():
        if actual[key] != expected:
            raise WP10V10InterfaceError("V10_SCIENCE_BINDING_DRIFT", f"{key}:{actual[key]}")
    if actual["science_identity_sha256"] != SCIENCE_IDENTITY_SHA256:
        raise WP10V10InterfaceError("V10_SCIENCE_IDENTITY_DRIFT", actual["science_identity_sha256"])


def binding_from_manifest(manifest: Mapping[str, Any]) -> RunBindingV10:
    raw = manifest.get("run_binding")
    if not isinstance(raw, Mapping):
        raise WP10V10InterfaceError("V10_MANIFEST_INVALID", "run_binding mapping required")
    keys = tuple(RunBindingV10.__dataclass_fields__)
    if set(raw) != set(keys):
        raise WP10V10InterfaceError("V10_BINDING_SHAPE_MISMATCH", f"keys={sorted(raw)}")
    binding = RunBindingV10(**{key: str(raw[key]) for key in keys})
    verify_science_unchanged(binding)
    if str(manifest.get("run_binding_sha256", "")) != binding.logical_hash:
        raise WP10V10InterfaceError("V10_MANIFEST_BINDING_HASH_MISMATCH", str(manifest.get("run_binding_sha256", "")))
    return binding


def mint_single_use_token(binding: RunBindingV10, *, operator_decision_id: str) -> dict[str, Any]:
    verify_science_unchanged(binding)
    core = {
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
        "operator_decision_id": str(operator_decision_id),
        "cardinality": "ONE_EXACT_BOUND_RUN",
    }
    token_id = stable_id("SRFD.JUNE.AUTH.", core)
    return {
        "schema": "ovc-srfd-june-authority-token/v10",
        "token_id": token_id,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_cardinality": "ONE_EXACT_BOUND_RUN",
        "run_binding_sha256": binding.logical_hash,
        "operator_decision_id": str(operator_decision_id),
        "science_identity_sha256": SCIENCE_IDENTITY_SHA256,
        "capacity_tier": "T1_EXTERNAL_ARTIFACT",
        "max_external_bytes": T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_promotion": "NONE",
        "selector_family_semantic_publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }
