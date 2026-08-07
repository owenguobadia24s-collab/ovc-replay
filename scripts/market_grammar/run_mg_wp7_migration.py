from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from ovc.opt_b.market_grammar.candidate_migration import build_input_from_sources,build_migration_artifacts

def _load_json(path:Path): return json.loads(path.read_text(encoding="utf-8"))
def _load_jsonl(path:Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def _sha(path:Path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    parser=argparse.ArgumentParser(description="Build the MG-WP7 compact migration ledger from the three accepted CEAR-G10 external artifacts.")
    parser.add_argument("--rule-candidates",type=Path,required=True)
    parser.add_argument("--functional-cores",type=Path,required=True)
    parser.add_argument("--disposition-evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--feature-registry-output",type=Path,required=True)
    parser.add_argument("--candidate-output-dir",type=Path,required=True)
    args=parser.parse_args()
    expected={
        "rule_candidates":"db9966224abd75619971bbdbff40e078e955ee5b933fa82416ceab2048521230",
        "functional_cores":"77f9ee2a58d5d8b9fcf0eb43cf20a9cef4c69ba8c2fe8750a6a04d123a2f1bae",
        "cear_g10_disposition_evidence":"6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944",
    }
    actual={"rule_candidates":_sha(args.rule_candidates),"functional_cores":_sha(args.functional_cores),"cear_g10_disposition_evidence":_sha(args.disposition_evidence)}
    for key,value in expected.items():
        if actual[key]!=value: raise SystemExit(f"{key} SHA-256 mismatch: {actual[key]} != {value}")
    source_artifacts={
        "rule_candidates":{"drive_file_id":"1rVbwRC_fD7SIO_XmZd_OCBppudKrQ0_6","raw_sha256":actual["rule_candidates"],"record_count":14},
        "functional_cores":{"drive_file_id":"1rvuaLZ82IzcAInejQRExWJ_V5_i61dRy","raw_sha256":actual["functional_cores"],"record_count":14},
        "cear_g10_disposition_evidence":{"drive_file_id":"1xffbDKFIGEK8MLNH-eh3UdhBueASHTU4","raw_sha256":actual["cear_g10_disposition_evidence"],"content_sha256":"4a21f3db44f8a6587ff863bb24fc6fe213f73ea9cf47d9d6cd69ba2e82b16fc2"},
    }
    payload=build_input_from_sources(_load_jsonl(args.rule_candidates),_load_json(args.functional_cores),_load_json(args.disposition_evidence),source_artifacts)
    ledger,feature_registry,candidate_records=build_migration_artifacts(payload)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.feature_registry_output.parent.mkdir(parents=True,exist_ok=True)
    args.candidate_output_dir.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(ledger,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    args.feature_registry_output.write_text(json.dumps(feature_registry,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    for record,ref in zip(candidate_records,ledger["migration_records"]):
        target=args.candidate_output_dir/Path(ref["path"]).name
        target.write_text(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
