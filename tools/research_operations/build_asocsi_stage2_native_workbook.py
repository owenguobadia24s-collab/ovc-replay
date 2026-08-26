#!/usr/bin/env python3
"""Build the append-only Session-1 Stage-2 native-observation review artifacts."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


REPLAY_CLASS = "C2_NATIVE_RUNTIME_AUDIT_REPLAY_NONAUTHORITATIVE"
PACKET_ID = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-REPLAY"
SOURCE_GAP_CASE_ID = "ASOCS.BLIND.9b251b8cfedc5e9a61396830"
COMPONENTS = ("HORIZON", "LEVEL", "CONTAINER", "RELATION")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_run(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def identity_projection(run: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in run.items() if key not in {"run_label", "logical_sha256", "identity_bearing_sha256"}}


def validate_runs(run_a: Mapping[str, Any], run_b: Mapping[str, Any]) -> None:
    for run in (run_a, run_b):
        if run.get("packet_id") != PACKET_ID or run.get("replay_class") != REPLAY_CLASS:
            raise ValueError("REPLAY_IDENTITY_MISMATCH")
        if len(run.get("cases", [])) != 25:
            raise ValueError("REPLAY_CASE_COUNT_MISMATCH")
        if run.get("firewall", {}).get("stage3_revealed") is not False:
            raise ValueError("STAGE3_FIREWALL_FAILED")
        statuses = [case["status"] for case in run["cases"]]
        if statuses.count("C2_NATIVE_OBSERVATION_AVAILABLE") != 24 or statuses.count("SOURCE_GAP_C2_NOT_FABRICATED") != 1:
            raise ValueError("REPLAY_CASE_STATUS_MISMATCH")
        gap = run["cases"][18]
        if gap["case_id"] != SOURCE_GAP_CASE_ID or any(gap[key] for key in ("horizons", "levels", "containers", "relations", "relation_sets")):
            raise ValueError("SOURCE_GAP_FABRICATION")
    if run_a["identity_bearing_sha256"] != run_b["identity_bearing_sha256"]:
        raise ValueError("IDENTITY_BEARING_SHA_MISMATCH")
    if canonical_bytes(identity_projection(run_a)) != canonical_bytes(identity_projection(run_b)):
        raise ValueError("IDENTITY_BEARING_PROJECTION_MISMATCH")


def extract_json_script(html: str, element_id: str) -> Any:
    match = re.search(rf'<script id="{re.escape(element_id)}" type="application/json">(.*?)</script>', html, re.S)
    if match is None:
        raise ValueError(f"MISSING_SCRIPT:{element_id}")
    return json.loads(match.group(1))


def template_from_base(base_html: str) -> dict[str, Any]:
    template = extract_json_script(base_html, "stage2-template")
    template.update({
        "schema": "ovc-asocsi-wp8-stage2-c2-native-observation-human-input-template/v0_1",
        "packet_id": "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-HUMAN-ADJUDICATION",
        "stage": "C2_PRIMITIVE_STRUCTURE",
        "reveal_index": "docs/programmes/asocs-v0-1/implementation/wp8/ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_REVEAL_INDEX_v0_1.json",
        "instructions": [
            "Use the exact frozen WP7 blind/source-native evidence as the human observational reference.",
            "Judge only the displayed actual C2 Horizon, Level, Container and Relation observations.",
            "Treat BID and UTC only as FORENSICALLY_SUPPORTED_NOT_DECLARED audit bindings.",
            "The source-gap case has no C2 observation; preserve that limitation and do not fabricate evidence.",
            "Do not use C2 composition, C2E, OccurrenceContext, Stage 3, cross-case rates or construct-survival conclusions.",
            "Complete all 25 placeholders in exact case order; no agent may supply or infer a human answer.",
        ],
    })
    return template


def audit_binding(run: Mapping[str, Any], wp7: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "ovc-asocsi-wp8-stage2-c2-native-observation-workbook-audit-binding/v0_1",
        "programme_id": "OVC-ASOCS-6M-v0.1",
        "packet_id": PACKET_ID,
        "session": 1,
        "stage": "C2_PRIMITIVE_STRUCTURE",
        "replay_class": REPLAY_CLASS,
        "identity_bearing_sha256": run["identity_bearing_sha256"],
        "source_sha256": run["source"]["sha256"],
        "case_sequence_sha256": run["case_sequence"]["sha256"],
        "c2_package_id": run["runtime"]["c2"]["package_id"],
        "c2_package_sha256": run["runtime"]["c2"]["package_sha256"],
        "forensic_binding": run["forensic_binding"],
        "anchor_cases": 24,
        "source_gap_cases": 1,
        "source_gap_case_id": SOURCE_GAP_CASE_ID,
        "source_gap": {"previous": "20260122 21:58:00", "next": "20260122 22:04:00", "delta_minutes": 6, "missing_slot_count": 5},
        "wp7_case_projection_sha256": sha256_bytes(canonical_bytes(wp7)),
        "human_response_prepopulation": "NONE",
        "construct_survival_decision": "PROHIBITED_DURING_CASE_REVIEW",
        "later_stage_firewall": {
            "c2_composition_included": False,
            "c2e_included": False,
            "occurrence_context_included": False,
            "stage3_reveal_started": False,
            "stage2_complete_session_freeze_required_before_stage3": True,
        },
    }


JS = r"""<script>
const WP7=JSON.parse(document.getElementById('wp7-data').textContent);
const C2=JSON.parse(document.getElementById('c2-native-data').textContent);
const BASE=JSON.parse(document.getElementById('stage2-template').textContent);
const AUDIT=JSON.parse(document.getElementById('stage2-audit').textContent);
const DISPOSITIONS=["COHERENT","COHERENT_SCOPE_RESTRICTED","MECHANICALLY_VALID_EMPIRICALLY_WEAK","OVER_SENSITIVE","UNDER_SENSITIVE","SEMANTICALLY_OVERLOADED","POSSIBLE_REDUNDANCY","REPRESENTATION_ARTEFACT","INFORMATION_GAP","NEEDS_REDEFINITION","INVALID","INDETERMINATE","SOURCE_LIMITED"];
const EVALUABILITY=["EVALUABLE","INFORMATION_GAP","SOURCE_LIMITED","INDETERMINATE"];
const CONFIDENCE=["HIGH","MODERATE","LOW"];
const COMPONENTS=['HORIZON','LEVEL','CONTAINER','RELATION'];
let idx=0;
const answers=BASE.cases.map(c=>({case_id:c.case_id,comparison_evaluability:null,component_judgements:{HORIZON:null,LEVEL:null,CONTAINER:null,RELATION:null},information_gap_disposition:null,case_notes:'',construct_survival_decision:'PROHIBITED_DURING_CASE_REVIEW'}));
function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
function options(items,value){return '<option value="">— choose —</option>'+items.map(x=>`<option value="${esc(x)}" ${x===value?'selected':''}>${esc(x.replaceAll('_',' '))}</option>`).join('');}
function complete(a){if(!a.comparison_evaluability||!a.information_gap_disposition)return false;for(const c of COMPONENTS){const x=a.component_judgements[c];if(!x||!x.disposition||!x.confidence||typeof x.notes!=='string')return false;}return typeof a.case_notes==='string';}
function updateProgress(){const n=answers.filter(complete).length;document.getElementById('progress').textContent=`${n} / 25 completed`;document.getElementById('export').disabled=n!==25;document.getElementById('jump').value=String(idx);}
function freezeWp7Controls(){document.querySelectorAll('.wp7-readonly input,.wp7-readonly textarea,.wp7-readonly select,.wp7-readonly button').forEach(el=>{el.disabled=true;el.tabIndex=-1;});}
function num(v){return typeof v==='number'?v.toFixed(5):v;}
function table(headers,rows){if(!rows.length)return '<p class="small">No emitted records at this anchor.</p>';return `<div class="tablewrap"><table><thead><tr>${headers.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(x=>`<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function nativeMachine(c){
 if(c.status==='SOURCE_GAP_C2_NOT_FABRICATED')return `<div class="card machine"><h4>Actual frozen C2 native-observation surface</h4><span class="badge">SOURCE GAP — NO C2 FABRICATED</span><p>No lawful C2 observation exists for this frozen source-gap case.</p></div>`;
 const o=c.observation||{};
 const hs=(c.horizons||[]).map(x=>[x.horizon_id,x.status,x.metadata?.requested_count??'',(x.member_observation_ids||[]).length,x.reason]);
 const ls=(c.levels||[]).map(x=>[x.horizon_id,x.level_type,num(x.value),x.origin,x.level_id]);
 const cs=(c.containers||[]).map(x=>[x.horizon_id,num(x.lower_value),num(x.upper_value),num(x.centre),num(x.width),x.container_id]);
 const rs=(c.relations||[]).map(x=>[x.object_kind,x.topology,num(x.signed_distance),x.object_id,x.relation_id]);
 return `<div class="card machine"><h4>Actual frozen C2 native-observation surface</h4><span class="badge">${esc(AUDIT.replay_class)}</span><p class="mono">Observation ${esc(o.observation_id)} • ${esc(o.first_valid_time)} • BID O/H/L/C ${esc(num(o.open))} / ${esc(num(o.high))} / ${esc(num(o.low))} / ${esc(num(o.close))}</p><details open><summary><b>Horizon memberships (${hs.length})</b></summary>${table(['Horizon','Status','Requested','Members','Reason'],hs)}</details><details open><summary><b>Levels (${ls.length})</b></summary>${table(['Horizon','Type','Value','Origin','Identity'],ls)}</details><details open><summary><b>Containers (${cs.length})</b></summary>${table(['Horizon','Lower','Upper','Centre','Width','Identity'],cs)}</details><details open><summary><b>Relations (${rs.length})</b></summary>${table(['Object kind','Topology','Signed distance','Object','Identity'],rs)}</details><p class="small">Audit-only, nonauthoritative replay. BID/UTC are forensic bindings, not declared provider provenance.</p></div>`;
}
function render(){
 const w=WP7[idx],c=C2[idx],a=answers[idx],kind=c.status==='SOURCE_GAP_C2_NOT_FABRICATED'?'SOURCE_GAP':'ANCHOR_15M';
 if(w.case_id!==c.case_id||w.case_id!==a.case_id)throw new Error('CASE_ORDER_BINDING_MISMATCH');
 const obs=Object.entries(w.observations||{}).map(([k,v])=>`<div class="obs"><b>${esc(k)} — frozen WP7 human observation</b>${esc(v)}</div>`).join('');
 const views=['local','development','wider'].map(k=>w.views_html&&w.views_html[k]?w.views_html[k]:'').join('');
 const comps=COMPONENTS.map(name=>{const x=a.component_judgements[name]||{disposition:null,confidence:null,notes:''};return `<div class="component"><h4>${name}</h4><div class="controls"><div class="field"><label class="required">Disposition</label><select data-component="${name}" data-part="disposition">${options(DISPOSITIONS,x.disposition)}</select></div><div class="field"><label class="required">Confidence</label><select data-component="${name}" data-part="confidence">${options(CONFIDENCE,x.confidence)}</select></div><div class="field full"><label class="required">Notes (may be empty)</label><textarea data-component="${name}" data-part="notes">${esc(x.notes||'')}</textarea></div></div></div>`;}).join('');
 document.getElementById('app').innerHTML=`
 <div class="case-head"><div><b>Case ${w.ordinal} of 25</b><div class="case-id">${esc(w.case_id)}</div></div><div class="small">${esc(kind)} • WP7 status: ${esc(w.review_status)} • anchor: ${esc(w.anchor_time)}</div></div>
 <section class="block"><h3>1. Frozen observational reference</h3><p>The exact frozen WP7 source/chart evidence and A0–A8 observations are read-only.</p><div class="wp7-readonly">${views}<div class="obs-grid">${obs}</div></div></section>
 <section class="block"><h3>2. Actual C2 Horizon / Level / Container / Relation observations</h3>${nativeMachine(c)}<div class="no-later">Not shown and not authorised: C2 composition, C2E, OccurrenceContext, Stage 3, construct survival, probability, risk, exposure, trading or execution.</div></section>
 <section class="block"><h3>3. Human Stage 2 judgement</h3><div class="controls"><div class="field"><label class="required">Comparison evaluability</label><select id="comparison">${options(EVALUABILITY,a.comparison_evaluability)}</select></div><div class="field"><label class="required">Information-gap disposition</label><select id="info-gap">${options(EVALUABILITY,a.information_gap_disposition)}</select></div></div><div class="grid" style="margin-top:12px">${comps}</div><div class="field" style="margin-top:12px"><label class="required">Case notes (may be empty)</label><textarea id="case-notes">${esc(a.case_notes)}</textarea></div><p><b>Construct survival:</b> PROHIBITED_DURING_CASE_REVIEW</p><p id="case-completion" class="small"></p></section>`;
 freezeWp7Controls();bind();updateProgress();document.getElementById('case-completion').textContent=complete(a)?'Case complete':'Case incomplete — all required selections must be made.';
}
function bind(){
 document.getElementById('comparison').addEventListener('change',e=>{answers[idx].comparison_evaluability=e.target.value||null;updateProgress();render();});
 document.getElementById('info-gap').addEventListener('change',e=>{answers[idx].information_gap_disposition=e.target.value||null;updateProgress();render();});
 document.getElementById('case-notes').addEventListener('input',e=>{answers[idx].case_notes=e.target.value;});
 document.querySelectorAll('[data-component]').forEach(el=>el.addEventListener(el.tagName==='TEXTAREA'?'input':'change',e=>{const name=e.target.dataset.component,part=e.target.dataset.part;let x=answers[idx].component_judgements[name];if(!x)x=answers[idx].component_judgements[name]={disposition:null,confidence:null,notes:''};x[part]=e.target.value||((part==='notes')?'':null);updateProgress();}));
}
function exportSubmission(){if(answers.filter(complete).length!==25)return;const out=structuredClone(BASE);out.cases=answers;const blob=new Blob([JSON.stringify(out,null,2)+'\n'],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_INPUT.json';a.click();URL.revokeObjectURL(u);}
const jump=document.getElementById('jump');WP7.forEach((c,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=`Case ${i+1} — ${c.case_id}`;jump.appendChild(o);});jump.addEventListener('change',e=>{idx=Number(e.target.value);render();scrollTo(0,0);});
document.getElementById('prev').addEventListener('click',()=>{idx=Math.max(0,idx-1);render();scrollTo(0,0);});document.getElementById('next').addEventListener('click',()=>{idx=Math.min(24,idx+1);render();scrollTo(0,0);});document.getElementById('export').addEventListener('click',exportSubmission);
if(WP7.length!==25||C2.length!==25||BASE.cases.length!==25)throw new Error('CASE_COUNT_MISMATCH');
render();
</script>"""


def build_html(base_html: str, run: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    wp7 = extract_json_script(base_html, "wp7-data")
    template = template_from_base(base_html)
    audit = audit_binding(run, wp7)
    if [item["case_id"] for item in wp7] != [item["case_id"] for item in run["cases"]]:
        raise ValueError("WP7_REPLAY_CASE_ORDER_MISMATCH")
    prefix = base_html.split('<script id="wp7-data"', 1)[0]
    wp7_script = re.search(r'<script id="wp7-data" type="application/json">.*?</script>', base_html, re.S).group(0)
    prefix = prefix.replace("ASOCSI WP8 — Session 1 — Stage 2 C2 Primitive Structure Review Workbook", "ASOCSI WP8 — Session 1 — Stage 2 C2 Native Observation Review Workbook")
    prefix = prefix.replace('data-stage="C2_PRIMITIVE_STRUCTURE"', 'data-stage="C2_NATIVE_OBSERVATION"')
    prefix = prefix.replace("25 frozen WP7 cases • Horizon / Level / Container / Relation only • Human scientific input required", "25 exact frozen cases • actual C2 Horizon / Level / Container / Relation • human scientific input required")
    prefix = prefix.replace("<div class=\"notice\"><strong>Machine audit limitation</strong>", "<div class=\"notice hidden\"><strong>Superseded machine limitation</strong>")
    prefix = prefix.replace("<div class=\"notice\"><strong>Scope firewall</strong>", "<div class=\"notice\"><strong>Scope firewall</strong>")
    prefix = prefix.replace("</style>", ".tablewrap{overflow:auto;margin:8px 0}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #bbb;padding:5px;text-align:left;vertical-align:top}details{margin:10px 0}\n</style>")
    prefix = re.sub(r'<div class="warning">.*?</div>', '<div class="warning"><strong>Human scientific boundary.</strong> Actual frozen C2 observations are displayed beside frozen WP7 evidence. No Stage 2 scientific answer is pre-filled, inferred, repaired or supplied by an agent.</div>', prefix, flags=re.S)
    prefix = re.sub(r'<div class="notice hidden"><strong>Superseded machine limitation</strong>.*?</div>', '<div class="notice"><strong>Replay qualification</strong> Two independent executions agree on identity-bearing output <span class="mono">'+run["identity_bearing_sha256"]+'</span>. Replay class: <b>'+REPLAY_CLASS+'</b>.</div>', prefix, flags=re.S)
    prefix = re.sub(r'<div class="notice"><strong>Scope firewall</strong>.*?</div>', '<div class="notice"><strong>Scope firewall</strong> BID and UTC are audit-only forensic bindings classified <b>FORENSICALLY_SUPPORTED_NOT_DECLARED</b>. Historical WP1/WP4 provenance is unchanged. C2E, OccurrenceContext, Stage 3 and construct survival remain unrevealed.</div>', prefix, flags=re.S)
    scripts = "\n".join([
        wp7_script,
        '<script id="c2-native-data" type="application/json">'+canonical_bytes(run["cases"]).decode("utf-8")+'</script>',
        '<script id="stage2-template" type="application/json">'+canonical_bytes(template).decode("utf-8")+'</script>',
        '<script id="stage2-audit" type="application/json">'+canonical_bytes(audit).decode("utf-8")+'</script>',
        JS,
        "</body></html>",
    ])
    return (prefix + scripts + "\n").encode("utf-8"), {"template": template, "audit": audit, "wp7": wp7}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--base-workbook", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    run_a, run_b = read_run(args.run_a), read_run(args.run_b)
    validate_runs(run_a, run_b)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    html_bytes, parts = build_html(args.base_workbook.read_text(encoding="utf-8"), run_a)
    workbook = args.out_dir / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REVIEW_WORKBOOK.html"
    workbook.write_bytes(html_bytes)
    receipt = {
        "schema": "ovc-asocsi-stage2-c2-native-observation-replay-determinism-receipt/v0_1",
        "programme_id": "OVC-ASOCS-6M-v0.1", "packet_id": PACKET_ID, "replay_class": REPLAY_CLASS,
        "result": "PASS_TWO_INDEPENDENT_IDENTITY_BEARING_REPLAYS_AGREE",
        "run_a": {"artifact_sha256": sha256_bytes(args.run_a.read_bytes()), "byte_size": args.run_a.stat().st_size, "logical_sha256": run_a["logical_sha256"]},
        "run_b": {"artifact_sha256": sha256_bytes(args.run_b.read_bytes()), "byte_size": args.run_b.stat().st_size, "logical_sha256": run_b["logical_sha256"]},
        "identity_bearing_sha256": run_a["identity_bearing_sha256"], "identity_bearing_projection_equal": True,
        "case_count": 25, "anchor_case_count": 24, "source_gap_case_count": 1, "totals": run_a["totals"],
        "firewall": run_a["firewall"],
    }
    (args.out_dir / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_DETERMINISM_RECEIPT.json").write_bytes(canonical_bytes(receipt) + b"\n")
    reveal = {
        "schema": "ovc-asocsi-stage2-c2-native-observation-replay-reveal-index/v0_1",
        "programme_id": "OVC-ASOCS-6M-v0.1", "packet_id": PACKET_ID, "session": 1,
        "stage": "C2_PRIMITIVE_STRUCTURE", "replay_class": REPLAY_CLASS,
        "identity_bearing_sha256": run_a["identity_bearing_sha256"], "forensic_binding": run_a["forensic_binding"],
        "runtime": run_a["runtime"], "source": run_a["source"], "case_sequence": run_a["case_sequence"],
        "case_count": 25, "case_ids": [item["case_id"] for item in run_a["cases"]], "cases": run_a["cases"],
        "human_judgements": [], "human_scientific_input_required": True,
        "construct_survival_decision": "PROHIBITED_DURING_CASE_REVIEW", "later_stage_firewall": parts["audit"]["later_stage_firewall"],
        "authority": {"active": False, "canonical": False, "publication": False, "validation": False},
    }
    (args.out_dir / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_REVEAL_INDEX.json").write_bytes(canonical_bytes(reveal) + b"\n")
    (args.out_dir / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_INPUT_TEMPLATE.json").write_bytes(canonical_bytes(parts["template"]) + b"\n")
    print(json.dumps({"workbook": str(workbook), "workbook_sha256": sha256_bytes(html_bytes), "workbook_byte_size": len(html_bytes), "identity_bearing_sha256": run_a["identity_bearing_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
