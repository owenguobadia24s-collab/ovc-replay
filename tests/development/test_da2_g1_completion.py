from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/development/v0_2/validate_da2_g1_completion.py"

class DA2G1CompletionTests(unittest.TestCase):
    def test_completion_packet(self) -> None:
        spec = importlib.util.spec_from_file_location("da2_g1_completion", VALIDATOR)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

if __name__ == "__main__":
    unittest.main()
