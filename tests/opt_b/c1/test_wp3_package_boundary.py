from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "ovc" / "opt_b" / "c1"


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

    def test_wp3_does_not_create_market_payloads_or_release_files(self) -> None:
        self.assertFalse(any((ROOT / "src" / "ovc" / "opt_b" / "c1").rglob("*.csv")))
        self.assertFalse(any((ROOT / "src" / "ovc" / "opt_b" / "c1").rglob("*.parquet")))
        selectors = (ROOT / "registries" / "opt_b" / "c1" / "C1_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("state: NONE", selectors)
        self.assertEqual(selectors.count("selector_state: NONE"), 3)


if __name__ == "__main__":
    unittest.main()
