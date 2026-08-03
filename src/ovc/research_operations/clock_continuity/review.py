from __future__ import annotations
from typing import Any, Mapping

VARIANTS=("V0_CURRENT_STRICT_CONTINUITY_AUTHORITATIVE","V1_PLANNED_CLOSURE_CLASSIFIED_CONTINUITY_SHADOW_ONLY","V2_PROVIDER_GAP_SEGMENTED_CONTINUITY_SHADOW_ONLY")
class CCRAuditError(ValueError): pass
def req(value:bool, marker:str)->None:
    if not value: raise CCRAuditError(marker)

def validate_reference(v:Mapping[str,Any])->dict[str,Any]:
    req(v.get("schema")=="ovc-ccr-full-audit-reference/v1","SCHEMA")
    req(v.get("programme_id")=="OVC-CLOCK-CONTINUITY-REVIEW-v0.1","PROGRAMME")
    art=v.get("external_artifact",{})
    req((art.get("file_id"),art.get("size_bytes"),art.get("sha256"))==("17aSvdnbnNivG5efnVnI8PII7veQpBeSx",50836,"57edecdef747a14ef9d1d27f6dd94f4a7bfb1bfde5035a266cec2144a2e71bfa"),"ARTIFACT")
    clocks=v.get("clock_reconstruction",{})
    for clock,count,parent_count in (("15M",2231,15),("2H_A_L",248,120)):
        for side in ("ASK","BID"):
            row=clocks[clock][side]
            req(row["records"]==count and row["duration_membership_mismatches"]==0,f"CLOCK:{clock}:{side}")
            req(row["parent_m1_count_distribution"]=={str(parent_count):count},f"PARENTS:{clock}:{side}")
    for side in ("ASK","BID"):
        reset=v["reset_census"][side]
        req(reset["causes"]=={"PROVIDER_GAP":48,"SCHEDULED_WEEKEND_CLOSURE":4,"SOURCE_PARTITION_START":1},f"RESET:{side}")
        req(reset["unknown_count"]==0,f"UNKNOWN:{side}")
        warm=v["warmup_summary"][side]["LOCATION"]
        req(warm["PROVIDER_GAP"]["bars_median"]=="32",f"GAP_WARMUP:{side}")
        req(warm["SCHEDULED_WEEKEND_CLOSURE"]["bars_median"]=="31.0",f"CLOSURE_WARMUP:{side}")
    variants=v.get("variants",{})
    req(tuple(variants)==VARIANTS,"VARIANTS")
    req(variants[VARIANTS[0]]["identity_changes"]==0,"V0_IDENTITY")
    req(variants[VARIANTS[1]]["potentially_changed_state_ids_total"]==496,"V1_SCOPE")
    req(variants[VARIANTS[1]]["bars_created"]==0 and variants[VARIANTS[1]]["activation"]=="DENIED","V1_AUTHORITY")
    req(variants[VARIANTS[2]]["identity_changes"]==0 and variants[VARIANTS[2]]["bars_created"]==0,"V2_IDENTITY")
    consequences=v["translation_consequences"]
    req((consequences["target_parent_available"],consequences["target_parent_total"],consequences["active_parent_range_target_states"])==(615,4072,0),"CONSEQUENCES")
    req(v["recommendation"]["clock"]=="KEEP_CURRENT_2H_A_L_UTC_CLOCK","CLOCK_RECOMMENDATION")
    req(v["recommendation"]["activation"]=="DENIED","ACTIVATION")
    req(v["qa_recommendation"]=="PASS_WITH_MATERIAL_FINDINGS","QA")
    req(v["authority"]["clock_or_continuity_activation"]=="DENIED","AUTHORITY")
    return {"status":"PASS","programme_id":v["programme_id"],"target_parent_available":615,"potentially_changed_shadow_states":496}

def build_read_model(v:Mapping[str,Any])->dict[str,Any]:
    validate_reference(v)
    return {"route":"/clock-continuity-review","read_only":True,"current_clock":v["authority"]["current_clock"],"variants":list(v["variants"]),"findings":list(v["findings"]),"recommendation":dict(v["recommendation"]),"activation":"DENIED"}
