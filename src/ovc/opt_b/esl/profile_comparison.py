from __future__ import annotations
import hashlib, json, os, platform, resource, sys, time
from collections import Counter
from pathlib import Path
from typing import Any

PROFILES=("BASE_STRUCTURAL","ORGANISATION_ENRICHED","CONSTRAINT_ENRICHED","FULL_RESEARCH")

class ProfileComparisonError(ValueError): pass

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def lh(v:Any)->str: return hashlib.sha256(canon(v)).hexdigest()

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def env()->dict[str,Any]:
    return {"python_version":platform.python_version(),"implementation":sys.implementation.name,
            "platform_system":platform.system(),"platform_machine":platform.machine(),
            "platform_release":platform.release(),"libc":list(platform.libc_ver()),
            "processor_count":os.cpu_count()}

def load_manifest(path:Path)->dict[str,Any]:
    m=json.loads(path.read_text())
    if m["schema"]!="ovc-esl-june-profile-comparison-manifest/v1": raise ProfileComparisonError("MANIFEST_SCHEMA")
    if m["freeze_state"]!="FROZEN_BEFORE_PROFILE_RESULT_INSPECTION": raise ProfileComparisonError("MANIFEST_NOT_PREFROZEN")
    if tuple(m["profiles"])!=PROFILES: raise ProfileComparisonError("PROFILE_ORDER")
    if m["winner_synthesis"]!="FORBIDDEN": raise ProfileComparisonError("PROFILE_WINNER_SYNTHESIS_FORBIDDEN")
    return m

def rows(path:Path)->list[dict[str,Any]]:
    out=[]
    with path.open("rb") as f:
        for i,line in enumerate(f,1):
            if not line.strip(): continue
            try: x=json.loads(line)
            except Exception as e: raise ProfileComparisonError(f"SOURCE_JSON_INVALID:{i}") from e
            if not isinstance(x,dict): raise ProfileComparisonError(f"SOURCE_ROW_OBJECT_REQUIRED:{i}")
            out.append(x)
    return out

def bind_source(path:Path,m:dict[str,Any])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    s=m["source"]
    if path.stat().st_size!=s["byte_size"]: raise ProfileComparisonError("SOURCE_BYTE_SIZE_MISMATCH")
    if sha(path)!=s["sha256"]: raise ProfileComparisonError("SOURCE_SHA256_MISMATCH")
    allr=rows(path)
    target=sorted((r for r in allr if r.get("target_eligible") is True),
                  key=lambda r:(str(r.get("first_valid_time")),str(r.get("c2_state_id"))))
    ids=sorted(str(r["c2_state_id"]) for r in target)
    cuts=sorted((str(r["c2_state_id"]),str(r["first_valid_time"])) for r in target)
    p=m["population"]
    if len(target)!=p["eligible_record_count"] or lh(ids)!=p["eligible_ids_sha256"]:
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:POPULATION")
    if lh(cuts)!=m["cutoff_schedule"]["sha256"]:
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:CUTOFF")
    for r in target:
        if r.get("source_slice_id")!=s["source_slice_id"] or r.get("side")!=s["side"] or r.get("clock")!=s["clock"]:
            raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:SCOPE")
    return allr,target

def measured(fn):
    w=time.perf_counter_ns(); c=time.process_time_ns(); result=fn()
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return result,{"wall_seconds":(time.perf_counter_ns()-w)/1e9,
                   "process_cpu_seconds":(time.process_time_ns()-c)/1e9,
                   "peak_rss_kib":int(rss)}

