from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ovc.fsr_full_stack import run_full_stack


def _head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "FSR_REHEARSAL_BRANCH_UNRESOLVED")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(os.environ.get("FSR_OUT", repo_root / ".fsr-full-stack"))
    output_root.mkdir(parents=True, exist_ok=True)
    result = run_full_stack(repo_root=repo_root, output_root=output_root, source_commit=_head())
    names = {
        "OPT_A_FIXTURE_MANIFEST.json": "opt_a",
        "C1_HANDOFF.json": "c1_handoff",
        "C1_STREAM.json": "c1",
        "C2_REVISED_SHADOW.json": "c2",
        "C2E_NEUTRAL_LEDGER.json": "c2e",
        "SRFD_BENCHMARK.json": "srfd",
        "MARKET_GRAMMAR_SHADOW.json": "market_grammar",
        "RESEARCH_OPERATIONS_PROJECTION.json": "research_operations",
        "FSR_RUN_MANIFEST.json": "run_manifest",
    }
    for filename, key in names.items():
        (output_root / filename).write_text(json.dumps(result[key], indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result["run_manifest"], sort_keys=True))


if __name__ == "__main__":
    main()
