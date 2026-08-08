from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from ovc.opt_b.srfd.source_adapter import C2SourceBinding
from ovc.opt_b.srfd.source_adapter_v02 import bind_source_population


def _rows(paths: Iterable[str]):
    for raw_path in paths:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"invalid JSONL {path}:{line_number}: {exc}") from exc
                if not isinstance(value, dict):
                    raise SystemExit(f"JSONL row must be an object {path}:{line_number}")
                yield value


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind an already-accepted SRFD v0.2 C1/C2 source population read-only.")
    parser.add_argument("--c1", action="append", required=True, help="C1 JSONL path; repeat for all frozen clock/side files")
    parser.add_argument("--c2", action="append", required=True, help="C2 state JSONL path; repeat for all frozen representation scopes")
    parser.add_argument("--source-release-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-slice-id", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--output-manifest-sha256", required=True)
    parser.add_argument("--active-c2-model-release-id", required=True)
    parser.add_argument("--benchmark-start", default="2026-06-01T00:00:00Z")
    parser.add_argument("--benchmark-end", default="2026-07-01T00:00:00Z")
    parser.add_argument("--context-start", default="2026-05-30T00:00:00Z")
    parser.add_argument("--context-end", default="2026-07-03T00:00:00Z")
    parser.add_argument("--output", help="Optional compact JSON output path; stdout is always emitted")
    args = parser.parse_args()

    binding = C2SourceBinding(
        source_release_id=args.source_release_id,
        source_commit=args.source_commit,
        source_slice_id=args.source_slice_id,
        source_manifest_sha256=args.source_manifest_sha256,
        output_manifest_sha256=args.output_manifest_sha256,
        active_c2_model_release_id=args.active_c2_model_release_id,
        benchmark_start_inclusive_utc=args.benchmark_start,
        benchmark_end_exclusive_utc=args.benchmark_end,
        context_start_utc=args.context_start,
        context_end_exclusive_utc=args.context_end,
    )
    result = bind_source_population(_rows(args.c2), _rows(args.c1), binding)
    compact = dict(result)
    compact.pop("eligible_record_ids", None)
    compact.pop("exclusions", None)
    compact["schema"] = "ovc-srfdi-real-source-population-binding/v1"
    compact["source_binding"] = binding.to_dict()
    compact["authority_state"] = "READ_ONLY_BINDING_CANDIDATE_NO_RUN_AUTHORITY"
    text = json.dumps(compact, sort_keys=True, separators=(",", ":")) + "\n"
    print(text, end="")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
