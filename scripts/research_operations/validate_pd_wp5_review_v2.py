from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ovc.research_operations.pattern_discovery.review_corrections import (
    OPERATOR_ID,
    validate_review_input_v2,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a PD-WP5 structured review input v2 without writing evidence.")
    parser.add_argument("review_file", type=Path)
    parser.add_argument("template_file", type=Path)
    args = parser.parse_args(argv)

    try:
        review = json.loads(args.review_file.read_text(encoding="utf-8"))
        template = json.loads(args.template_file.read_text(encoding="utf-8"))
        expected = [str(item["candidate_window_id"]) for item in template.get("decisions", ())]
        normalized = validate_review_input_v2(
            review,
            expected_candidate_ids=expected,
            pilot_run_id=str(review.get("pilot_run_id") or ""),
            operator_id=OPERATOR_ID,
            pilot_markings={
                "pilot_only": True,
                "promotion_eligibility": "NON_PROMOTABLE",
                "canonical_discovery_population": False,
                "canonical_append": "DENIED",
                "live_prospective": False,
            },
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"PD-WP5 review v2 invalid: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "VALID_STRUCTURED_REVIEW_V2",
        "decision_count": len(normalized),
        "candidate_window_ids": [item["candidate_window_id"] for item in normalized],
        "canonical_append": "DENIED",
        "second_pilot_replay_authorised": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
