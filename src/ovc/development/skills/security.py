from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path


HARD_DENY_ACTIONS = {
    "FORCE_PUSH", "HISTORY_REWRITE", "MERGE", "SECRET_ACCESS", "RAW_CREDENTIAL_READ",
    "VALIDATION_DISCOVERY", "VALIDATION_READ", "SELECTOR_ACTIVATION", "SCIENTIFIC_PROMOTION",
    "CANONICAL_PUBLICATION", "R2_PUBLICATION", "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION",
}
WRITE_ACTIONS = {"WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"}
SENSITIVE_KEYS = {"secret", "password", "token", "api_key", "credential", "raw_credential"}


def _canonical_symbolic_action(value: Any) -> str:
    """Canonicalize semantic action vocabulary so separator/case aliases cannot evade policy."""
    raw = str(value).strip()
    return re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").upper()


def _prefix_match(path: str, prefixes: Sequence[str]) -> bool:
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def resolve_security_envelope(*, skill_id: str, capability_ids: Sequence[str], allowed_semantic_actions: Sequence[str], read_prefixes: Sequence[str] = (), write_prefixes: Sequence[str] = (), semantic_owners: Sequence[str] = (), logical_credential_ids: Sequence[str] = (), network_allowlist: Sequence[str] = (), filesystem_zone_profile: str = "WP5-ZONE-PROFILE-READONLY", write_authority_active: bool = False, validation_authority_active: bool = False) -> dict[str, Any]:
    actions = sorted(set(_canonical_symbolic_action(v) for v in allowed_semantic_actions) - HARD_DENY_ACTIONS)
    logical = {
        "skill_id":str(skill_id), "capability_ids":sorted(set(str(v) for v in capability_ids)), "allowed_semantic_actions":actions,
        "read_prefixes":sorted({normalize_relative_path(v).rstrip("/") for v in read_prefixes}),
        "write_prefixes":sorted({normalize_relative_path(v).rstrip("/") for v in write_prefixes}),
        "semantic_owners":sorted(set(str(v) for v in semantic_owners)), "logical_credential_ids":sorted(set(str(v) for v in logical_credential_ids)),
        "network_allowlist":sorted(set(str(v) for v in network_allowlist)), "filesystem_zone_profile":str(filesystem_zone_profile),
        "write_authority_active":bool(write_authority_active), "validation_authority_active":bool(validation_authority_active), "deny_by_default":True,
    }
    return {"schema":"ovc-dsai-execution-security-envelope/v1", **logical, "authority_effect":"NONE", "raw_credentials_exposed":False, "envelope_id":canonical_sha256(logical, role="DSAI_EXECUTION_SECURITY_ENVELOPE")}


def build_tool_request(*, action: str, path: str | None = None, semantic_owner: str | None = None, logical_credential_id: str | None = None, network_target: str | None = None, resource_class: str = "GENERAL", raw_credential: str | None = None) -> dict[str, Any]:
    if raw_credential is not None:
        raise ValueError("raw credentials are prohibited in ToolRequest")
    logical={"action":_canonical_symbolic_action(action),"path":path,"semantic_owner":semantic_owner,"logical_credential_id":logical_credential_id,"network_target":network_target,"resource_class":str(resource_class).upper()}
    return {"schema":"ovc-dsai-tool-request/v1",**logical,"request_id":canonical_sha256(logical,role="DSAI_TOOL_REQUEST")}


