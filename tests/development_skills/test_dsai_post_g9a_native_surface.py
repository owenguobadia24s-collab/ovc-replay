from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import tempfile
import unittest


NATIVE_MODULES = (
    "tests.development_skills.test_dsai_wp9_orch2_qualification",
    "tests.development_skills.test_dsai_wp9_orch2_git_sandbox",
    "tests.development_skills.test_dsai_g9b_gate_ready",
    "tests.development_skills.test_dsai_g9b_operator_orch2_activation",
    "tests.development_skills.test_dsai_wp9_g9b_post_merge_reconciliation",
    "tests.development_skills.test_dsai_wp10_console_projection",
    "tests.development_skills.test_dsai_g10_auto_ratification",
    "tests.development_skills.test_dsai_wp10_g10_post_merge_reconciliation",
    "tests.development_skills.test_dsai_wp11_post_pilot_review",
    "tests.development_skills.test_dsai_g11_auto_ratification",
)


class DSAIPostG9ANativeSurfaceTests(unittest.TestCase):
    """Run post-G9A pytest-native conformance tests under canonical unittest CI."""

    def _invoke(self, module_name: str, name: str, fn) -> None:
        params = list(inspect.signature(fn).parameters)
        try:
            if not params:
                fn()
                return
            if params == ["tmp_path"]:
                with tempfile.TemporaryDirectory(prefix="ovc-dsai-native-") as tmp:
                    fn(Path(tmp))
                return
            self.fail(f"Unsupported native fixture signature {module_name}.{name}{tuple(params)}")
        except Exception as exc:
            detail = f"{module_name}.{name}: {type(exc).__name__}: {exc}"
            print(f"::error title=DSAI native-surface failure::{detail}", flush=True)
            raise

    def _run_native_module(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        functions = [
            (name, fn)
            for name, fn in inspect.getmembers(module, inspect.isfunction)
            if name.startswith("test_") and fn.__module__ == module.__name__
        ]
        self.assertTrue(functions, f"No native test functions found in {module_name}")
        for name, fn in functions:
            with self.subTest(module=module_name, native_test=name):
                self._invoke(module_name, name, fn)

    def test_post_g9a_native_modules_are_exercised_by_canonical_unittest(self):
        for module_name in NATIVE_MODULES:
            with self.subTest(native_module=module_name):
                self._run_native_module(module_name)


if __name__ == "__main__":
    unittest.main()
