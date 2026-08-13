from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.wp0 import reconcile, write_reconciliation_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce immutable GRT B0 and build the separate GRT2-WP0 current-tree census."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--output-dir", default="docs/programmes/grt-v0-2/wp0")
    parser.add_argument("--single-b0-run", action="store_true", help="Diagnostic only; G1 evidence requires determinism proof.")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = Path(args.output_dir)
    if not output.is_absolute():
        output = root / output
    result = reconcile(
        root,
        baseline_commit=args.baseline_commit,
        verify_b0_determinism=not args.single_b0_run,
    )
    write_reconciliation_outputs(result, output)
    print(
        json.dumps(
            {
                "baseline_commit": result["baseline"]["commit"],
                "baseline_tree": result["baseline"]["tree"],
                "b0_warning_count": result["b0"]["raw_warning_count"],
                "b0_topology_sha256": result["b0"]["topology_sha256"],
                "current_warning_count": result["current_census"]["raw_warning_count"],
                "b0_mapped": len(result["current_census"]["classification"]["B0_MAPPED"]),
                "late_discovered_pre_existing": len(
                    result["current_census"]["classification"]["LATE_DISCOVERED_PRE_EXISTING"]
                ),
                "resolved_before_grt2": len(
                    result["current_census"]["classification"]["RESOLVED_BEFORE_GRT2"]
                ),
                "transition_or_new_debt": len(
                    result["current_census"]["classification"]["TRANSITION_OR_NEW_DEBT"]
                ),
                "authority_effect": result["authority_effect"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
