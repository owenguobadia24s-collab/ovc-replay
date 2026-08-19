"""ASOCS WP7 blind-review infrastructure; creates no human scientific evidence."""
from __future__ import annotations
import hashlib, json, re
from typing import Any, Mapping

BLIND_RESOURCE_ROOT="external/asocs/g1/blind"
REVEAL_RESOURCE_ROOT="external/asocs/g1/reveal"
BLIND_INDEX_ALLOWED_KEYS=frozenset({"case_id","navigation_window","source_native_visual_ref"})
BLIND_INDEX_FORBIDDEN_KEYS=frozenset({"construct","stratum","stratum_memberships","machine_state","machine_disposition","c1","c2","c2e","occurrence_context","prior_disagreement_rate","cross_case_result","hidden_repeat","outcome","failure_attribution"})
PROHIBITED_PROMPT_TERMS=("swing high","swing low","level","container","envelope","relation","structural change","reference identity","parent","episode","phase","re-parent","mutation","persistent object","c2","c2e","rejection","acceptance","support","resistance","breakout")
REVIEW_STATUSES=frozenset({"REVIEWED","UNREVIEWABLE_TECHNICAL","SOURCE_LIMITED","REVIEWER_DEFERRED"})

class ASOCSBlindFirewallError(ValueError): pass

def _canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _forbidden_keys(value:Any)->list[str]:
    hits=[]
    if isinstance(value,Mapping):
        for key,item in value.items():
            if str(key).casefold() in BLIND_INDEX_FORBIDDEN_KEYS: hits.append(str(key))
            hits.extend(_forbidden_keys(item))
    elif isinstance(value,(list,tuple)):
        for item in value: hits.extend(_forbidden_keys(item))
    return sorted(set(hits))

def validate_blind_index(entry:Mapping[str,Any])->dict[str,Any]:
    leaked=_forbidden_keys(entry)
    if leaked: raise ASOCSBlindFirewallError("BLIND_METADATA_LEAK:"+",".join(leaked))
    keys=set(entry); extras=sorted(keys-BLIND_INDEX_ALLOWED_KEYS); missing=sorted(BLIND_INDEX_ALLOWED_KEYS-keys)
    if extras: raise ASOCSBlindFirewallError("BLIND_FIELD_NOT_ALLOWED:"+",".join(extras))
    if missing: raise ASOCSBlindFirewallError("BLIND_FIELD_MISSING:"+",".join(missing))
    windows=entry.get("navigation_window")
    visuals=entry.get("source_native_visual_ref")
    if not isinstance(windows,Mapping) or not {"local","development","wider"}.issubset(windows): raise ASOCSBlindFirewallError("STANDARD_VIEWS_MISSING")
    if not isinstance(visuals,Mapping) or not {"local","development","wider"}.issubset(visuals): raise ASOCSBlindFirewallError("SOURCE_NATIVE_STANDARD_VIEWS_MISSING")
    return dict(entry)

def lint_neutral_prompt(text:str)->list[str]:
    normalized=text.casefold(); hits=[]
    for term in PROHIBITED_PROMPT_TERMS:
        if re.search(r"(?<![a-z0-9])"+re.escape(term)+r"(?![a-z0-9])",normalized): hits.append(term)
    return hits

def require_neutral_prompt(text:str)->str:
    hits=lint_neutral_prompt(text)
    if hits: raise ASOCSBlindFirewallError("PROHIBITED_OVC_VOCABULARY:"+",".join(hits))
    return text

def validate_prompt_registry(prompts:list[Mapping[str,Any]])->None:
    if [p.get("id") for p in prompts] != [f"A{i}" for i in range(9)]: raise ASOCSBlindFirewallError("PROMPT_ORDER_INVALID")
    for prompt in prompts: require_neutral_prompt(str(prompt.get("text","")))

def freeze_blind_record(record:Mapping[str,Any])->dict[str,Any]:
    payload=dict(record); status=str(payload.get("review_status","REVIEWED"))
    if status not in REVIEW_STATUSES: raise ASOCSBlindFirewallError("INVALID_REVIEW_STATUS")
    if status=="REVIEWED" and not str(payload.get("neutral_description","")).strip(): raise ASOCSBlindFirewallError("FREE_DESCRIPTION_REQUIRED")
    payload["review_status"]=status; payload["protocol_label"]="WITHIN_SINGLE_REVIEWER_PROTOCOL"; payload["frozen_before_reveal"]=True
    digest=hashlib.sha256(_canonical(payload)).hexdigest()
    return {**payload,"blind_record_sha256":digest}

def successor_annotation(frozen_record:Mapping[str,Any],annotation:Mapping[str,Any])->dict[str,Any]:
    if not frozen_record.get("frozen_before_reveal"): raise ASOCSBlindFirewallError("BASE_RECORD_NOT_FROZEN")
    return {"schema":"ovc-asocs-blind-successor-annotation/v0_1","predecessor_blind_record_sha256":str(frozen_record["blind_record_sha256"]),"annotation":dict(annotation),"mutates_predecessor":False}

def tradingview_trace_record(*,case_id:str,trace_timestamp:str,displayed_timezone:str,feed_label:str,mismatch_class:str)->dict[str,Any]:
    return {"case_id":case_id,"trace_timestamp":trace_timestamp,"displayed_timezone":displayed_timezone,"feed_label":feed_label,"mismatch_class":mismatch_class,"role":"SECONDARY_TRACE_NAVIGATION_ONLY","can_override_primary_adjudication":False}
