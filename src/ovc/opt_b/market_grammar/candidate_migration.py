"""CEAR-G10 fourteen-candidate migration and domain ablation.

Inactive, noncanonical SHADOW_EXPERIMENT research only. This module translates the
legacy frequency-conjunction candidate representation into a typed migration ledger.
It does not promote candidates, create canonical grammars, or grant semantic authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Mapping

AUTHORITY_STATE="SHADOW_EXPERIMENT"
DOMAINS=frozenset({"STRUCTURAL","TEMPORAL","OBJECT_BINDING","CONTEXT","COMPUTABILITY","PROVENANCE"})
LAYERS=frozenset({"context","location","condition","episode_phase","event","response","transition","possible_resolution","evidence_gate","diagnostic_only"})
_INDEXED_DEVELOPMENT=re.compile(r"^ordered_development\[(\d+)\]\.([a-z0-9_]+)$")

def _canon(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def _hash(value): return sha256(_canon(value).encode("utf-8")).hexdigest()
def _text(value,field):
    out=str(value).strip()
    if not out: raise ValueError(f"{field} must be non-empty")
    return out

def classify_legacy_feature(feature_key:str)->str:
    """Migration-only domain adapter for the flattened CEAR-G10 feature namespace."""
    key=_text(feature_key,"feature_key").lower()
    if key.startswith("assurance."): return "PROVENANCE"
    if re.match(r"^context_ids\[\d+\]$",key): return "CONTEXT"
    if re.match(r"^object_ids\[\d+\]$",key): return "PROVENANCE"
    if key.startswith("missingness."): return "COMPUTABILITY"
    match=_INDEXED_DEVELOPMENT.match(key)
    if match:
        leaf=match.group(2)
        if leaf in {"availability","quality_state"}: return "COMPUTABILITY"
        if leaf=="position": return "TEMPORAL"
        return "STRUCTURAL"
    if key in {"duration_observations","start_condition.sequence_length"}: return "TEMPORAL"
    if key in {"path_geometry.available_observation_count","start_condition.continuity_segment_available","ending_structural_effect.continuity_state"}: return "COMPUTABILITY"
    if key.endswith(("_sha256","_hash")): return "PROVENANCE"
    return "STRUCTURAL"

def map_typed_layer(feature_key:str,domain:str)->str:
    key=_text(feature_key,"feature_key").lower(); domain=_text(domain,"domain").upper()
    if domain not in DOMAINS: raise ValueError(f"unsupported domain: {domain}")
    if domain=="PROVENANCE": return "diagnostic_only"
    if domain=="COMPUTABILITY": return "evidence_gate"
    if domain=="CONTEXT": return "context"
    if domain=="OBJECT_BINDING": return "condition"
    if key.startswith("ordered_development["): return "episode_phase"
    if key.startswith("ending_structural_effect."): return "possible_resolution"
    if key.startswith("start_condition."): return "condition"
    if "location" in key: return "location"
    return "condition"

def _usage(domain:str)->str:
    return {"STRUCTURAL":"STRUCTURAL_PREDICATE","TEMPORAL":"TEMPORAL_GUARD","OBJECT_BINDING":"OBJECT_BINDING_GUARD","CONTEXT":"CONTEXT_GUARD","COMPUTABILITY":"COMPUTABILITY_GUARD","PROVENANCE":"DIAGNOSTIC_ONLY_PROVENANCE"}[domain]

@dataclass(frozen=True)
class CandidateMigration:
    migration_id:str
    rule_candidate_id:str
    functional_core_id:str
    family_id:str
    migration_status:str
    source_rule_content_sha256:str
    source_clause_inventory_sha256:str
    typed_mapping_sha256:str
    legacy_operator:str
    legacy_clause_count:int
    legacy_component_classification_counts:Mapping[str,int]
    selected_clause_classification_counts:Mapping[str,int]
    domain_counts:Mapping[str,int]
    typed_layer_counts:Mapping[str,int]
    typed_feature_keys_by_domain:Mapping[str,tuple[str,...]]
    typed_feature_keys_by_layer:Mapping[str,tuple[str,...]]
    provenance_ablation:Mapping[str,object]
    frequency_conjunction_comparison:Mapping[str,object]
    evaluation:Mapping[str,object]
    conflict_proof_status:str
    counterexample_status:str
    promotion_authority:str="NONE"
    canonical:bool=False
    authority_state:str=AUTHORITY_STATE

    def to_dict(self):
        return {
            "migration_id":self.migration_id,"rule_candidate_id":self.rule_candidate_id,
            "functional_core_id":self.functional_core_id,"family_id":self.family_id,
            "migration_status":self.migration_status,"source_rule_content_sha256":self.source_rule_content_sha256,
            "source_clause_inventory_sha256":self.source_clause_inventory_sha256,"typed_mapping_sha256":self.typed_mapping_sha256,
            "legacy_operator":self.legacy_operator,"legacy_clause_count":self.legacy_clause_count,
            "legacy_component_classification_counts":dict(self.legacy_component_classification_counts),
            "selected_clause_classification_counts":dict(self.selected_clause_classification_counts),
            "domain_counts":dict(self.domain_counts),"typed_layer_counts":dict(self.typed_layer_counts),
            "typed_feature_keys_by_domain":{k:list(v) for k,v in self.typed_feature_keys_by_domain.items()},
            "typed_feature_keys_by_layer":{k:list(v) for k,v in self.typed_feature_keys_by_layer.items()},
            "provenance_ablation":dict(self.provenance_ablation),
            "frequency_conjunction_comparison":dict(self.frequency_conjunction_comparison),
            "evaluation":dict(self.evaluation),"conflict_proof_status":self.conflict_proof_status,
            "counterexample_status":self.counterexample_status,"promotion_authority":self.promotion_authority,
            "canonical":self.canonical,"authority_state":self.authority_state,
        }

def migrate_candidate(candidate:Mapping[str,object])->CandidateMigration:
    required={"rule_candidate_id","functional_core_id","family_id","source_rule_content_sha256","ast_operator","clauses","functional_core_classification_counts","evaluation"}
    missing=required-set(candidate)
    if missing: raise ValueError("missing candidate fields: "+", ".join(sorted(missing)))
    if _text(candidate["ast_operator"],"ast_operator").upper()!="ALL_OF": raise ValueError("CEAR-G10 migration accepts only frozen ALL_OF source candidates")
    typed=[]; domains={}; layers={}; selected={}; by_domain={}; by_layer={}; seen=set()
    raw_clause_inventory=[]
    for raw in candidate["clauses"]:
        clause=dict(raw); key=_text(clause["feature_key"],"feature_key"); comparison=_text(clause["comparison"],"comparison").upper(); operator=_text(clause["operator"],"operator").upper(); value=_text(clause["value"],"value")
        if operator!="MEASUREMENT_COMPARISON" or comparison!="EQUALS": raise ValueError("unsupported legacy clause operator/comparison")
        identity=(key,comparison,value)
        if identity in seen: raise ValueError("duplicate legacy clause")
        seen.add(identity)
        legacy_class=_text(clause["legacy_classification"],"legacy_classification").upper()
        if legacy_class=="CONTRADICTORY": raise ValueError("selected source clause may not be legacy CONTRADICTORY")
        selected[legacy_class]=selected.get(legacy_class,0)+1
        domain=classify_legacy_feature(key); layer=map_typed_layer(key,domain)
        domains[domain]=domains.get(domain,0)+1; layers[layer]=layers.get(layer,0)+1
        by_domain.setdefault(domain,set()).add(key); by_layer.setdefault(layer,set()).add(key)
        mapped={"feature_key":key,"comparison":comparison,"value":value,"legacy_classification":legacy_class,"domain":domain,"typed_layer":layer,"usage":_usage(domain)}
        typed.append(mapped)
        raw_clause_inventory.append({"feature_key":key,"comparison":comparison,"value":value,"legacy_classification":legacy_class,"legacy_count":int(clause["legacy_count"]),"legacy_frequency":str(clause["legacy_frequency"])})
    typed.sort(key=lambda x:(x["typed_layer"],x["feature_key"],x["value"]))
    raw_clause_inventory.sort(key=lambda x:(x["feature_key"],x["value"]))
    structural=[x for x in typed if x["domain"] in {"STRUCTURAL","TEMPORAL","OBJECT_BINDING","CONTEXT"}]
    provenance=[x for x in typed if x["domain"]=="PROVENANCE"]; computability=[x for x in typed if x["domain"]=="COMPUTABILITY"]
    status="MAPPED" if structural else "UNRESOLVED"
    source_clause_hash=_hash(raw_clause_inventory); mapping_hash=_hash(typed)
    source_hash=_text(candidate["source_rule_content_sha256"],"source_rule_content_sha256").lower()
    eval_record=dict(candidate["evaluation"]); counterexamples=int(eval_record.get("counterexample_count",0))
    identity_payload={"rule_candidate_id":candidate["rule_candidate_id"],"functional_core_id":candidate["functional_core_id"],"family_id":candidate["family_id"],"source_rule_content_sha256":source_hash,"source_clause_inventory_sha256":source_clause_hash,"typed_mapping_sha256":mapping_hash,"migration_status":status}
    return CandidateMigration(
        migration_id="MG.CEAR_G10.MIGRATION."+_hash(identity_payload)[:24],
        rule_candidate_id=_text(candidate["rule_candidate_id"],"rule_candidate_id"),
        functional_core_id=_text(candidate["functional_core_id"],"functional_core_id"),
        family_id=_text(candidate["family_id"],"family_id"),migration_status=status,
        source_rule_content_sha256=source_hash,source_clause_inventory_sha256=source_clause_hash,typed_mapping_sha256=mapping_hash,
        legacy_operator="ALL_OF",legacy_clause_count=len(typed),
        legacy_component_classification_counts=MappingProxyType(dict(sorted((str(k),int(v)) for k,v in dict(candidate["functional_core_classification_counts"]).items()))),
        selected_clause_classification_counts=MappingProxyType(dict(sorted(selected.items()))),
        domain_counts=MappingProxyType(dict(sorted(domains.items()))),typed_layer_counts=MappingProxyType(dict(sorted(layers.items()))),
        typed_feature_keys_by_domain=MappingProxyType({k:tuple(sorted(v)) for k,v in sorted(by_domain.items())}),
        typed_feature_keys_by_layer=MappingProxyType({k:tuple(sorted(v)) for k,v in sorted(by_layer.items())}),
        provenance_ablation=MappingProxyType({"legacy_clause_count":len(typed),"provenance_clause_count":len(provenance),"computability_guard_count":len(computability),"typed_structural_context_temporal_clause_count":len(structural),"provenance_excluded_from_structural_grammar":True,"ablation_scope":"CLAUSE_DOMAIN_SEPARATION_ONLY","empirical_match_set_recomputed":False}),
        frequency_conjunction_comparison=MappingProxyType({"legacy_form":"ALL_OF_MEASUREMENT_COMPARISONS","typed_form":"DOMAIN_SEPARATED_TYPED_PREDICATE_INVENTORY","legacy_identity_conditioning_present":bool(provenance),"typed_structural_grammar_excludes_provenance":True,"exact_empirical_parity":"NOT_EVALUATED_IN_WP7","reason":"REMOVING_NONSTRUCTURAL_CONJUNCTS_CAN_CHANGE_MATCH_SET;_WP7_DOES_NOT_PROMOTE_OR_REPLAY_A_NEW_GRAMMAR"}),
        evaluation=MappingProxyType(dict(sorted(eval_record.items()))),
        conflict_proof_status="NOT_PROVEN_NO_MATCHING_FROZEN_EXCLUSIVITY_RULE",
        counterexample_status="PRESENT_SOURCE_HASH_BOUND" if counterexamples>0 else "NONE_RECORDED",
    )

def build_migration_artifacts(input_payload:Mapping[str,object]):
    if input_payload.get("candidate_count")!=14: raise ValueError("exactly fourteen CEAR-G10 candidates are required")
    raw=list(input_payload.get("candidates",[]))
    if len(raw)!=14: raise ValueError("candidate inventory length must equal fourteen")
    migrations=sorted((migrate_candidate(x) for x in raw),key=lambda x:x.rule_candidate_id)
    if len({x.rule_candidate_id for x in migrations})!=14: raise ValueError("candidate IDs must be unique")
    if any(x.promotion_authority!="NONE" or x.canonical for x in migrations): raise ValueError("migration may not promote candidates")
    status={}; domain_totals={}; selected_totals={}; legacy_totals={}
    for item in migrations:
        status[item.migration_status]=status.get(item.migration_status,0)+1
        for k,v in item.domain_counts.items(): domain_totals[k]=domain_totals.get(k,0)+int(v)
        for k,v in item.selected_clause_classification_counts.items(): selected_totals[k]=selected_totals.get(k,0)+int(v)
        for k,v in item.legacy_component_classification_counts.items(): legacy_totals[k]=legacy_totals.get(k,0)+int(v)
    # Deduplicate the repeated legacy feature namespace into one compact typed dictionary.
    feature_keys=sorted({key for item in migrations for values in item.typed_feature_keys_by_domain.values() for key in values})
    feature_index={key:index for index,key in enumerate(feature_keys)}
    feature_dictionary={}
    for key in feature_keys:
        domain=classify_legacy_feature(key); layer=map_typed_layer(key,domain)
        feature_dictionary[key]=[domain,layer,_usage(domain)]
    compact=[]
    for item in migrations:
        evaluation=dict(item.evaluation)
        compact_eval={
            "population_id":evaluation.get("population_id"),"matched_count":evaluation.get("matched_count"),
            "match_set_sha256":evaluation.get("match_set_sha256"),"counterexample_count":evaluation.get("counterexample_count"),
            "counterexample_set_sha256":evaluation.get("counterexample_set_sha256"),
            "independent_recurrence_observed":evaluation.get("independent_recurrence_observed"),
        }
        compact.append({
            "migration_id":item.migration_id,"rule_candidate_id":item.rule_candidate_id,"functional_core_id":item.functional_core_id,
            "family_id":item.family_id,"migration_status":item.migration_status,"source_rule_content_sha256":item.source_rule_content_sha256,
            "source_clause_inventory_sha256":item.source_clause_inventory_sha256,"typed_mapping_sha256":item.typed_mapping_sha256,
            "legacy_clause_count":item.legacy_clause_count,"legacy_component_classification_counts":dict(item.legacy_component_classification_counts),
            "selected_clause_classification_counts":dict(item.selected_clause_classification_counts),"domain_counts":dict(item.domain_counts),
            "typed_layer_counts":dict(item.typed_layer_counts),"typed_feature_indices_by_domain":{k:[feature_index[x] for x in v] for k,v in sorted(item.typed_feature_keys_by_domain.items())},
            "evaluation":compact_eval,
        })
    payload={
        "schema":"ovc-mg-cear-g10-migration-ledger/v1","programme_id":"OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1",
        "packet_id":"MG-WP7","authority":"INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
        "candidate_count":len(migrations),"migration_status_counts":dict(sorted(status.items())),"domain_totals":dict(sorted(domain_totals.items())),
        "selected_clause_classification_totals":dict(sorted(selected_totals.items())),"legacy_core_classification_totals":dict(sorted(legacy_totals.items())),
        "source_artifacts":dict(input_payload.get("source_artifacts",{})),"feature_dictionary_format":["domain","typed_layer","usage"],
        "feature_dictionary":feature_dictionary,"migrations":compact,
        "migration_policy":{"legacy_operator":"ALL_OF","legacy_form":"ALL_OF_MEASUREMENT_COMPARISONS","typed_form":"DOMAIN_SEPARATED_TYPED_PREDICATE_INVENTORY","provenance_structural_usage":"DIAGNOSTIC_ONLY_PROVENANCE","computability_usage":"COMPUTABILITY_GUARD","exact_empirical_parity":"NOT_EVALUATED_IN_WP7","logical_conflict_requirement":"MATCHING_FROZEN_EXCLUSIVITY_RULE_SAME_OBJECT_CLOCK_FIRST_VALID_SCOPE","candidate_authority_state":"SHADOW_EXPERIMENT","candidate_canonical":False,"candidate_promotion_authority":"NONE","counterexamples":"SOURCE_HASH_BOUND"},
        "canonical":False,"promotion_authority":"NONE"
    }
    feature_registry={"schema":"ovc-mg-cear-g10-feature-migration-registry/v1","programme_id":"OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1","packet_id":"MG-WP7","authority":"SHADOW_EXPERIMENT","feature_dictionary_format":payload.pop("feature_dictionary_format"),"feature_dictionary":payload.pop("feature_dictionary"),"canonical":False,"promotion_authority":"NONE"}
    feature_registry["registry_sha256"]=_hash(feature_registry)
    candidate_records=payload.pop("migrations")
    migration_records=[]
    for record in candidate_records:
        record_sha256=_hash(record)
        migration_records.append({"rule_candidate_id":record["rule_candidate_id"],"migration_id":record["migration_id"],"record_sha256":record_sha256,"path":"registries/opt_b/market_grammar/cear_g10_migrations/"+record["rule_candidate_id"].replace(".","_")+".json"})
    payload["migration_records"]=migration_records
    payload["feature_registry_id"]="MG.CEAR_G10.TYPED_FEATURE_MIGRATION.v0.1"
    payload["feature_registry_sha256"]=feature_registry["registry_sha256"]
    payload["ledger_sha256"]=_hash(payload)
    return payload,feature_registry,candidate_records

def build_migration_ledger(input_payload:Mapping[str,object]):
    return build_migration_artifacts(input_payload)[0]

def build_feature_migration_registry(input_payload:Mapping[str,object]):
    return build_migration_artifacts(input_payload)[1]

def build_input_from_sources(rule_candidates:list[Mapping[str,object]],functional_core_document:Mapping[str,object],disposition_document:Mapping[str,object],source_artifacts:Mapping[str,object]):
    """Join the three frozen CEAR-G10 source artifacts into the compact migration input."""
    cores={x["functional_core_id"]:x for x in functional_core_document["functional_cores"]}
    dispositions={x["rule_candidate_id"]:x for x in disposition_document["rule_candidates"]}
    candidates=[]
    for rule in sorted(rule_candidates,key=lambda x:x["rule_candidate_id"]):
        core=cores[rule["functional_core_id"]]; disp=dispositions[rule["rule_candidate_id"]]
        component_index={(x["feature_key"],str(x["feature_value"])):x for x in core["component_matrix"]}
        clauses=[]
        for clause in rule["ast"]["clauses"]:
            component=component_index.get((clause["feature_key"],str(clause["value"])))
            if component is None: raise ValueError("source rule clause missing from functional-core component matrix")
            clauses.append({"operator":clause["operator"],"comparison":clause["comparison"],"feature_key":clause["feature_key"],"value":str(clause["value"]),"legacy_classification":component["classification"],"legacy_count":component["count"],"legacy_frequency":component["frequency"]})
        candidates.append({"rule_candidate_id":rule["rule_candidate_id"],"functional_core_id":rule["functional_core_id"],"family_id":rule["family_id"],"source_rule_content_sha256":rule["content_sha256"],"ast_operator":rule["ast"]["operator"],"clauses":clauses,"functional_core_classification_counts":core["classification_counts"],"evaluation":{"population_id":disp["evaluation_population_id"],"result_count":disp["evaluation_result_count"],"outcome_counts":disp["evaluation_outcome_counts"],"matched_count":disp["matched_count"],"match_set_sha256":disp["match_set_sha256"],"counterexample_count":disp["counterexample_count"],"counterexample_set_sha256":disp["counterexample_set_sha256"],"matched_controls":disp["matched_controls"],"independent_recurrence_observed":disp["independent_recurrence_observed"]}})
    return {"schema":"ovc-mg-wp7-candidate-migration-input/v1","programme_id":"OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1","packet_id":"MG-WP7","authority":"INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_INPUT_ONLY","source_artifacts":dict(source_artifacts),"candidate_count":len(candidates),"candidates":candidates}
