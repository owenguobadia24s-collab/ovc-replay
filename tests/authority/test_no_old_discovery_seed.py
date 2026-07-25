from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_FILES = (
    ROOT / "fixtures" / "opt_a" / "FIXTURE_PACK.json",
    ROOT / "fixtures" / "c1" / "FIXTURE_PACK.json",
    ROOT / "fixtures" / "c2" / "FIXTURE_PACK.json",
)
PROHIBITED_TOKENS = (
    "CAND-",
    "STORY-",
    "B-STATE-0.3",
    "B-REF-0.2",
    "OPT-C-MEASURE",
    "OPT-D-",
    "PAPER-PLAYBOOK",
    "202 blocked",
    "58 research candidates",
)


class NoOldDiscoverySeedTests(unittest.TestCase):
    def test_fixture_packs_have_no_legacy_seed_tokens(self) -> None:
        violations: list[str] = []
        for path in FIXTURE_FILES:
            payload = json.loads(path.read_text(encoding="utf-8"))
            serialized = json.dumps(payload, sort_keys=True)
            for token in PROHIBITED_TOKENS:
                if token in serialized:
                    violations.append(f"{path.relative_to(ROOT)}: {token}")
            for case in payload["cases"]:
                self.assertEqual("DENIED", case["authority"]["discovery_seed"])
                self.assertEqual("DENIED", case["authority"]["release_parent"])
                self.assertEqual("NONE", case["authority"]["market"])
        self.assertEqual([], violations)

    def test_active_model_source_has_no_legacy_seed_tokens(self) -> None:
        violations: list[str] = []
        for path in sorted((ROOT / "src" / "ovc").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in PROHIBITED_TOKENS:
                if token in text:
                    violations.append(f"{path.relative_to(ROOT)}: {token}")
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