def p0(target:list[dict[str,Any]],m:dict[str,Any])->dict[str,Any]:
    axes={}
    for a in ("LOCATION","MOTION","ORGANISATION","INTERACTION","QUALITY"):
        st=Counter(); vals=Counter(); rs=Counter()
        for r in target:
            x=(r.get("axes") or {}).get(a) or {}
            state=str(x.get("status") or x.get("evidence_state") or "UNKNOWN"); st[state]+=1
            val=x.get("value")
            if val is not None: vals[json.dumps(val,sort_keys=True,separators=(",",":"))]+=1
            rc=x.get("reason_code")
            if rc: rs[str(rc)]+=1
            for q in x.get("reason_codes") or []: rs[str(q)]+=1
        axes[a]={"evidence_state_counts":dict(sorted(st.items())),
                 "distinct_value_count":len(vals),"reason_code_counts":dict(sorted(rs.items()))}
    structural=("LOCATION","MOTION","ORGANISATION","INTERACTION")
    def ev(r,a):
        x=(r.get("axes") or {}).get(a) or {}
        return str(x.get("status") or x.get("evidence_state") or "UNKNOWN") not in {"NOT_EVALUATED","NOT_EVALUABLE","MISSING","UNKNOWN"}
    payload={"schema":"ovc-esl-profile-information-entry/v1","profile":"BASE_STRUCTURAL",
             "execution_status":"EXECUTED_SOURCE_BOUND_SUMMARY",
             "common_population":{"eligible_record_count":len(target),"eligible_ids_sha256":m["population"]["eligible_ids_sha256"],
                                  "cutoff_schedule_sha256":m["cutoff_schedule"]["sha256"]},
             "information_vector":{"axis_summary":axes,
                "records_with_any_structural_axis_evaluated":sum(any(ev(r,a) for a in structural) for r in target),
                "records_with_all_four_structural_axes_evaluated":sum(all(ev(r,a) for a in structural) for r in target),
                "records_with_level_refs":sum(bool(r.get("level_ids")) for r in target),
                "records_with_container_refs":sum(bool(r.get("container_ids")) for r in target),
                "records_with_persistence":sum(bool(r.get("persistence")) for r in target),
                "continuity_counts":dict(sorted(Counter(str(r.get("continuity") or "UNKNOWN") for r in target).items()))},
             "structural_occurrence_projection":{"execution_status":"NOT_EXECUTABLE_FROM_THIS_ACCEPTED_SOURCE_SURFACE",
                "reason_code":"SOURCE_SURFACE_IS_C2_STATE_SUMMARY_NOT_C2_OBSERVATION_VNEXT_R1","no_synthetic_observation_conversion":True},
             "c3_projection":{"execution_status":"NOT_EXECUTABLE_UPSTREAM_STRUCTURAL_OCCURRENCE_NOT_MATERIALIZED",
                              "c3_bridge_maturity":"INACTIVE_REFERENCE"},
             "authority_effect":"NONE"}
    payload["logical_hash"]=lh(payload); return payload

def absent(profile:str,reason:str,m:dict[str,Any])->dict[str,Any]:
    x={"schema":"ovc-esl-profile-information-entry/v1","profile":profile,
       "execution_status":"NOT_EXECUTABLE_UNDER_CURRENT_PACK","reason_code":reason,
       "common_population":{"eligible_record_count":m["population"]["eligible_record_count"],
                            "eligible_ids_sha256":m["population"]["eligible_ids_sha256"],
                            "cutoff_schedule_sha256":m["cutoff_schedule"]["sha256"]},
       "information_vector":{"typed_absence":True},"authority_effect":"NONE"}
    x["logical_hash"]=lh(x); return x

def p3(p0x,p1x,p2x,m):
    hand={"schema":"ovc-esl-full-research-handoff/v1","handoff_status":"FULL_RESEARCH_HANDOFF",
          "source_profile_hashes":{"BASE_STRUCTURAL":p0x["logical_hash"],"ORGANISATION_ENRICHED":p1x["logical_hash"],
                                   "CONSTRAINT_ENRICHED":p2x["logical_hash"]},
          "source_population_sha256":m["population"]["eligible_ids_sha256"],
          "research_candidate_generation":"NOT_PERFORMED","structural_term_admission":"NONE","mechanism_claim":"NONE",
          "downstream_runtime":"DOWNSTREAM_RUNTIME_NOT_MATERIALIZED","authority_effect":"NONE"}
    hand["logical_hash"]=lh(hand)
    x={"schema":"ovc-esl-profile-information-entry/v1","profile":"FULL_RESEARCH",
       "execution_status":"FULL_RESEARCH_HANDOFF","reason_code":"DOWNSTREAM_RUNTIME_NOT_MATERIALIZED",
       "common_population":{"eligible_record_count":m["population"]["eligible_record_count"],
                            "eligible_ids_sha256":m["population"]["eligible_ids_sha256"],
                            "cutoff_schedule_sha256":m["cutoff_schedule"]["sha256"]},
       "information_vector":{"handoff_object_count":1,"handoff":hand},"authority_effect":"NONE"}
    x["logical_hash"]=lh(x); return x

