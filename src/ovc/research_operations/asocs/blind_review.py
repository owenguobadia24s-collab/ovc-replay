"""ASOCS WP7 blind-review infrastructure; creates no human scientific evidence."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
import hashlib, json, re
from typing import Any, Mapping, Sequence

from .population_core import RENDERER_CONTRACT

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

def _parse_literal_time(value:Any)->datetime:
    if isinstance(value,datetime):
        return value
    text=str(value).strip()
    if not text: raise ASOCSBlindFirewallError("REVIEW_TIME_MISSING")
    try:
        return datetime.fromisoformat(text)
    except ValueError as e:
        raise ASOCSBlindFirewallError("REVIEW_TIME_INVALID:"+text) from e

def review_anchor_time(window:Mapping[str,Any])->datetime:
    """Return the neutral WP7 review anchor: the exact midpoint of one navigation window."""
    start=_parse_literal_time(window.get("start")); end=_parse_literal_time(window.get("end"))
    if end<=start: raise ASOCSBlindFirewallError("REVIEW_WINDOW_NONPOSITIVE")
    return start+(end-start)/2

def review_anchor_partition(bars:Sequence[Mapping[str,Any]],window:Mapping[str,Any])->tuple[datetime,int]:
    """Locate the anchor between the last pre-anchor and first at/after-anchor rendered bars.

    Source-native SVGs deliberately collapse literal source gaps rather than invent missing bars.  The
    anchor therefore uses the rendered bar chronology, not geometric 50%, so a gap cannot move the
    before/after scientific partition to the wrong candle.
    """
    if len(bars)<2: raise ASOCSBlindFirewallError("REVIEW_ANCHOR_REQUIRES_TWO_BARS")
    anchor=review_anchor_time(window)
    starts=[]
    for bar in bars:
        if "interval_start" not in bar: raise ASOCSBlindFirewallError("REVIEW_BAR_INTERVAL_START_MISSING")
        starts.append(_parse_literal_time(bar["interval_start"]))
    if any(b<=a for a,b in zip(starts,starts[1:])): raise ASOCSBlindFirewallError("REVIEW_BAR_TIMES_NON_MONOTONIC")
    split=sum(t<anchor for t in starts)
    if split<=0 or split>=len(starts): raise ASOCSBlindFirewallError("REVIEW_ANCHOR_OUTSIDE_RENDERED_BAR_SPAN")
    return anchor,split

def overlay_visible_review_anchor(svg:str,bars:Sequence[Mapping[str,Any]],window:Mapping[str,Any])->str:
    """Add a neutral visible anchor overlay without changing the frozen candle geometry or evidence identity."""
    if 'data-asocs-review-anchor="visible-neutral-reference"' in svg: raise ASOCSBlindFirewallError("REVIEW_ANCHOR_ALREADY_PRESENT")
    if "</svg>" not in svg: raise ASOCSBlindFirewallError("REVIEW_SVG_CLOSE_TAG_MISSING")
    anchor,split=review_anchor_partition(bars,window)
    w=int(RENDERER_CONTRACT["fixed_width"]); h=int(RENDERER_CONTRACT["fixed_height"]); p=int(RENDERER_CONTRACT["padding"]); prec=int(RENDERER_CONTRACT["coordinate_precision"])
    step=Decimal(w-2*p)/Decimal(len(bars)); x=Decimal(p)+Decimal(split)*step
    label=anchor.isoformat()
    overlay=(f'<g data-asocs-review-anchor="visible-neutral-reference" data-anchor-time="{label}">\n'
             f'<line x1="{x:.{prec}f}" y1="{p}" x2="{x:.{prec}f}" y2="{h-p}" stroke="black" stroke-width="2" stroke-dasharray="8 6"/>\n'
             f'<text x="{x+Decimal(4):.{prec}f}" y="{p+16}" font-size="14" font-family="system-ui,sans-serif">REVIEW ANCHOR</text>\n'
             f'</g>\n')
    return svg.replace("</svg>",overlay+"</svg>",1)

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
