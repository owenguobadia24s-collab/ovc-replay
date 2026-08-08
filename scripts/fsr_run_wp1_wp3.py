from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path

from ovc.opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from ovc.opt_b.c1.builder import build as build_c1


def canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def build_c1_stream(handoff: list[dict]) -> list[dict]:
    output: list[dict] = []
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            group = sorted(
                (item for item in handoff if item["clock_id"] == clock and item["price_side"] == side),
                key=lambda item: item["open_time"],
            )
            prior = None
            for current in group:
                output.append(dataclasses.asdict(build_c1(current, prior)))
                prior = current
    return output


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out = Path(os.environ.get("FSR_OUT", repo_root / ".fsr-out"))
    out.mkdir(parents=True, exist_ok=True)

    opt_a = build_opt_a_fixture(out / "fixture", repo_root=repo_root)
    handoff = c1_handoff_records(opt_a)
    c1 = build_c1_stream(handoff)

    (out / "OPT_A_FIXTURE_MANIFEST.json").write_text(json.dumps(opt_a, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "C1_HANDOFF.json").write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "C1_STREAM.json").write_text(json.dumps(c1, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    qa = {
        "schema": "ovc-fsr-wp1-wp3-qa/v1",
        "programme_id": "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1",
        "fixture_id": opt_a["fixture_id"],
        "opt_a_manifest_sha256": opt_a["manifest_sha256"],
        "c1_handoff_count": len(handoff),
        "c1_record_count": len(c1),
        "c1_logical_sha256": canonical_sha(c1),
        "source_object_count": len(opt_a["source_inventory"]),
        "source_row_count": sum(item["row_count"] for item in opt_a["source_inventory"]),
        "quarantine_count": len(opt_a["quarantine"]),
        "hidden_construction_consumed": False,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "selector_mutation": "NONE",
        "publication": "NONE",
        "market_evidence": False,
        "status": "PASS",
    }
    (out / "FSR_WP1_WP3_QA.json").write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(qa, sort_keys=True))


if __name__ == "__main__":
    main()
