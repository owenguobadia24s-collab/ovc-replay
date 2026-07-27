from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


class RO3G0DesignTests(unittest.TestCase):
    def test_design_validator_passes(self) -> None:
        root = Path(__file__).resolve().parents[3]
        path = root / "scripts" / "research_operations" / "validate_ro3_g0_design.py"
        spec = importlib.util.spec_from_file_location("validate_ro3_g0_design", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
