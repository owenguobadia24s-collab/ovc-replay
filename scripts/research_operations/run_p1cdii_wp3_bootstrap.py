from __future__ import annotations

import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_json_bytes  # noqa: E402
from ovc.research_operations.p1cdi.bootstrap import (  # noqa: E402
    freeze_source_census,
    reconcile_source_census,
    scan_repository_source_subjects,
)


def main() -> int:
    census = freeze_source_census(
        census_id="P1CDI-G0-SOURCE-CENSUS:lawful-main-35d3dc73:v0.2",
        as_of_commit="35d3dc736d5b16b3113a89cc1733a9c75bafd139",
        subjects=scan_repository_source_subjects(ROOT),
    )
    completeness = reconcile_source_census(
        manifest_id="P1CDI-G0-SOURCE-COMPLETENESS:lawful-main-35d3dc73:v0.1",
        census=census,
        subjects=[],
    )
    digest = hashlib.sha256(
        canonical_json_bytes({"census": census, "completeness": completeness})
    ).hexdigest()
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
