from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from .canonical import canonical_bytes
from .chronology import validate_causal_times, ChronologyError
from .dependencies import evaluate_synthetic_source


@dataclass(frozen=True)
class CandidateExtractionResult:
    candidate: dict[str, Any] | None
    computability: str
    evidence_status: str
    reason_codes: tuple[str, ...]


def _hash(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_bytes(dict(payload))).hexdigest()


def extract_candidate(source: Mapping[str, Any], object_pack: Mapping[str, Any]) -> CandidateExtractionResult:
    decision = evaluate_synthetic_source(source)
    if decision.computability != "AVAILABLE":
        return CandidateExtractionResult(None, decision.computability, decision.evidence_status, decision.reason_codes)
    if object_pack.get("status") != "SYNTHETIC_ONLY_NONEMPIRICAL" or object_pack.get("real_source_forbidden") is not True:
        return CandidateExtractionResult(None, "NOT_EVALUABLE", "NOT_EVALUABLE", ("C2P_WP2_SYNTHETIC_PACK_REQUIRED",))
    if source.get("candidate_present", True) is not True:
        return CandidateExtractionResult(None, "AVAILABLE", "AVAILABLE", ("C2P_CANDIDATE_ABSENT",))
    try:
        validate_causal_times(
            market_effective_start=source["market_effective_start"],
            market_effective_end=source.get("market_effective_end"),
            first_valid_time=source["first_valid_time"],
            evaluation_cutoff=source["evaluation_cutoff"],
        )
    except ChronologyError as exc:
        return CandidateExtractionResult(None, "NOT_EVALUABLE", "NOT_EVALUABLE", (str(exc),))

    hard_scope = {
        "instrument": "SYNTH",
        "side": "SYNTH",
        "scale": "STEP",
        "partition_id": str(source["fixture_partition_id"]),
    }
    identity_geometry = dict(source["identity_defining_geometry"])
    identity_payload = {
        "schema": "c2p-candidate-identity/v0.2",
        "object_pack_id": object_pack["object_pack_id"],
        "structural_role_id": object_pack["structural_role_id"],
        "geometry_kind_id": object_pack["geometry_kind_id"],
        "hard_scope": hard_scope,
        "identity_defining_geometry": identity_geometry,
        "fixture_structure_key": source["fixture_structure_key"],
        "fixture_step": int(source["fixture_step"]),
        "coordinate_class": source["coordinate_class"],
        "source_refs": sorted(set(source["source_refs"])),
        "first_valid_time": source["first_valid_time"],
    }
    candidate = {
        "schema": "c2p-candidate/v0.2",
        "candidate_id": _hash(identity_payload),
        "hash_version": "sha256-canonical-json-v1",
        "object_pack_id": object_pack["object_pack_id"],
        "structural_role_id": object_pack["structural_role_id"],
        "geometry_kind_id": object_pack["geometry_kind_id"],
        "hard_scope": hard_scope,
        "identity_defining_geometry": identity_geometry,
        "source_lineage_envelope_id": source["source_lineage_envelope_id"],
        "source_refs": sorted(set(source["source_refs"])),
        "market_effective_start": source["market_effective_start"],
        "market_effective_end": source.get("market_effective_end"),
        "first_valid_time": source["first_valid_time"],
        "evaluation_cutoff": source["evaluation_cutoff"],
        "computability": "AVAILABLE",
        "evidence_status": "AVAILABLE",
        "reason_codes": [],
    }
    return CandidateExtractionResult(candidate, "AVAILABLE", "AVAILABLE", ())
