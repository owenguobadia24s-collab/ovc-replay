#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from ovc.opt_b.market_grammar.topology_smoke import make_checkpoint,resume_topology_smoke,run_topology_smoke
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE=ROOT/'fixtures/market_grammar/wp8/topology_smoke_cases.json'
PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
MIGRATIONS=ROOT/'registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json'
def load(path):
 value=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(value,dict): raise ValueError('JSON root must be object')
 return value
def run(path=DEFAULT_FIXTURE): return run_topology_smoke(load(path),load(PACKS),load(MIGRATIONS))
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--fixture',type=Path,default=DEFAULT_FIXTURE); parser.add_argument('--checkpoint',type=Path); parser.add_argument('--write-checkpoint',type=Path); args=parser.parse_args(); fixture=load(args.fixture); packs=load(PACKS); migrations=load(MIGRATIONS)
 if args.checkpoint: result=resume_topology_smoke(fixture,packs,migrations,load(args.checkpoint))
 else: result=run_topology_smoke(fixture,packs,migrations)
 if args.write_checkpoint:
  args.write_checkpoint.parent.mkdir(parents=True,exist_ok=True); args.write_checkpoint.write_text(json.dumps(make_checkpoint(result),sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 print(json.dumps(result,sort_keys=True,separators=(',',':'))); return 0
if __name__=='__main__': raise SystemExit(main())
