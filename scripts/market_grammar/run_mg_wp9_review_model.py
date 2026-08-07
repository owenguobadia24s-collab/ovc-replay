#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from ovc.opt_b.market_grammar.review_surfaces import build_review_model
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'fixtures/market_grammar/wp8/topology_smoke_cases.json'
PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
LEDGER=ROOT/'registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json'
def load(path):
 value=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(value,dict): raise ValueError('JSON root must be object')
 return value
def run():
 ledger=load(LEDGER); records=[load(ROOT/item['path']) for item in ledger['migration_records']]
 return build_review_model(load(FIXTURE),load(PACKS),ledger,records)
def main():
 parser=argparse.ArgumentParser(description='Build the deterministic MG-WP9 read-only review model.'); parser.add_argument('--output',type=Path); args=parser.parse_args(); result=run(); payload=json.dumps(result,sort_keys=True,separators=(',',':'))+'\n'
 if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(payload,encoding='utf-8')
 else: print(payload,end='')
 return 0
if __name__=='__main__': raise SystemExit(main())
