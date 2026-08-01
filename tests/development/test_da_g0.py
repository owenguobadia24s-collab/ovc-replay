from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class DevelopmentAccelerationG0Test(unittest.TestCase):
    def test_da_g0_validator(self) -> None:
        root = Path(__file__).resolve().parents[2]
        path = root / "scripts" / "development" / "validate_da_g0.py"
        spec = importlib.util.spec_from_file_location("validate_da_g0", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
