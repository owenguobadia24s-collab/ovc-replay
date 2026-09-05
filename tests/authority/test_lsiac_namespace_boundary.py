from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class LsiacNamespaceBoundaryTests(unittest.TestCase):
    def test_lsiac_namespace_is_governance_only_and_non_authoritative(self) -> None:
        init_text = (
            ROOT / "src" / "ovc" / "research_operations" / "lsiac" / "__init__.py"
        ).read_text(encoding="utf-8").lower()

        for token in (
            "governance-only",
            "research-only",
            "non-authoritative",
            "frontier accounting only",
            "selector",
            "scientific-promotion",
            "validation",
            "publication",
            "probability",
            "risk",
            "exposure",
            "trading",
            "execution",
            "agent-write authority",
            "fails closed",
        ):
            self.assertIn(token, init_text)


if __name__ == "__main__":
    unittest.main()
