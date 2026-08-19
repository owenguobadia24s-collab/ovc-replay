"""Deterministic, audit-only ASOCS G1 population materialisation."""
from datetime import timedelta
from pathlib import Path
import hashlib
from .population_core import *
from .population_aggregate import build_15m, build_2h

def materialize_population(source_path:str|Path,external_parent:str|Path,*,expected_sha256:str,source_logical_name:str,renderer_reference_max_bars:int=96)->MaterializationResult:
    rows,byte_size=read_source(Path(source_path),expected_sha256)
    contract={"schema":"ovc-asocs-g1-generation-contract/v0_1","source_logical_name":source_logical_name,"source_sha256":expected_sha256,"target_start":literal(TARGET_START),"target_end":literal(TARGET_END),"source_clock_state":SOURCE_CLOCK_STATE,"source_side_state":SOURCE_SIDE_STATE,"claim_class":CLAIM_CLASS,"lattice_15m":{"id":LATTICE_15M_ID,"slots":15,"anchor":"SOURCE_LITERAL_DAY_00:00"},"lattice_2h":{"id":LATTICE_2H_ID,"parents":8,"anchor":"SOURCE_LITERAL_DAY_00:00","labels":"A-L"},"repair_policy":"NO_INTERPOLATION_NO_FILL_NO_SUBSTITUTION","authority_class":AUTHORITY_CLASS}
    gid=canonical_sha256(contract); logical=f"asocs/g1/{gid}"; root=Path(external_parent)/gid; root.mkdir(parents=True,exist_ok=True)
    regions={"PRE_CONTEXT":0,"TARGET":0,"POST_CONTEXT":0}; m1=[]
    for r in rows:
        reg=region(r.source_time); regions[reg]+=1
        m1.append({"schema":"ovc-asocs-m1-source-index-record/v0_1","source_row_id":r.source_row_id,"source_sha256":expected_sha256,"row_number":r.row_number,"literal_timestamp":r.literal_timestamp,"source_clock_state":SOURCE_CLOCK_STATE,"price_side":SOURCE_SIDE_STATE,"region":reg,"ohlc":{"open":r.open,"high":r.high,"low":r.low,"close":r.close},"volume":r.volume,"authority_class":AUTHORITY_CLASS,"active":False})
    gaps=[]
    for a,b in zip(rows,rows[1:]):
        d=int((b.source_time-a.source_time).total_seconds()//60)
        if d>1:
            p={"previous_source_row_id":a.source_row_id,"next_source_row_id":b.source_row_id,"previous_literal_timestamp":a.literal_timestamp,"next_literal_timestamp":b.literal_timestamp,"delta_minutes":d,"missing_slot_count":d-1,"previous_region":region(a.source_time),"next_region":region(b.source_time)}
            gaps.append({"schema":"ovc-asocs-source-gap-ledger-record/v0_1","gap_id":f"asocs:gap:{canonical_sha256(p)}",**p,"state":"OBSERVED_SOURCE_GAP","cause_classification":"UNKNOWN_SOURCE_ABSENCE","proven_market_closure":False,"repair_applied":False,"authority_class":AUTHORITY_CLASS})
    s15,complete15=build_15m(rows,expected_sha256); s2=build_2h(rows,complete15,expected_sha256)
    arts=[]
    for name,recs in (("m1_source_index.jsonl.gz",m1),("source_gap_ledger.jsonl.gz",gaps),("audit_15m_surface.jsonl.gz",s15),("audit_2h_a_l_surface.jsonl.gz",s2)):
        arts.append({"logical_name":f"{logical}/{name}",**write_gzip_jsonl(root/name,recs)})
    if renderer_reference_max_bars<=0: raise ASOCSPopulationError("RENDERER_REFERENCE_MAX_BARS_INVALID")
    starts=sorted(t for t in complete15 if region(t)=="TARGET"); runs=[]; run=[]
    for t in starts:
        if not run or t==run[-1]+timedelta(minutes=15): run.append(t)
        else: runs.append(run); run=[t]
    if run:runs.append(run)
    if not runs: raise ASOCSPopulationError("NO_COMPLETE_TARGET_15M_RENDERER_REFERENCE_WINDOW")
    best=sorted(runs,key=lambda r:(-len(r),r[0]))[0][:renderer_reference_max_bars]; ref=[complete15[t] for t in best]; sp=root/f"renderer_reference_{len(ref)}x15m.svg"; sp.write_text(render_source_native_svg(ref),encoding="utf-8",newline="\n"); sb=sp.read_bytes(); arts.append({"logical_name":f"{logical}/{sp.name}","sha256":hashlib.sha256(sb).hexdigest(),"byte_size":len(sb),"record_count":len(ref)})
    def count(surface,reg,status):return sum(x["region"]==reg and x["status"]==status for x in surface)
    def rsc(surface):
        d={}
        for x in surface:d.setdefault(str(x["region"]),{}).setdefault(str(x["status"]),0);d[str(x["region"])][str(x["status"])]+=1
        return {r:dict(sorted(v.items())) for r,v in sorted(d.items())}
    def months(surface,status):
        d={}
        for x in surface:
            if x["region"]=="TARGET" and x["status"]==status:m=str(x["interval_start"])[:7];d[m]=d.get(m,0)+1
        return dict(sorted(d.items()))
    gr={}
    for g in gaps:k=f'{g["previous_region"]}->{g["next_region"]}';gr[k]=gr.get(k,0)+1
    tg=[g for g in gaps if g["previous_region"]==g["next_region"]=="TARGET"];tc=[x for x in s15 if x["region"]=="TARGET" and x["status"]=="COMPLETE"]
    manifest={"schema":"ovc-asocs-population-manifest/v0_1","programme_id":"OVC-ASOCS-6M-v0.1","packet_id":"ASOCSI-WP2","gate_id":"ASOCSI-G1","population_generation_id":gid,"generation_contract":contract,"source":{"logical_name":source_logical_name,"sha256":expected_sha256,"byte_size":byte_size,"row_count":len(rows),"region_row_counts":regions},"gap_ledger":{"gap_count_all_source":len(gaps),"region_transition_counts":dict(sorted(gr.items())),"target_internal_gap_count":len(tg),"target_shortest_delta_minutes":min((int(g["delta_minutes"]) for g in tg),default=None),"target_longest_delta_minutes":max((int(g["delta_minutes"]) for g in tg),default=None),"closure_assertions":0,"repair_count":0},"surface_15m":{"lattice_id":LATTICE_15M_ID,"total_expected_buckets":len(s15),"complete":sum(x["status"]=="COMPLETE" for x in s15),"incomplete":sum(x["status"]=="INCOMPLETE" for x in s15),"absent":sum(x["status"]=="ABSENT" for x in s15),"target_complete":count(s15,"TARGET","COMPLETE"),"target_incomplete":count(s15,"TARGET","INCOMPLETE"),"target_absent":count(s15,"TARGET","ABSENT"),"target_first_complete_interval_start":str(tc[0]["interval_start"]),"target_last_complete_interval_start":str(tc[-1]["interval_start"]),"region_status_counts":rsc(s15),"target_complete_month_counts":months(s15,"COMPLETE")},"surface_2h_a_l":{"lattice_id":LATTICE_2H_ID,"total_expected_buckets":len(s2),"complete":sum(x["status"]=="COMPLETE" for x in s2),"unavailable":sum(x["status"]=="UNAVAILABLE" for x in s2),"target_complete":count(s2,"TARGET","COMPLETE"),"target_unavailable":count(s2,"TARGET","UNAVAILABLE"),"region_status_counts":rsc(s2),"target_complete_month_counts":months(s2,"COMPLETE")},"renderer":{"contract":RENDERER_CONTRACT,"contract_id":canonical_sha256(RENDERER_CONTRACT),"reference_window_start":str(ref[0]["interval_start"]),"reference_window_end":str(ref[-1]["interval_end"]),"reference_bar_count":len(ref),"reference_max_bar_cap":renderer_reference_max_bars,"reference_selection":"LONGEST_COMPLETE_TARGET_CONTINUITY_RUN_EARLIEST_TIE_CAPPED_FOR_PRESENTATION","network_dependency":False},"external_artifacts":sorted(arts,key=lambda x:str(x["logical_name"])),"population_freeze":"G1_FROZEN_BEFORE_STRUCTURAL_COMPUTATION_OR_REVIEW_SAMPLING","structural_computation_started":False,"review_sampling_started":False,"source_bytes_mutated":False,"source_repair_applied":False,"active_provider":False,"selector_eligible":False,"ec1_eligible":False,"canonical":False,"publication":False,"authority_class":AUTHORITY_CLASS}
    manifest["population_manifest_id"]=canonical_sha256(manifest);(root/"population_manifest.json").write_bytes(canonical_json_bytes(manifest)+b"\n");return MaterializationResult(manifest,root)
