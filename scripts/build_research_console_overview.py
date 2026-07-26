from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.console_overview_candidate import CandidateOverviewProjectionBuilder
from ovc.research_operations.read_model import ReadModelNode, ResearchReadModel


def load_read_model(path: Path) -> ResearchReadModel:
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes = tuple(
        ReadModelNode(
            object_id=str(node["object_id"]),
            object_type=str(node["object_type"]),
            authority=str(node["authority"]),
            status=str(node["status"]),
            source_refs=tuple(str(value) for value in node.get("source_refs", [])),
            payload=dict(node.get("payload", {})),
        )
        for node in raw.get("nodes", [])
    )
    return ResearchReadModel(
        schema=str(raw["schema"]),
        source_commit=str(raw["source_commit"]),
        catalogue_sha256=raw.get("catalogue_sha256"),
        nodes=nodes,
        health=tuple(dict(item) for item in raw.get("health", [])),
        logical_sha256=str(raw["logical_sha256"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the RC-WP2-v0.3 deterministic Overview projection candidate"
    )
    parser.add_argument(
        "--read-model",
        type=Path,
        default=Path("var/research_operations/read_model/current.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/research_operations/console/overview_candidate.json"),
    )
    args = parser.parse_args()

    if not args.read_model.is_file():
        raise FileNotFoundError(f"Research read model unavailable: {args.read_model}")

    projection = CandidateOverviewProjectionBuilder().build(load_read_model(args.read_model))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(projection.to_dict(), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(projection.logical_sha256)
    print("CANDIDATE_ONLY_PENDING_RC_G2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
