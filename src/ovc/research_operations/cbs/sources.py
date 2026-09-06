from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .identity import CBSContractError, seal_object

C2_AUTHORITY = "registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json"
C2_READ_POINTER = "registries/opt_b/c2/vnext/CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ_SURFACE.json"
C2E_AUTHORITY = "registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json"
C2E_PACK_REGISTRY = "registries/opt_b/c2e/v0_2/C2E_BOUNDARY_PACK_REGISTRY_v0_2.json"
RO_AUTHORITY = "registries/research_operations/ACTIVE_FOUNDATION_AUTHORITY_v0_1.json"

EXPECTED_C2_AUTHORITY = "AUTH.OPT-B.C2.vNext.ACTIVE.RUNTIME.v0.1"
EXPECTED_C2E_AUTHORITY = "AUTH.OPT-B.C2E.v0.2.ACTIVE.ENGINE.v0.1"
EXPECTED_C2E_PACK = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
EXPECTED_C2E_PACK_SHA256 = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
EXPECTED_RO_AUTHORITY = "AUTH.RESEARCH_OPERATIONS.ACTIVE_FOUNDATION.v0.1"


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CBSContractError(f"SOURCE_BINDING_INCOMPLETE:{relative}") from exc
    if not isinstance(value, dict):
        raise CBSContractError(f"SOURCE_BINDING_INCOMPLETE:{relative}")
    return value


def _blob(root: Path, relative: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "hash-object", relative], capture_output=True, text=True, check=False
    )
    if proc.returncode or len(proc.stdout.strip()) != 40:
        raise CBSContractError(f"SOURCE_BINDING_INCOMPLETE:{relative}")
    return proc.stdout.strip()


def resolve_current_authority(root: Path) -> dict[str, Any]:
    c2 = _read(root, C2_AUTHORITY)
    read_pointer = _read(root, C2_READ_POINTER)
    c2e = _read(root, C2E_AUTHORITY)
    pack_registry = _read(root, C2E_PACK_REGISTRY)
    ro = _read(root, RO_AUTHORITY)
    if c2.get("authority_id") != EXPECTED_C2_AUTHORITY:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:C2_AUTHORITY_DRIFT")
    if read_pointer.get("owner_authority_id") != EXPECTED_C2_AUTHORITY or read_pointer.get("validation") != "LOCKED_UNCONSUMED":
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:C2_OWNER_READ_SURFACE")
    if c2e.get("authority_id") != EXPECTED_C2E_AUTHORITY:
        raise CBSContractError("C2E_REFERENCE_PACK_UNRESOLVED:AUTHORITY_DRIFT")
    if c2e.get("active_boundary_pack_id") != EXPECTED_C2E_PACK or c2e.get("active_boundary_pack_logical_sha256") != EXPECTED_C2E_PACK_SHA256:
        raise CBSContractError("C2E_REFERENCE_PACK_UNRESOLVED:PACK_DRIFT")
    if pack_registry.get("active_boundary_pack_id") != EXPECTED_C2E_PACK or not pack_registry.get("production_pack_selected"):
        raise CBSContractError("C2E_REFERENCE_PACK_UNRESOLVED:REGISTRY_DRIFT")
    if ro.get("authority_id") != EXPECTED_RO_AUTHORITY:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:RESEARCH_OPERATIONS_AUTHORITY")
    envelopes = [c2.get("market_envelope"), c2e.get("market_envelope"), ro.get("market_envelope")]
    if any(envelope != envelopes[0] for envelope in envelopes[1:]) or envelopes[0].get("validation") != "LOCKED_UNCONSUMED":
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:OWNER_ENVELOPE_CONFLICT")
    return seal_object(
        {
            "schema": "ovc-cbs-authority-resolution/v0.1",
            "c2_authority_id": EXPECTED_C2_AUTHORITY,
            "c2_owner_generation_id": read_pointer.get("generation_id"),
            "c2e_authority_id": EXPECTED_C2E_AUTHORITY,
            "c2e_pack_id": EXPECTED_C2E_PACK,
            "c2e_pack_sha256": EXPECTED_C2E_PACK_SHA256,
            "research_operations_authority_id": EXPECTED_RO_AUTHORITY,
            "market_envelope": envelopes[0],
            "source_blobs": {path: _blob(root, path) for path in (C2_AUTHORITY, C2_READ_POINTER, C2E_AUTHORITY, C2E_PACK_REGISTRY, RO_AUTHORITY)},
            "owner_state_effect": "READ_ONLY_NONE",
        },
        id_field="authority_resolution_id",
    )


def build_source_population_manifest(
    *, authority_resolution_id: str, source_release_id: str, source_manifest_sha256: str,
    source_object_ids: Sequence[str], instrument: str, sides: Sequence[str], clocks: Sequence[str],
    research_role: str, interval_start: str, interval_end_exclusive: str,
    gap_policy: str = "PRESERVE_TYPED", censor_policy: str = "PRESERVE_TYPED",
) -> dict[str, Any]:
    if instrument != "GBPUSD" or set(sides) - {"BID", "ASK"} or set(clocks) - {"15M", "2H_A_L"}:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:MARKET_ENVELOPE")
    if research_role not in {"DISCOVERY", "DEVELOPMENT"}:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:RESEARCH_ROLE")
    if not source_release_id or len(source_manifest_sha256) != 64 or not source_object_ids:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:POPULATION_IDENTITY")
    return seal_object(
        {
            "schema":"ovc-cbs-source-population-manifest/v0.1", "authority_resolution_id":authority_resolution_id,
            "source_release_id":source_release_id, "source_manifest_sha256":source_manifest_sha256,
            "source_object_ids":sorted(set(source_object_ids)), "instrument":instrument, "sides":sorted(set(sides)),
            "clocks":sorted(set(clocks)), "research_role":research_role, "interval_start":interval_start,
            "interval_end_exclusive":interval_end_exclusive, "gap_policy":gap_policy, "censor_policy":censor_policy,
            "validation":"LOCKED_UNCONSUMED", "raw_or_downstream_reconstruction":"FORBIDDEN",
        }, id_field="source_population_id"
    )


def validate_owner_snapshot(snapshot: Mapping[str, Any], *, expected_generation_id: str) -> None:
    if snapshot.get("owner_authority_id") != EXPECTED_C2_AUTHORITY or snapshot.get("owner_generation_id") != expected_generation_id:
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:SNAPSHOT_OWNER_IDENTITY")
    authority = snapshot.get("authority")
    if not isinstance(authority, Mapping) or authority.get("read_only") is not True or authority.get("validation") != "LOCKED_UNCONSUMED":
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:SNAPSHOT_AUTHORITY")
    if snapshot.get("effective_time") != snapshot.get("interval_end"):
        raise CBSContractError("SOURCE_BINDING_INCOMPLETE:SNAPSHOT_CHRONOLOGY")
