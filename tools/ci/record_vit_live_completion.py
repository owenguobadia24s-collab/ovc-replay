from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_live_completion import record_live_completion


def _load_mapping(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _load_sequence(path: str | None) -> Sequence[Mapping[str, Any]]:
    if not path:
        return ()
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"expected JSON array of objects: {path}")
    return tuple(value)


def _decode_lineage(*, lineage_file: str | None, lineage_b64: str | None) -> Mapping[str, Any]:
    if bool(lineage_file) == bool(lineage_b64):
        raise RuntimeError("provide exactly one of --lineage-file or --lineage-b64")
    if lineage_file:
        value = json.loads(Path(lineage_file).read_text(encoding="utf-8"))
    else:
        token = str(lineage_b64)
        token += "=" * (-len(token) % 4)
        value = json.loads(base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT lineage must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Persist one post-merge VIT physical materialisation + PacketCompletionReceipt + "
            "canonical DEVOBS attachment into the governed local ReceiptStore."
        )
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--lineage-file")
    parser.add_argument("--lineage-b64")
    parser.add_argument("--predecessor-commit", required=True)
    parser.add_argument("--observed-commit", required=True)
    parser.add_argument("--implementation-ref", required=True)
    parser.add_argument("--qa-ref", required=True)
    parser.add_argument("--gate-decision-ref", required=True)
    parser.add_argument("--assurance-frontier-id", required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--contextual-latency-receipt")
    parser.add_argument("--trace-summary")
    parser.add_argument("--orch-receipts")
    parser.add_argument("--vit-receipts")
    parser.add_argument("--siq-receipts")
    parser.add_argument("--async-assurance-metrics")
    args = parser.parse_args()

    lineage = _decode_lineage(lineage_file=args.lineage_file, lineage_b64=args.lineage_b64)
    result = record_live_completion(
        args.repo,
        lineage=lineage,
        predecessor_commit=args.predecessor_commit,
        observed_commit=args.observed_commit,
        implementation_ref=args.implementation_ref,
        qa_ref=args.qa_ref,
        gate_decision_ref=args.gate_decision_ref,
        assurance_frontier_id=args.assurance_frontier_id,
        attempt=args.attempt,
        contextual_latency_receipt=_load_mapping(args.contextual_latency_receipt),
        trace_summary=_load_mapping(args.trace_summary),
        orch_receipts=_load_sequence(args.orch_receipts),
        vit_receipts=_load_sequence(args.vit_receipts),
        siq_receipts=_load_sequence(args.siq_receipts),
        async_assurance_metrics=_load_mapping(args.async_assurance_metrics),
    )
    print(json.dumps(asdict(result), sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
