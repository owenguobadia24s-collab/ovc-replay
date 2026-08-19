from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_sha256


TEST_PATH = ROOT / "tests/research_operations/p2cti/test_p2ctii_wp4_remediation_2.py"


def _load_test_module():
    spec = importlib.util.spec_from_file_location("p2ctii_wp4_remediation_2_tests", TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load WP4 remediation-2 evidence module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_test_module()
    evidence = module.build_remediation_2_evidence()
    failures = [name for name, result in evidence["cases"].items() if result != "PASS"]
    if failures:
        raise SystemExit(f"P2CTII_WP4_REMEDIATION_2_FAILURES:{','.join(failures)}")
    print(canonical_sha256(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
