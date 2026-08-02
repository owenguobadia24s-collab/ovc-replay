from __future__ import annotations
from typing import Any, Mapping
RULES=("BOUNDARY_ZONE_ENTRY","BREACH_ACTIVE","RETURN_INSIDE","COMPRESSION_TO_DISPLACEMENT","LONG_PERSISTENCE","REPEATED_SWITCHING","LOCAL_PARENT_CONFLICT","ALIGNMENT_GAINED")
EXPECTED_CLASSES={"ALGORITHM_NOT_EVALUABLE_CONTROL":2338,"MATCHED_NON_TRIGGER_CONTROL":3368,"TRIGGER":1410}
EXPECTED_FIRED={"BOUNDARY_ZONE_ENTRY":388,"BREACH_ACTIVE":588,"RETURN_INSIDE":0,"COMPRESSION_TO_DISPLACEMENT":0,"LONG_PERSISTENCE":306,"REPEATED_SWITCHING":316,"LOCAL_PARENT_CONFLICT":0,"ALIGNMENT_GAINED":0}
class MTAWP5AuditError(ValueError): pass
def req(c,m):
 if not c: raise MTAWP5AuditError(m)
def validate_reference(v:Mapping[str,Any])->dict[str,Any]:
 req(v.get('schema')=='ovc-mta-wp5-marker-population-audit-reference/v1','SCHEMA')
 req((v.get('programme_id'),v.get('packet_id'),v.get('gate_id'))==('OVC-MTA-v0.2','MTA-WP5','MTA-G5'),'IDENTITY')
 p=v.get('population'); req(isinstance(p,dict),'POPULATION')
 req(p.get('eligible_windows')==7116 and p.get('rule_count')==8 and p.get('rule_attempts')==56928,'DENOMINATOR')
 req(p.get('candidate_class_counts')==EXPECTED_CLASSES,'CLASSES')
 req(p.get('rule_level_evaluable')+p.get('rule_level_not_evaluable')==56928,'RULE_ACCOUNTING')
 req(p.get('source_axis_not_evaluable_markers')==13993,'SOURCE_NE')
 req((p.get('parent_usable_target_resolutions'),p.get('parent_target_resolutions'),p.get('parent_usability_rate_percent'))==(615,4072,'15.103143'),'PARENT_RATE')
 rc=v.get('rule_counts'); req(isinstance(rc,dict) and tuple(sorted(rc))==tuple(sorted(RULES)),'RULE_SET')
 for r in RULES:
  x=rc[r]; req(x['attempted']==7116 and x['evaluable']+x['not_evaluable']==7116 and x['fired']+x['not_fired']==x['evaluable'],f'RULE_ACCOUNTING:{r}')
  req(x['fired']==EXPECTED_FIRED[r],f'FIRED:{r}')
 req(rc['LOCAL_PARENT_CONFLICT']['not_evaluable']==7116 and rc['ALIGNMENT_GAINED']['not_evaluable']==7116,'CROSS_SCALE')
 req(all(x==0 for x in v.get('mismatch_counts',{}).values()),'MISMATCH')
 a=v.get('external_artifact',{}); req(a.get('file_id')=='1Aqjax8L_5dj_QPs31zIpC0AdeWMMz4GO' and a.get('size_bytes')==7444145 and a.get('sha256')=='7044c02b1c20883736d1de1906c8099d2c9c0898effef95936b66efb82a5ad75','ARTIFACT')
 req(v.get('qa_recommendation')=='PASS_WITH_MATERIAL_FINDINGS','QA')
 for k,e in {'formula_threshold_change':'DENIED','marker_semantic_promotion':'DENIED','selector_change':'DENIED','c2e_c2_5_c3':'DENIED','validation_consumption':'DENIED','r2_publication':'DENIED','probability_risk_exposure_execution':'NONE'}.items(): req(v.get(k)==e,f'AUTHORITY:{k}')
 return {'status':'PASS','eligible_windows':7116,'rule_attempts':56928,'rule_level_not_evaluable':p['rule_level_not_evaluable'],'material_findings':sorted(x['finding_id'] for x in v['findings'])}