def decide_tool_request(envelope: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    action=_canonical_symbolic_action(request.get("action","")); reasons:list[str]=[]
    if action in HARD_DENY_ACTIONS: reasons.append("HARD_DENY_OPERATION")
    if str(request.get("resource_class","GENERAL")).upper()=="VALIDATION" and not envelope.get("validation_authority_active"): reasons.append("VALIDATION_FIREWALL")
    if action not in set(envelope.get("allowed_semantic_actions",[])): reasons.append("SEMANTIC_ACTION_NOT_PERMITTED")
    cred=request.get("logical_credential_id")
    if cred and cred not in set(envelope.get("logical_credential_ids",[])): reasons.append("CREDENTIAL_ID_NOT_PERMITTED")
    target=request.get("network_target")
    if target and target not in set(envelope.get("network_allowlist",[])): reasons.append("NETWORK_DENY_DEFAULT")
    path=request.get("path"); normalized_path=None
    if path:
        try: normalized_path=normalize_relative_path(str(path))
        except (ValueError,OSError): reasons.append("FILESYSTEM_ESCAPE_OR_UNSAFE_PATH")
        if normalized_path is not None:
            if action in WRITE_ACTIONS:
                if not envelope.get("write_authority_active"): reasons.append("WRITE_AUTHORITY_INACTIVE")
                if not _prefix_match(normalized_path,envelope.get("write_prefixes",[])): reasons.append("WRITE_PATH_OUT_OF_SCOPE")
                owner=request.get("semantic_owner")
                if not owner or owner not in set(envelope.get("semantic_owners",[])): reasons.append("SEMANTIC_OWNERSHIP_DENIED")
            elif not _prefix_match(normalized_path,envelope.get("read_prefixes",[])): reasons.append("READ_PATH_OUT_OF_SCOPE")
    decision="DENY" if reasons else "ALLOW"
    logical={"envelope_id":envelope.get("envelope_id"),"request_id":request.get("request_id"),"action":action,"decision":decision,"reason_codes":sorted(set(reasons)),"normalized_path":normalized_path}
    return {"schema":"ovc-dsai-security-decision-record/v1",**logical,"authority_effect":"NONE","raw_credentials_exposed":False,"decision_id":canonical_sha256(logical,role="DSAI_SECURITY_DECISION")}


def issue_credential_handle(*, logical_credential_id: str, raw_secret: str | None = None) -> dict[str, Any]:
    if raw_secret is not None: raise ValueError("raw secret material cannot be brokered to Skill code")
    logical={"logical_credential_id":str(logical_credential_id),"secret_material_included":False}
    return {"schema":"ovc-dsai-credential-handle/v1",**logical,"handle_id":canonical_sha256(logical,role="DSAI_CREDENTIAL_HANDLE"),"authority_effect":"NONE"}


def redact_sensitive(value: Mapping[str, Any]) -> dict[str, Any]:
    result:dict[str,Any]={}
    for key,item in value.items():
        lower=str(key).lower()
        if any(token in lower for token in SENSITIVE_KEYS): result[str(key)]="[REDACTED]"
        elif isinstance(item,Mapping): result[str(key)]=redact_sensitive(item)
        else: result[str(key)]=item
    return result


def negative_reachability_probe(envelope: Mapping[str, Any]) -> dict[str, Any]:
    probes=[build_tool_request(action="VALIDATION_READ",resource_class="VALIDATION"),build_tool_request(action="SECRET_ACCESS",resource_class="SECRET"),build_tool_request(action="READ_FILE",path="../outside"),build_tool_request(action="READ_FILE",path="registries/validation/protected.json",resource_class="VALIDATION"),build_tool_request(action="READ_FILE",path="src/ovc/development/skills/security.py",network_target="internet.example")]
    decisions=[decide_tool_request(envelope,request) for request in probes]; escaped=[row for row in decisions if row["decision"]!="DENY"]
    return {"schema":"ovc-dsai-negative-reachability-result/v1","status":"PASS" if not escaped else "BLOCK","probe_count":len(decisions),"unexpected_allows":escaped,"decisions":decisions,"authority_effect":"NONE"}


def sandbox_leakage_probe(*, environment: Mapping[str, str], discovered_paths: Sequence[str], allowed_environment_keys: Sequence[str] = ("PATH", "PYTHONPATH"), protected_path_prefixes: Sequence[str] = ("validation", "credentials", "dmrp/cross_path")) -> dict[str, Any]:
    allowed=set(str(v) for v in allowed_environment_keys)
    leaked_env=sorted(key for key in environment if key not in allowed)
    leaked_paths=[]
    for raw in discovered_paths:
        try: path=normalize_relative_path(raw)
        except (ValueError,OSError): leaked_paths.append(str(raw)); continue
        if any(path==prefix or path.startswith(prefix.rstrip("/")+"/") for prefix in protected_path_prefixes): leaked_paths.append(path)
    status="PASS" if not leaked_env and not leaked_paths else "BLOCK"
    return {"schema":"ovc-dsai-sandbox-leakage-result/v1","status":status,"leaked_environment_keys":leaked_env,"leaked_paths":sorted(leaked_paths),"authority_effect":"NONE"}


def security_containment(*, severity: str) -> dict[str, Any]:
    level=str(severity).upper(); contained=level in {"S3","S4"}
    return {"schema":"ovc-dsai-security-containment/v1","severity":level,"privileged_actions_denied":contained,"terminate_sandbox":contained,"notification_required":level in {"S2","S3","S4"},"authority_effect":"NONE"}
