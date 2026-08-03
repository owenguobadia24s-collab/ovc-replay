#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
WF=ROOT/'.github/workflows'
REG=ROOT/'registries/development/v0_2/OVC_DA2_WORKFLOW_ADMISSION_MODES_v0_1.json'
GATE=ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_GATE_PACKET.json'
QA=ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_QA_PACKET.json'
DECISION=ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_OPERATOR_DECISION.json'
RULESET=ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_RULESET_MIGRATION_PACKET.json'
CANONICAL={'.github/workflows/tests.yml','.github/workflows/ovc-tiered-tests.yml'}
FULL='python3 -m unittest discover -s tests -v'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 r=load(REG); g=load(GATE); q=load(QA); d=load(DECISION); rs=load(RULESET)
 assert set(r['canonical_pull_request_workflows'])==CANONICAL
 actual={f'.github/workflows/{p.name}':p for p in WF.glob('*.yml')}
 assert CANONICAL.issubset(actual)
 pr=set(); full=set(); missing_concurrency=[]
 for path,p in actual.items():
  text=p.read_text(encoding='utf-8'); has='\n  pull_request:' in text or text.startswith('on:\n  pull_request:')
  if has:
   pr.add(path)
   if 'concurrency:' not in text or 'cancel-in-progress: true' not in text: missing_concurrency.append(path)
   if FULL in text: full.add(path)
 unexpected=sorted(pr-CANONICAL)
 assert not unexpected, f'unexpected pull_request workflows ({len(unexpected)}): {unexpected}'
 assert not missing_concurrency, f'pull_request workflows missing concurrency ({len(missing_concurrency)}): {sorted(missing_concurrency)}'
 assert full=={'.github/workflows/tests.yml'}, f'complete-suite PR workflows: {sorted(full)}'
 tests=actual['.github/workflows/tests.yml'].read_text(); tiered=actual['.github/workflows/ovc-tiered-tests.yml'].read_text()
 assert tests.count(FULL)==1 and 'python-version: "3.11"' in tests
 assert FULL not in tiered and 'python-version: "3.11"' in tiered and 'OVC merge readiness' in tiered and 'OVC tiered test selection shadow' in tiered and "run.name === 'tests'" in tiered
 for path in r['push_manual_preserved_workflows']:
  text=actual[path].read_text(); assert 'pull_request:' not in text and 'push:' in text and 'workflow_dispatch:' in text and 'concurrency:' in text and 'cancel-in-progress: true' in text, path
 assert d['decision']=='PASS'
 assert g['status']=='GATE_READY_AFTER_DA2_G0_MERGE' and g['workflow_mutation_active'] is False and g['ruleset_mutation_active'] is False and g['operator_decision_required'] is True
 assert q['qa_recommendation']=='PENDING_FINAL_HEAD_CI_AND_RULESET_APPLICATION'
 assert rs['current_required_contexts']==['tests','OVC tiered test selection shadow'] and rs['target_required_contexts']==['OVC merge readiness'] and rs['accepted_source']=={'app_id':15368,'app_slug':'github-actions'}
 material='\n'.join([REG.read_text(),QA.read_text(),DECISION.read_text(),RULESET.read_text()])
 for token in ('ghp_','github_pat_','-----BEGIN PRIVATE KEY-----','sk-proj_','Bearer '): assert token not in material
 print(f'DA2-G1 orchestration validation PASS; workflows={len(actual)}; pr_workflows={len(pr)}'); return 0
if __name__=='__main__': raise SystemExit(main())
