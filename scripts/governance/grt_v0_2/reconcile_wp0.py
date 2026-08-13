from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.wp0_evidence import (
    reconcile,
    write_reconciliation_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce immutable GRT B0 and build the separate GRT2-WP0 current-tree census."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--output-dir", default="docs/programmes/grt-v0-2/wp0")
    parser.add_argument(
        "--single-b0-run",
        action="store_true",
        help="Diagnostic only; G1 evidence requires determinism proof.",
    )
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
    lineage = result["current_census"]["lineage_classification"]
    print(
        json.dumps(
            {
                "baseline_commit": result["baseline"]["commit"],
                "baseline_tree": result["baseline"]["tree"],
                "b0_warning_count": result["b0"]["raw_warning_count"],
                "b0_topology_sha256": result["b0"]["topology_sha256"],
                "current_warning_count": result["current_census"]["raw_warning_count"],
                "lineage_classification_status": lineage["status"],
                "direct_anomaly_id_match_count": lineage["direct_anomaly_id_match_count"],
                "current_only_anomaly_id_count": lineage["current_only_anomaly_id_count"],
                "b0_only_anomaly_id_count": lineage["b0_only_anomaly_id_count"],
                "transition_debt_status": result["current_census"]["transition_debt_status"],
                "authority_effect": result["authority_effect"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
