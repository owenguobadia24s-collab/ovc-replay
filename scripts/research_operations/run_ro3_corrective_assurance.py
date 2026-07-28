from __future__ import annotations

import runpy
from decimal import getcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PINNED_RUNNER = ROOT / "scripts/research_operations/run_ro3_g3_assurance.py"
DECIMAL_PRECISION = 34


def main() -> None:
    """Run the pinned RO3 assurance under the C1 release arithmetic context.

    The independent invariant registry remains byte-frozen. This adapter only
    supplies the Decimal precision already used to build the active C1 release
    shards, removing a QA-runner context mismatch without changing an equation,
    invariant or acceptance condition.
    """

    if not PINNED_RUNNER.exists():
        raise SystemExit(f"pinned RO3 assurance runner unavailable: {PINNED_RUNNER}")
    getcontext().prec = DECIMAL_PRECISION
    runpy.run_path(str(PINNED_RUNNER), run_name="__main__")


if __name__ == "__main__":
    main()
