from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.opt_b.esl.c3_reference import (
    C3BridgeError,
    C3BridgeMaturity,
    C3ExplanationRecord,
    proposition_from_occurrence,
    render_normative_reference_trace,
    render_reference_statement,
    require_reference_maturity,
    statement_ast_from_occurrence,
)
from ovc.opt_b.esl.compiler import compile_structural_occurrence

ROOT = Path(__file__).resolve().parents[3]
WP2 = ROOT / "fixtures" / "opt_b" / "esl" / "wp2" / "normative_traces.json"
WP3 = ROOT / "fixtures" / "opt_b" / "esl" / "wp3" / "bootstrap_c2_input.json"


def _record():
    source = json.loads(WP3.read_text(encoding="utf-8"))
    return compile_structural_occurrence(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"])


def test_all_five_ratified_normative_renderings_are_reproduced():
    traces = json.loads(WP2.read_text(encoding="utf-8"))["traces"]
    for trace in traces:
        assert render_normative_reference_trace(trace["trace_id"], trace["payload"]) == trace["canonical_rendering"]


def test_base_vertical_reference_path_is_deterministic_and_source_immutable():
    record = _record(); before = copy.deepcopy(record); proposition = proposition_from_occurrence(record); ast = statement_ast_from_occurrence(record, proposition); text1, trace1 = render_reference_statement(record, proposition, ast); text2, trace2 = render_reference_statement(record, proposition, ast)
    assert record == before
    assert proposition.authority_state == ast.authority_state == trace1.authority_state == "INACTIVE_REFERENCE"
    assert (text1, trace1) == (text2, trace2)
    assert proposition.source_refs == (record.occurrence_record_id,)
    assert trace1.selected_proposition_refs == (proposition.proposition_id,)
    assert trace1.deterministic_bytes is True


def test_family_organisation_constraint_are_optional_and_do_not_invalidate_base_statement():
    record=_record(); proposition=proposition_from_occurrence(record); ast=statement_ast_from_occurrence(record,proposition); decisions={item.clause_type:item for item in ast.optional_clauses}
    assert decisions["FAMILY_CONTEXT"].decision == "OMIT"
    assert decisions["ORGANISATION_EVIDENCE"].decision == "OMIT"
    assert decisions["CONSTRAINT_EVIDENCE"].decision == "OMIT"
    text,trace=render_reference_statement(record,proposition,ast); assert text.startswith("Occurrence "); assert "OPTIONAL_FAMILY_CONTEXT_NOT_REQUIRED" in trace.omission_reasons


def test_shadow_and_production_maturity_fail_closed_without_activation_record():
    for maturity in (C3BridgeMaturity.SHADOW_EVALUATION,C3BridgeMaturity.PRODUCTION_GRAMMAR):
        with pytest.raises(C3BridgeError,match="C3_BRIDGE_ACTIVATION_RECORD_MISSING"): require_reference_maturity(maturity)
    with pytest.raises(C3BridgeError,match="C3_BRIDGE_ACTIVATION_FORBIDDEN_IN_ESLI"): require_reference_maturity(C3BridgeMaturity.INACTIVE_REFERENCE,activation_state="ACTIVE")


def test_activation_registry_is_empty_and_maturity_registry_is_reference_only():
    activation=json.loads((ROOT/"registries/opt_b/esl/C3_VOCABULARY_ACTIVATION_v0_1.json").read_text(encoding="utf-8")); maturity=json.loads((ROOT/"registries/opt_b/esl/C3_BRIDGE_MATURITY_v0_1.json").read_text(encoding="utf-8")); assert activation["activation_state"]=="NONE" and activation["bindings"]==[]; assert maturity["current_maturity"]=="INACTIVE_REFERENCE"; assert maturity["esli_reachable"]==["INACTIVE_REFERENCE"]


def test_llm_explanation_is_separate_noncanonical_sidecar():
    record=_record(); proposition=proposition_from_occurrence(record); ast=statement_ast_from_occurrence(record,proposition); explanation=C3ExplanationRecord("EXPL.1",ast.statement_id,{"generator":"fixture"},"Non-authoritative explanation.",(record.occurrence_record_id,),("NONCANONICAL",)); assert explanation.noncanonical is True; assert "generated_text" not in ast.__dict__; assert "explanation" not in repr(ast).lower()
