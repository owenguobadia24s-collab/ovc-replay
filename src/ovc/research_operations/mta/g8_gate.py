from __future__ import annotations
from typing import Any, Mapping

GATES=("MTA-G8-CLOCK","MTA-G8-C2E","MTA-G8-C2.5","MTA-G8-C3")
ALLOWED={"PASS","DEFER","BLOCK","QUARANTINE","SUPERSEDE"}
class MTAG8GateError(ValueError): pass
def _require(condition:bool, marker:str)->None:
    if not condition: raise MTAG8GateError(marker)
def validate_packet(packet:Mapping[str,Any])->dict[str,Any]:
    _require(packet.get("schema")=="ovc-mta-g8-consolidated-operator-decision-packet/v1","SCHEMA_MISMATCH")
    _require((packet.get("programme_id"),packet.get("gate_id"),packet.get("status"))==("OVC-MTA-v0.2","MTA-G8","GATE_READY"),"IDENTITY_MISMATCH")
    _require(packet.get("operator_decision_required") is True,"OPERATOR_GATE_MISSING")
    decisions=packet.get("decisions")
    _require(isinstance(decisions,Mapping) and tuple(decisions)==GATES,"DECISION_SET_OR_ORDER_MISMATCH")
    expected={"MTA-G8-CLOCK":"PASS","MTA-G8-C2E":"PASS","MTA-G8-C2.5":"PASS","MTA-G8-C3":"DEFER"}
    _require(packet.get("recommended_consolidated_decision")==expected,"RECOMMENDATION_MISMATCH")
    for gate in GATES:
        item=decisions[gate]
        _require(set(item.get("allowed_decisions",()))==ALLOWED,f"ALLOWED_DECISIONS_MISMATCH:{gate}")
        _require(item.get("recorded_decision") is None,f"PREMATURE_DECISION:{gate}")
        _require(item.get("recommended_decision")==expected[gate],f"DOMAIN_RECOMMENDATION_MISMATCH:{gate}")
    c25=decisions["MTA-G8-C2.5"]
    _require(c25.get("bounded_rule_set")==["BOUNDARY_ZONE_ENTRY","BREACH_ACTIVE","LONG_PERSISTENCE","REPEATED_SWITCHING"],"C2_5_BOUNDED_SET_MISMATCH")
    _require(c25.get("excluded_rules")=={"RETURN_INSIDE":"DEFER_ZERO_FIRES","COMPRESSION_TO_DISPLACEMENT":"DEFER_ZERO_FIRES","LOCAL_PARENT_CONFLICT":"BLOCK_NOT_EVALUABLE","ALIGNMENT_GAINED":"BLOCK_NOT_EVALUABLE"},"C2_5_EXCLUSION_MISMATCH")
    c3=decisions["MTA-G8-C3"]["evidence"]
    _require(c3=={"complete_c2_quality_states":0,"active_parent_range_target_states":0,"robust_occurrences":0,"ro4_comparison":"NOT_DETERMINABLE"},"C3_EVIDENCE_MISMATCH")
    _require(len(packet.get("external_artifacts",()))==5,"EXTERNAL_ARTIFACT_SET_MISMATCH")
    _require(all(item.get("result")=="PASS" for item in packet.get("tests",())),"TEST_EVIDENCE_NOT_PASS")
    denied=packet.get("authority_boundary",{})
    for key,value in denied.items(): _require(value in {"DENIED","NONE"},f"AUTHORITY_ESCAPE:{key}")
    _require(packet.get("exact_operator_command")=="OVC APPROVE MTA-G8 CLOCK=PASS C2E=PASS C2.5=PASS C3=DEFER","OPERATOR_COMMAND_MISMATCH")
    return {"status":"PASS","gate":"MTA-G8","decisions":expected,"operator_required":True}
