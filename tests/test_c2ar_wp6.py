"""Top-level discovery bridge for the bounded C2AR-WP6 assurance suites."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGETS = (
    ROOT / "opt_b/c2/vnext/test_integrated_shadow_freeze.py",
    ROOT / "opt_b/c2/vnext/test_formula_profiles.py",
)


def _load(path: Path):
    name = f"c2ar_wp6_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    for path in TARGETS:
        suite.addTests(loader.loadTestsFromModule(_load(path)))
    return suite
