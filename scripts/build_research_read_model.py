from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.catalogue import read_catalogue
from ovc.research_operations.read_model import ReadModelBuilder


def load_records(root: Path) -> list[dict]:
    records: list[dict] = []
    if not root.exists():
        return records
    for path in sorted(root.rglob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "record_type" in value:
            records.append(value)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the replaceable RO-WP3 typed read model")
    parser.add_argument("--records-root", type=Path, default=Path("records/research_operations"))
    parser.add_argument("--catalogue", type=Path, default=Path("var/research_operations/catalogue/current.json"))
    parser.add_argument("--output", type=Path, default=Path("var/research_operations/read_model/current.json"))
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    catalogue = read_catalogue(args.catalogue) if args.catalogue.is_file() else None
    model = ReadModelBuilder().build(source_commit=args.source_commit, catalogue=catalogue, records=load_records(args.records_root))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model.to_dict(), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(model.logical_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
