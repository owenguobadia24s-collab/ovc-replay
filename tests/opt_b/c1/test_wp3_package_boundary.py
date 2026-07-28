from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "ovc" / "opt_b" / "c1"
CORRECTIVE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G4_G5_COORDINATED_SELECTOR_TRANSACTION.json"


class C1WP3PackageBoundaryTests(unittest.TestCase):
    def test_reference_engine_has_no_legacy_or_downstream_imports(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py"))
        for forbidden in (
            "ovc_opt_b",
            "ovc.opt_b.c2",
            "opt_c",
            "opt_d",
            "future_return",
            "trade_label",
        ):
            self.assertNotIn(forbidden, text)

    def test_reference_engine_contains_no_network_or_remote_write_code(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py"))
        for forbidden in ("requests.", "urllib", "boto3", "rclone", "cloudflare", "subprocess"):
            self.assertNotIn(forbidden, text)

    def test_wp3_package_remains_payload_free_after_later_selector_transitions(self) -> None:
        self.assertFalse(any((ROOT / "src" / "ovc" / "opt_b" / "c1").rglob("*.csv")))
        self.assertFalse(any((ROOT / "src" / "ovc" / "opt_b" / "c1").rglob("*.parquet")))
        selectors = (ROOT / "registries" / "opt_b" / "c1" / "C1_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        if CORRECTIVE.exists():
            transaction = json.loads(CORRECTIVE.read_text(encoding="utf-8"))
            self.assertTrue(transaction["atomic_on_main_merge"])
            self.assertIn("state: ACTIVE", selectors)
            self.assertEqual(selectors.count("selector_state: ACTIVE"), 2)
            self.assertEqual(selectors.count("selector_state: NONE"), 1)
            self.assertIn("OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2", selectors)
            self.assertIn("OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2", selectors)
            self.assertIn("C1.IMPLEMENTATION.v0.2", selectors)
            self.assertIn("c2_consumption: AUTHORISED_EXACT_C2_V2_ACTIVE_DISCOVERY_PARENT", selectors)
        else:
            self.assertIn("state: SHADOW", selectors)
            self.assertEqual(selectors.count("selector_state: SHADOW"), 2)
            self.assertEqual(selectors.count("selector_state: NONE"), 1)
            self.assertIn("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW", selectors)


if __name__ == "__main__":
    unittest.main()
