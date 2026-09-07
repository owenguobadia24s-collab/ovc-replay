from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REQUEST = ROOT / "docs/programmes/c2e-boundary-stability-v0-1/wp6/CBSI_G2_ALGORITHM_REVIEW_REQUEST_v0_1.json"
CANDIDATE = ROOT / "registries/research_operations/cbs/CBSI_WP6_DEVELOPMENT_RESEARCH_PROTOCOL_CANDIDATE_v0_1.json"


def _blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()


def _fresh_pytest(seed: str, tests: list[str]) -> dict[str, object]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = f"{ROOT}{os.pathsep}{ROOT / 'src'}"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q"], cwd=ROOT, env=environment,
        text=True, capture_output=True, check=False,
    )
    return {"seed": seed, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def main() -> int:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    drift = {path: {"expected": expected, "observed": _blob(path)}
             for path, expected in request["frontier"].items() if _blob(path) != expected}
    sys.path.insert(0, str(ROOT / "src"))
    from ovc.research_operations.cbs.development_candidate import build_development_candidate

    generated = build_development_candidate()["protocol"]
    recorded = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    tests = [
        "tests/research_operations/cbs/test_cbsi_wp2_source_universe.py",
        "tests/research_operations/cbs/test_cbsi_wp3_comparators.py",
        "tests/research_operations/cbs/test_cbsi_wp4_correspondence.py",
        "tests/research_operations/cbs/test_cbsi_wp5_assurance.py",
        "tests/research_operations/cbs/test_cbsi_wp6_preregistration.py",
    ]
    runs = [_fresh_pytest("1", tests), _fresh_pytest("987654", list(reversed(tests)))]
    result = {
        "schema":"ovc-cbs-g2-mechanical-reproduction-output/v0.1",
        "frontier_drift":drift,
        "candidate_reconstructed_exactly":generated == recorded,
        "fresh_process_runs":runs,
        "mechanical_reproduction_complete":not drift and generated == recorded and all(run["returncode"] == 0 for run in runs),
        "reviewer_decision":"REQUIRED_SEPARATELY_THIS_RUNNER_DOES_NOT_SELF_CERTIFY_G2",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["mechanical_reproduction_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
