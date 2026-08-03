#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / ".github/workflows"
REG = ROOT / "registries/development/v0_2/OVC_DA2_WORKFLOW_ADMISSION_MODES_v0_1.json"
GATE = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_GATE_PACKET.json"
QA = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_QA_PACKET.json"
DECISION = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_OPERATOR_DECISION.json"
RULESET = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_RULESET_MIGRATION_PACKET.json"
CANONICAL = {".github/workflows/tests.yml",".github/workflows/ovc-tiered-tests.yml"}
FULL_SUITE = "python3 -m unittest discover -s tests -v"
def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def main() -> int:
    registry=load(REG); gate=load(GATE); qa=load(QA); decision=load(DECISION); ruleset=load(RULESET)
    modes=registry["modes"]
    canonical_paths=set(modes["CANONICAL_PULL_REQUEST"]); manual_paths=set(modes["RETIRED_NON_AUTHORITATIVE_MANUAL_VERIFICATION"]); push_paths=set(modes["PUSH_AND_MANUAL_PRESERVED"])
    assert len(canonical_paths)==2 and len(manual_paths)==71 and len(push_paths)==3 and canonical_paths==CANONICAL
    registered_paths=canonical_paths|manual_paths|push_paths
    assert len(registered_paths)==76
    actual={f".github/workflows/{p.name}":p for p in WF.glob("*.yml")}
    missing=sorted(registered_paths-set(actual)); assert not missing, f"registered workflows missing: {missing}"
    pr_paths=set(); complete_suite_pr_paths=set()
    for path,file in actual.items():
        text=file.read_text(encoding="utf-8"); has_pr="\n  pull_request:" in text or text.startswith("on:\n  pull_request:")
        if has_pr:
            pr_paths.add(path); assert "concurrency:" in text and "cancel-in-progress: true" in text
            if FULL_SUITE in text: complete_suite_pr_paths.add(path)
    assert pr_paths==CANONICAL and complete_suite_pr_paths=={".github/workflows/tests.yml"}
    tests=actual[".github/workflows/tests.yml"].read_text(); tiered=actual[".github/workflows/ovc-tiered-tests.yml"].read_text()
    assert tests.count(FULL_SUITE)==1 and 'python-version: "3.11"' in tests
    assert "OVC merge readiness" in tiered and "OVC tiered test selection shadow" in tiered and "FINAL_HEAD profile without duplicate complete suite" in tiered and FULL_SUITE not in tiered and 'python-version: "3.11"' in tiered and "actions/github-script@v7" in tiered and "run.name === 'tests'" in tiered
    for path in registered_paths:
        text=actual[path].read_text(); assert "concurrency:" in text and "cancel-in-progress: true" in text
        if path in manual_paths:
            assert "pull_request:" not in text and "workflow_dispatch:" in text and "Historical definition:" in text and "Provider, R2, publication, selector, Validation, risk, exposure and execution actions are not performed." in text
        elif path in push_paths:
            assert "pull_request:" not in text and "push:" in text and "workflow_dispatch:" in text
    assert decision["decision"]=="PASS" and decision["approved_delta"]=="BOUNDED_GITHUB_ACTIONS_ORCHESTRATION_TRIGGER_AND_REQUIRED_CONTEXT_RECONFIGURATION_ONLY"
    assert gate["workflow_mutation_active"] is True and gate["ruleset_mutation_active"] is False
    assert qa["qa_recommendation"]=="PENDING_FINAL_HEAD_CI_AND_RULESET_APPLICATION"
    assert ruleset["current_required_contexts"]==["tests","OVC tiered test selection shadow"] and ruleset["target_required_contexts"]==["OVC merge readiness"] and ruleset["accepted_source"]=={"app_id":15368,"app_slug":"github-actions"} and ruleset["connector_capability"]=="RULESET_WRITE_ENDPOINT_NOT_EXPOSED"
    material="\n".join([REG.read_text(),GATE.read_text(),QA.read_text(),DECISION.read_text(),RULESET.read_text()])
    for token in ("ghp_","github_pat_","-----BEGIN PRIVATE KEY-----","sk-proj_","Bearer "): assert token not in material
    print("DA2-G1 orchestration validation PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
