#!/usr/bin/env python3
"""Build reproducible pre-G3 transition-debt evidence from exact Git trees.

The output is observer evidence only. Novel observer conditions are not promoted
to constitutional debt without a v0.2 rule mapping.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import B0_SOURCE_COMMIT
from ovc.programme_genesis.grt_v0_2.g3_readiness import reconcile_observer_transition_candidates
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--current-ref", default="HEAD")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    baseline = build_repository_topology(root, ref=B0_SOURCE_COMMIT)
    current = build_repository_topology(root, ref=args.current_ref)
    result = reconcile_observer_transition_candidates(
        baseline_topology=baseline,
        current_topology=current,
    )
    result["baseline_topology_sha256"] = baseline["topology_sha256"]
    result["current_topology_sha256"] = current["topology_sha256"]
    result["evidence_hash"] = canonical_sha256(result)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
