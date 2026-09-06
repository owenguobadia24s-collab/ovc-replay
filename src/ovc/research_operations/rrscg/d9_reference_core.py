from __future__ import annotations
import math

R2_VIEWS=("C_LAST_EXACT","C_LAST_HI","C_LAST_MID","CARRIER_BAG_HI","CARRIER_BAG_MID")

class D9Error(ValueError): pass

def normalize_rational(o):
    n=int(o["numerator"]);d=int(o["denominator"])
    if d<=0: raise D9Error("RATIONAL_DENOMINATOR")
    g=math.gcd(n,d);return {"numerator":n//g,"denominator":d//g}

def rational(n,d): return normalize_rational({"numerator":n,"denominator":d})

def val_rat(n,d): return {"status":"VALUE","value":rational(n,d)}

def na_rat(x): return {"status":"NOT_EVALUABLE","reason_code":x}

def val_int(x): return {"status":"VALUE","value":int(x)}

def na_int(x): return {"status":"NOT_EVALUABLE","reason_code":x}

def eval_set(xs): return {"status":"EVALUABLE","target_ids":sorted(set(xs))}

def na_set(x): return {"status":"NOT_EVALUABLE","reason_code":x}

def _derive_view(raw,support_min,relation_min):
    vid=raw["view_id"];src=raw["source_evaluable"];comp=raw["comparable"];sup=raw["antecedent_support_count"]
    if not src:return {"view_id":vid,"view_status":"NOT_EVALUABLE_REQUIRED_FIELD","source_evaluable":False,"comparable":False,"antecedent_support_count":0,"antecedent_supported":False,"relation_bearing":False,"qualified_frontier_target_ids":[],"relation_support_records":[]}
    if not comp:return {"view_id":vid,"view_status":"NOT_COMPARABLE","source_evaluable":True,"comparable":False,"antecedent_support_count":0,"antecedent_supported":False,"relation_bearing":False,"qualified_frontier_target_ids":[],"relation_support_records":[]}
    if sup<support_min:return {"view_id":vid,"view_status":"EVALUABLE_BELOW_ANTECEDENT_SUPPORT","source_evaluable":True,"comparable":True,"antecedent_support_count":sup,"antecedent_supported":False,"relation_bearing":False,"qualified_frontier_target_ids":[],"relation_support_records":[]}
    rels={x["target_id"]:x["support_count"] for x in raw["relation_support_records"]};q=sorted(y for y,n in rels.items() if n>=relation_min)
    return {"view_id":vid,"view_status":"EVALUABLE_RELATION_BEARING" if q else "EVALUABLE_NO_QUALIFIED_RELATION","source_evaluable":True,"comparable":True,"antecedent_support_count":sup,"antecedent_supported":True,"relation_bearing":bool(q),"qualified_frontier_target_ids":q,"relation_support_records":[{"target_id":y,"support_count":rels[y]} for y in sorted(rels)]}

def _build_state(namespace,raw_views,support_min,relation_min,parent_payload):
    by={x["view_id"]:x for x in raw_views};views=[_derive_view(by[v],support_min,relation_min) for v in R2_VIEWS];src=[v for v in views if v["source_evaluable"]];comp=[v for v in views if v["comparable"]];sup=[v for v in views if v["antecedent_supported"]];rel=[v for v in views if v["relation_bearing"]];Eset=set().union(*[set(v["qualified_frontier_target_ids"]) for v in views]);E=eval_set(Eset)
    if len(sup)==len(R2_VIEWS):sets=[set(v["qualified_frontier_target_ids"]) for v in views];Kset=set.intersection(*sets);K=eval_set(Kset);core=True
    else:Kset=None;K=na_set("FULL_CORE_INCOMPLETE_VIEW_SUPPORT");core=False
    A=eval_set(Eset-Kset) if core else na_set("FULL_CORE_NOT_EVALUABLE");Q=eval_set(parent_payload["selected_frontier_target_ids"]);qstate="RESOLVED_NONEMPTY" if parent_payload["relation_resolved"] else "ABSTAIN_NO_CONSTRAINT";tier=parent_payload["selected_resolution_tier"];full=parent_payload["full_consensus_state"]
    if not set(Q["target_ids"]).issubset(Eset):raise D9Error("PARENT_Q_OUTSIDE_ENVELOPE")
    srecords=[]
    for y in sorted(Eset):
        ids=sorted(v["view_id"] for v in views if y in v["qualified_frontier_target_ids"]);c=len(ids);srecords.append({"target_id":y,"supporting_view_ids":ids,"supporting_view_count":c,"declared_view_fraction":rational(c,len(R2_VIEWS)),"antecedent_supported_view_fraction":val_rat(c,len(sup)) if sup else na_rat("ZERO_ANTECEDENT_SUPPORTED_VIEWS")})
    coherence=val_rat(len(Kset),len(Eset)) if core and Eset else na_rat("EMPTY_ENVELOPE_OR_FULL_CORE_NOT_EVALUABLE")
    return {"constraint_shape_semantic_namespace_id":namespace,"declared_view_ids":sorted(R2_VIEWS),"K":K,"E":E,"A":A,"Q":Q,"q_state":qstate,"resolution_tier":tier,"full_consensus_state":full,"view_evidence_records":sorted(views,key=lambda x:x["view_id"]),"representation_support_records":srecords,"declared_view_count":len(R2_VIEWS),"source_evaluable_view_count":len(src),"comparable_view_count":len(comp),"antecedent_supported_view_count":len(sup),"relation_bearing_view_count":len(rel),"full_core_evaluable":core,"coherence":coherence}

def _view_sets(s):return ({v["view_id"] for v in s["view_evidence_records"] if v["source_evaluable"]},{v["view_id"] for v in s["view_evidence_records"] if v["comparable"]},{v["view_id"] for v in s["view_evidence_records"] if v["antecedent_supported"]},{v["view_id"] for v in s["view_evidence_records"] if v["relation_bearing"]})

def _trans(p,c):
    g=set(c)-set(p);l=set(p)-set(c)
    return "UNCHANGED" if not g and not l else "GAIN_ONLY" if g and not l else "LOSS_ONLY" if l and not g else "MIXED_CHANGE"

def _gb(p,c):
    d=set(R2_VIEWS);p=set(p);c=set(c)
    if not p and not c:return "NO_SUPPORTED_VIEW_BASIS",set()
    if p==c==d:return "FULL_DECLARED_VIEW_BASIS",d
    if p==c:return "FIXED_PARTIAL_SUPPORTED_VIEW_BASIS",p
    z=p&c
    return ("COMMON_SUPPORTED_VIEW_BASIS",z) if z else ("NO_COMMON_SUPPORTED_VIEW_BASIS",set())

def _front(s,b):
    if not b:return None,None,None
    by={v["view_id"]:set(v["qualified_frontier_target_ids"]) for v in s["view_evidence_records"]};E=set().union(*[by[v] for v in b]);K=set.intersection(*[by[v] for v in b]);return E,K,E-K

def _jac(a,b):
    u=set(a)|set(b);return val_rat(0,1) if not u else val_rat(len(u)-len(set(a)&set(b)),len(u))

def _ratsub(a,b):
    if a["status"]!="VALUE" or b["status"]!="VALUE":return na_rat("COHERENCE_NOT_EVALUABLE")
    x=a["value"];y=b["value"];return val_rat(x["numerator"]*y["denominator"]-y["numerator"]*x["denominator"],x["denominator"]*y["denominator"])

def _dc(a,b,ids):
    if not ids:return na_rat("ZERO_VIEW_BASIS")
    def counts(s):
        by={v["view_id"]:set(v["qualified_frontier_target_ids"]) for v in s["view_evidence_records"]};ys=set().union(*[by[v] for v in ids]);return {y:sum(y in by[v] for v in ids) for y in ys}
    p=counts(a);c=counts(b);ys=set(p)|set(c);return val_rat(0,1) if not ys else val_rat(sum(abs(c.get(y,0)-p.get(y,0)) for y in ys),len(ids)*len(ys))

def _build_motion(ns,a,b):
    ps,pc,pp,pr=_view_sets(a);cs,cc,cp,cr=_view_sets(b);gs,basis=_gb(pp,cp);pE,pK,pA=_front(a,basis);cE,cK,cA=_front(b,basis)
    if basis:dWE=val_int(len(cE)-len(pE));dWK=val_int(len(cK)-len(pK));dWA=val_int(len(cA)-len(pA));DE=_jac(pE,cE);DK=_jac(pK,cK);pco=val_rat(len(pK),len(pE)) if pE else na_rat("EMPTY_BASIS_ENVELOPE");cco=val_rat(len(cK),len(cE)) if cE else na_rat("EMPTY_BASIS_ENVELOPE");cd=_ratsub(cco,pco);dcc=_dc(a,b,basis)
    else:dWE=dWK=dWA=na_int("NO_GEOMETRY_VIEW_BASIS");DE=DK=na_rat("NO_GEOMETRY_VIEW_BASIS");cd=dcc=na_rat("NO_GEOMETRY_VIEW_BASIS")
    pQ=set(a["Q"]["target_ids"]);cQ=set(b["Q"]["target_ids"]);dWQ=val_int(len(cQ)-len(pQ));DQ=_jac(pQ,cQ);qt={('RESOLVED_NONEMPTY','RESOLVED_NONEMPTY'):'RESOLVED_TO_RESOLVED',('RESOLVED_NONEMPTY','ABSTAIN_NO_CONSTRAINT'):'RESOLVED_TO_ABSTAIN',('ABSTAIN_NO_CONSTRAINT','RESOLVED_NONEMPTY'):'ABSTAIN_TO_RESOLVED',('ABSTAIN_NO_CONSTRAINT','ABSTAIN_NO_CONSTRAINT'):'ABSTAIN_TO_ABSTAIN'}[(a["q_state"],b["q_state"])];labels=[]
    if dWE["status"]=="VALUE":labels+=['ENVELOPE_TIGHTENING'] if dWE["value"]<0 else ['ENVELOPE_BROADENING'] if dWE["value"]>0 else ['ENVELOPE_TRANSLATION'] if DE["value"]["numerator"] else []
    if qt=='RESOLVED_TO_ABSTAIN':labels.append('ABSTENTION_ENTRY')
    if qt=='ABSTAIN_TO_RESOLVED':labels.append('ABSTENTION_EXIT')
    return {"constraint_shape_semantic_namespace_id":ns,"geometry_basis_status":gs,"source_evaluability_transition_status":_trans(ps,cs),"comparability_transition_status":_trans(pc,cc),"support_basis_transition_status":_trans(pp,cp),"relation_basis_transition_status":_trans(pr,cr),"q_transition_status":qt,"source_evaluable_view_ids_prev":sorted(ps),"source_evaluable_view_ids_t":sorted(cs),"comparable_view_ids_prev":sorted(pc),"comparable_view_ids_t":sorted(cc),"antecedent_supported_view_ids_prev":sorted(pp),"antecedent_supported_view_ids_t":sorted(cp),"relation_bearing_view_ids_prev":sorted(pr),"relation_bearing_view_ids_t":sorted(cr),"geometry_view_basis_ids":sorted(basis),"delta_W_E":dWE,"delta_W_K":dWK,"delta_W_A":dWA,"delta_W_Q":dWQ,"D_E":DE,"D_K":DK,"D_Q":DQ,"D_c_declared":_dc(a,b,set(R2_VIEWS)),"D_c_common":dcc,"coherence_delta":cd,"R_prev":a["resolution_tier"],"R_t":b["resolution_tier"],"primitive_motion_labels":sorted(set(labels))}
