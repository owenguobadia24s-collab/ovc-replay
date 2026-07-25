from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


class NoReverseDependencyTests(unittest.TestCase):
    def assert_no_imports(self, source_root: Path, forbidden: tuple[str, ...]) -> None:
        violations: list[str] = []
        for path in sorted(source_root.rglob("*.py")):
            for module in imported_modules(path):
                if any(matches(module, prefix) for prefix in forbidden):
                    violations.append(f"{path.relative_to(ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_opt_a_does_not_read_opt_b_or_later(self) -> None:
        self.assert_no_imports(ROOT / "src" / "ovc" / "opt_a", ("ovc.opt_b", "ovc.opt_c", "ovc.opt_d", "legacy", "ovc_opt_b"))

    def test_c1_does_not_read_c2_or_later(self) -> None:
        self.assert_no_imports(ROOT / "src" / "ovc" / "opt_b" / "c1", ("ovc.opt_b.c2", "ovc.opt_c", "ovc.opt_d", "legacy", "ovc_opt_b"))

    def test_c2_does_not_read_deferred_or_historical_layers(self) -> None:
        self.assert_no_imports(ROOT / "src" / "ovc" / "opt_b" / "c2", ("ovc.opt_b.c2e", "ovc.opt_b.c2_5", "ovc.opt_b.c3", "ovc.opt_c", "ovc.opt_d", "legacy", "ovc_opt_b"))

    def test_evidence_store_does_not_depend_on_model_tree(self) -> None:
        self.assert_no_imports(ROOT / "src" / "ovc_evidence_store", ("ovc", "legacy", "ovc_opt_b"))


if __name__ == "__main__":
    unittest.main()
