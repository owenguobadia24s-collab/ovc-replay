from __future__ import annotations

from typing import Any, Iterable, Mapping

from ovc.development.identity import canonical_sha256


class SkillResolutionError(ValueError):
    pass


def build_skill_read_model(
    *,
    capabilities: Iterable[Mapping[str, Any]],
    skills: Iterable[Mapping[str, Any]],
    releases: Iterable[Mapping[str, Any]],
    knowledge_packs: Iterable[Mapping[str, Any]],
    environments: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    payload = {
        "capabilities": sorted((dict(row) for row in capabilities), key=lambda row: row.get("capability_id", "")),
        "skills": sorted((dict(row) for row in skills), key=lambda row: row.get("skill_id", "")),
        "releases": sorted((dict(row) for row in releases), key=lambda row: row.get("release_id", "")),
        "knowledge_packs": sorted((dict(row) for row in knowledge_packs), key=lambda row: row.get("knowledge_pack_id", "")),
        "environments": sorted((dict(row) for row in environments), key=lambda row: row.get("environment_id", "")),
    }
    return {"schema": "ovc-dsai-skill-read-model/v1", **payload, "read_model_id": canonical_sha256(payload, role="SKILL_READ_MODEL"), "authority_effect": "NONE"}


def build_resolution_records(
    *,
    packet_id: str,
    environment_id: str,
    required_capability_ids: Iterable[str],
    candidate_release_ids: Iterable[str],
    resolved_release_ids: Iterable[str],
    reason_codes: Iterable[str],
    knowledge_pack_ids: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = sorted(set(required_capability_ids))
    candidates = sorted(set(candidate_release_ids))
    resolved = sorted(set(resolved_release_ids))
    if not packet_id or not environment_id:
        raise SkillResolutionError("packet_id and environment_id are required")
    if not set(resolved).issubset(candidates):
        raise SkillResolutionError("resolved releases must be a subset of candidates")
    manifest_payload = {"packet_id": packet_id, "environment_id": environment_id, "required_capability_ids": required, "candidate_release_ids": candidates}
    manifest_id = canonical_sha256(manifest_payload, role="SKILL_RESOLUTION_MANIFEST")
    manifest = {"schema":"ovc-dsai-skill-resolution-manifest/v1","resolution_manifest_id":manifest_id,**manifest_payload,"authority_effect":"NONE"}
    reasons = sorted(set(reason_codes))
    status = "RESOLVED" if required and resolved and not reasons else ("NOT_RESOLVED" if not resolved else "BLOCKED")
    receipt_payload = {"resolution_manifest_id":manifest_id,"status":status,"resolved_release_ids":resolved,"reason_codes":reasons}
    receipt_id = canonical_sha256(receipt_payload, role="SKILL_RESOLUTION_RECEIPT")
    receipt = {"schema":"ovc-dsai-skill-resolution-receipt/v1","resolution_receipt_id":receipt_id,**receipt_payload,"authority_effect":"NONE"}
    packet_payload = {"packet_id":packet_id,"manifest_id":manifest_id,"receipt_id":receipt_id,"knowledge_pack_ids":sorted(set(knowledge_pack_ids)),"environment_id":environment_id}
    packet = {"schema":"ovc-dsai-packet-skill-resolution/v1","packet_skill_resolution_id":canonical_sha256(packet_payload, role="PACKET_SKILL_RESOLUTION"),**packet_payload,"authority_effect":"NONE"}
    return manifest, receipt, packet
