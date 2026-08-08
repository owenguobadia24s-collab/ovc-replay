from __future__ import annotations

from typing import Any, Mapping, Sequence

from .serialization import logical_hash


class SFCReplayError(ValueError):
    pass


def build_replay_manifest(*, source_stream_id: str, pack_ids: Sequence[str], spec_ids: Sequence[str], configuration_ids: Sequence[str], rule_pack_ids: Sequence[str], code_hashes: Mapping[str,str], schema_hashes: Mapping[str,str], upstream_receipt_id: str, external_inventory: Sequence[Mapping[str,Any]] = (), checkpoints: Sequence[str] = ()) -> dict[str, Any]:
    payload={
        "source_stream_id":source_stream_id,
        "pack_ids":sorted(set(pack_ids)),
        "spec_ids":sorted(set(spec_ids)),
        "configuration_ids":sorted(set(configuration_ids)),
        "rule_pack_ids":sorted(set(rule_pack_ids)),
        "code_hashes":dict(sorted(code_hashes.items())),
        "schema_hashes":dict(sorted(schema_hashes.items())),
        "upstream_receipt_id":upstream_receipt_id,
        "srfd_june_interlock":"DENY",
        "external_inventory":sorted((dict(x) for x in external_inventory),key=lambda x:logical_hash(x)),
        "checkpoints":sorted(set(checkpoints)),
        "authority_state":"SYNTHETIC_CONFORMANCE_ONLY",
    }
    payload["replay_manifest_id"]="SFC.REPLAY."+logical_hash(payload)[:24]
    payload["logical_hash"]=logical_hash(payload)
    return payload


def checkpoint_state(manifest: Mapping[str,Any], *, completed_ids: Sequence[str], partial_evidence: Sequence[Mapping[str,Any]], last_source_fvt: str) -> dict[str,Any]:
    payload={"replay_manifest_id":manifest["replay_manifest_id"],"manifest_hash":manifest["logical_hash"],"completed_ids":sorted(set(completed_ids)),"partial_evidence_hashes":sorted(logical_hash(x) for x in partial_evidence),"last_source_fvt":last_source_fvt}
    payload["checkpoint_id"]="SFC.CHECKPOINT."+logical_hash(payload)[:24]; payload["logical_hash"]=logical_hash(payload); return payload


def resume_remaining(source_ids: Sequence[str], checkpoint: Mapping[str,Any]) -> list[str]:
    return sorted(set(str(x) for x in source_ids)-set(str(x) for x in checkpoint.get("completed_ids",[])))


def capacity_guard(*, population_id: str, eligible_count: int, pair_count: int, family_grid_count: int, limits: Mapping[str,int]) -> dict[str,Any]:
    exceeded=[]
    for key,value in (("eligible_count",eligible_count),("pair_count",pair_count),("family_grid_count",family_grid_count)):
        if key in limits and value>int(limits[key]): exceeded.append(key)
    status="CAPACITY_EXCEEDED" if exceeded else "SUCCESS"
    payload={"population_id":population_id,"eligible_count":eligible_count,"pair_count":pair_count,"family_grid_count":family_grid_count,"limits":dict(sorted(limits.items())),"status":status,"exceeded":exceeded,"sampling_applied":False,"methods_dropped":[],"sensitivity_changed":False,"population_preserved":True,"reason_code":"SFC_CAPACITY_EXCEEDED" if exceeded else None}
    payload["logical_hash"]=logical_hash(payload); return payload


def enforce_june_interlock(interlock: str, action: str) -> dict[str,Any]:
    protected={"SRFDI-G-JUNE-AUTH-PREP","SRFDI-G-JUNE-AUTH","JUNE_SCIENTIFIC_RUN","FRESH_JUNE_RUN_TOKEN"}
    denied=interlock=="DENY" and action in protected
    payload={"interlock":interlock,"action":action,"status":"DENIED" if denied else "ALLOWED","reason_code":"SFC_SRFD_JUNE_INTERLOCK_ACTIVE" if denied else None}
    payload["logical_hash"]=logical_hash(payload); return payload


def dependency_status(value: str) -> str:
    allowed={"READY","UNKNOWN","UNAVAILABLE","BLOCKED","QUARANTINED"}
    if value not in allowed: raise SFCReplayError("SFC_DEPENDENCY_STATUS_INVALID")
    return value


def propagate_quarantine(*statuses: str) -> str:
    return "QUARANTINED" if "QUARANTINED" in statuses else "READY"


def build_g2_block(*, observed_upstream_state: str, missing_artifacts: Sequence[str], expected_upstream_evidence: Sequence[str]) -> dict[str,Any]:
    payload={"gate_id":"SFC-G2","reason_code":"BLOCK_UPSTREAM","missing_artifacts":sorted(set(missing_artifacts)),"observed_upstream_state":observed_upstream_state,"expected_upstream_evidence":sorted(set(expected_upstream_evidence)),"no_fallback_assertion":"HISTORICAL_MG_C2E_FORBIDDEN","reevaluation_triggers":["UPSTREAM_ARTIFACT_MATERIALIZED","UPSTREAM_STATE_CHANGED"],"authority_state":"BLOCKED_NO_FALLBACK"}
    payload["logical_hash"]=logical_hash(payload); return payload
