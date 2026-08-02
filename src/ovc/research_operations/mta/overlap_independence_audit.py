from __future__ import annotations
from typing import Any,Mapping
EXPECTED={'STRICT_OVERLAP':(24,92),'PRIMARY_OVERLAP_PLUS_1':(20,166),'PERMISSIVE_OVERLAP_PLUS_4':(18,251)}
class MTAWP6AuditError(ValueError):pass
def req(c,m):
 if not c:raise MTAWP6AuditError(m)
def validate_reference(v:Mapping[str,Any])->dict[str,Any]:
 req(v.get('schema')=='ovc-mta-wp6-overlap-independence-audit-reference/v1','SCHEMA')
 req((v.get('programme_id'),v.get('packet_id'),v.get('gate_id'))==('OVC-MTA-v0.2','MTA-WP6','MTA-G6'),'IDENTITY')
 req(v.get('source_wp5_sha256')=='7044c02b1c20883736d1de1906c8099d2c9c0898effef95936b66efb82a5ad75','SOURCE')
 req(v.get('occurrence_count')==1779,'OCCURRENCES')
 req(v.get('collapse_rule')=='IDENTICAL_CENTER_TIME_ACROSS_BID_ASK_AND_LOCAL_PARENT_SCOPES','COLLAPSE')
 req(v.get('primary_variant')=='PRIMARY_OVERLAP_PLUS_1','PRIMARY')
 variants=v.get('variants_summary');req(isinstance(variants,dict) and set(variants)==set(EXPECTED),'VARIANTS')
 for name,(count,max_size) in EXPECTED.items():
  x=variants[name];req(x.get('occurrence_count')==1779 and x.get('cluster_count')==count and x.get('max_cluster_size')==max_size,f'VARIANT:{name}')
  req(sum(int(size)*int(n) for size,n in x.get('cluster_size_histogram',{}).items())==1779,f'HISTOGRAM:{name}')
 req(v.get('sensitivity_counts')=={'MATERIAL_SENSITIVITY':1456,'STRUCTURALLY_UNSTABLE':323},'SENSITIVITY')
 req(sum(v['sensitivity_counts'].values())==1779,'SENSITIVITY_TOTAL')
 req(all(x==0 for x in v.get('mismatch_counts',{}).values()),'MISMATCH')
 a=v.get('external_artifact',{});req(a.get('file_id')=='167VslSePpzwLBIrawKJ6XC5tmWtop8rv' and a.get('size_bytes')==1683479 and a.get('sha256')=='eb1ae33c89e8c1afe6e8ea2afabe85e611a4ff5ef63f8c4a42652924c757a087','ARTIFACT')
 req(v.get('qa_recommendation')=='PASS_WITH_MATERIAL_FINDINGS','QA')
 for k,e in {'cluster_semantic_promotion':'DENIED','selector_change':'DENIED','c2e_c2_5_c3':'DENIED','validation_consumption':'DENIED','r2_publication':'DENIED','probability_risk_exposure_execution':'NONE'}.items():req(v.get(k)==e,f'AUTHORITY:{k}')
 return {'status':'PASS','occurrences':1779,'primary_clusters':20,'sensitivity_counts':v['sensitivity_counts'],'findings':sorted(x['finding_id'] for x in v['findings'])}