def execute(source:Path,manifest:Path,out:Path)->dict[str,str]:
    m=load_manifest(manifest)
    if env()!=m["execution_environment"]: raise ProfileComparisonError("PROFILE_CAPACITY_NOT_COMPARABLE:ENVIRONMENT_MISMATCH")
    (allr,target),cold=measured(lambda:bind_source(source,m)); (_,target2),warm=measured(lambda:bind_source(source,m))
    if [r["c2_state_id"] for r in target]!=[r["c2_state_id"] for r in target2]: raise ProfileComparisonError("WARM_SOURCE_DRIFT")
    p0x,p0cap=measured(lambda:p0(target,m))
    p1x=absent("ORGANISATION_ENRICHED","MATCHING_SFC_FAMILY_CATALOG_NOT_MATERIALIZED_FOR_FROZEN_POPULATION",m)
    p2x=absent("CONSTRAINT_ENRICHED","CONSTRAINT_COMPARATOR_NOT_MATERIALIZED",m)
    p3x,p3cap=measured(lambda:p3(p0x,p1x,p2x,m))
    info={"schema":"ovc-esl-profile-information-ledger/v1","manifest_id":m["manifest_id"],
          "entries":[p0x,p1x,p2x,p3x],"winner_synthesis":"FORBIDDEN","authority_effect":"NONE"}; info["logical_hash"]=lh(info)
    cap={"schema":"ovc-esl-profile-capacity-ledger/v1","manifest_id":m["manifest_id"],"execution_environment":env(),
         "source_measurements":{"cold":cold,"warm":warm},"profile_measurements":[
          {"profile":"BASE_STRUCTURAL","status":"EXECUTED_SOURCE_BOUND_SUMMARY","cold":p0cap},
          {"profile":"ORGANISATION_ENRICHED","status":"NOT_EXECUTABLE_UNDER_CURRENT_PACK","cold":None},
          {"profile":"CONSTRAINT_ENRICHED","status":"NOT_EXECUTABLE_UNDER_CURRENT_PACK","cold":None},
          {"profile":"FULL_RESEARCH","status":"FULL_RESEARCH_HANDOFF","cold":p3cap}],
         "generated_information_bytes":len(canon(info)),"cache_policy":m["cache_policy"],"checkpoint_policy":m["checkpoint_policy"],
         "authority_effect":"NONE"}
    marginal={"schema":"ovc-esl-marginal-profile-delta-ledger/v1","manifest_id":m["manifest_id"],"baseline_profile":"BASE_STRUCTURAL",
      "entries":[
       {"profile":"ORGANISATION_ENRICHED","information_delta":"TYPED_ABSENCE_NOT_ZERO","capacity_delta":"NOT_COMPARABLE_PROFILE_NOT_EXECUTABLE"},
       {"profile":"CONSTRAINT_ENRICHED","information_delta":"TYPED_ABSENCE_NOT_ZERO","capacity_delta":"NOT_COMPARABLE_PROFILE_NOT_EXECUTABLE"},
       {"profile":"FULL_RESEARCH","information_delta":{"handoff_objects_added":1},"capacity_delta":p3cap}],
      "winner_synthesis":"FORBIDDEN","authority_effect":"NONE"}
    absence={"schema":"ovc-esl-profile-absence-disagreement-ledger/v1","manifest_id":m["manifest_id"],"entries":[
      {"profile":"BASE_STRUCTURAL","state":"PARTIAL_EXECUTABILITY","reason_code":"SOURCE_SURFACE_IS_C2_STATE_SUMMARY_NOT_C2_OBSERVATION_VNEXT_R1"},
      {"profile":"ORGANISATION_ENRICHED","state":"NOT_EXECUTABLE_UNDER_CURRENT_PACK","reason_code":"MATCHING_SFC_FAMILY_CATALOG_NOT_MATERIALIZED_FOR_FROZEN_POPULATION"},
      {"profile":"CONSTRAINT_ENRICHED","state":"NOT_EXECUTABLE_UNDER_CURRENT_PACK","reason_code":"CONSTRAINT_COMPARATOR_NOT_MATERIALIZED"},
      {"profile":"FULL_RESEARCH","state":"FULL_RESEARCH_HANDOFF","reason_code":"DOWNSTREAM_RUNTIME_NOT_MATERIALIZED"}],
      "winner_synthesis":"FORBIDDEN","authority_effect":"NONE"}
    receipt={"schema":"ovc-esl-wp13-reproducibility-authority-receipt/v1","manifest_id":m["manifest_id"],
      "source":{"sha256":sha(source),"byte_size":source.stat().st_size,"row_count":len(allr),"eligible_record_count":len(target),
                "eligible_ids_sha256":m["population"]["eligible_ids_sha256"],"cutoff_schedule_sha256":m["cutoff_schedule"]["sha256"]},
      "profile_result_hashes":{x["profile"]:x["logical_hash"] for x in info["entries"]},"information_ledger_logical_hash":info["logical_hash"],
      "authority":{"validation":"LOCKED_UNCONSUMED","provider_fetch":"DENIED","selector_change":"NONE","scientific_promotion":"NONE",
                   "semantic_admission":"NONE","c3_activation":"NONE","publication":"NONE","probability_risk_exposure_execution":"NONE",
                   "winner_synthesis":"FORBIDDEN"}}
    docs={"ProfileInformationLedger_v1.json":info,"ProfileCapacityLedger_v1.json":cap,"MarginalProfileDeltaLedger_v1.json":marginal,
          "ProfileAbsenceDisagreementLedger_v1.json":absence,"ESLI_WP13_REPRODUCIBILITY_AUTHORITY_RECEIPT.json":receipt}
    out.mkdir(parents=True,exist_ok=True)
    for n,v in docs.items(): (out/n).write_text(json.dumps(v,sort_keys=True,separators=(",",":"))+"\n")
    return {n:sha(out/n) for n in sorted(docs)}

if __name__=="__main__":
    if len(sys.argv)!=4: raise SystemExit("usage: profile_comparison_v2.py SOURCE MANIFEST OUTPUT_DIR")
    print(json.dumps(execute(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3])),sort_keys=True))
