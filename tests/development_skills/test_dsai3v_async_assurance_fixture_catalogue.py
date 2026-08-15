from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/development_skills/async_assurance/DSAI3V_AA_QUALIFICATION_FIXTURES_v1.json"


class Dsai3vAsyncAssuranceFixtureCatalogueTests(unittest.TestCase):
    def test_exact_eighteen_qualification_fixtures_and_zero_tolerance_surface(self) -> None:
        record = json.loads(FIXTURE.read_text(encoding="utf-8"))
        ids = [row["id"] for row in record["fixtures"]]
        self.assertEqual(ids, [f"AA-AV{index:02d}" for index in range(1, 19)])
        self.assertEqual(len({row["scenario"] for row in record["fixtures"]}), 18)
        self.assertEqual(record["authority_effect"], "NONE_SYNTHETIC_SHADOW_ONLY")
        self.assertEqual(
            set(record["zero_tolerance"]),
            {
                "FALSE_AUTHORITY_ALLOW",
                "DUPLICATE_EFFECTIVE_MERGE",
                "ACCEPTED_TREE_MISMATCH",
                "PARALLEL_PHYSICAL_MERGE",
                "LOST_MANDATORY_COMPLETION_RECEIPT",
                "PROVIDER_ADAPTER_WRITE_REACHABILITY",
            },
        )


if __name__ == "__main__":
    unittest.main()
