from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_ROOTS = (ROOT / "src" / "ovc", ROOT / "src" / "ovc_evidence_store")
FORBIDDEN = ("legacy", "ovc_opt_b")


def forbidden_module(name: str) -> bool:
    return any(name == item or name.startswith(item + ".") for item in FORBIDDEN)


class NoQuarantineImports(unittest.TestCase):
    def test_active_sources_do_not_import_legacy_modules(self) -> None:
        violations: list[str] = []
        for root in ACTIVE_ROOTS:
            for path in sorted(root.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        violations.extend(
                            f"{path.relative_to(ROOT)}: {alias.name}"
                            for alias in node.names
                            if forbidden_module(alias.name)
                        )
                    elif isinstance(node, ast.ImportFrom) and node.module and forbidden_module(node.module):
                        violations.append(f"{path.relative_to(ROOT)}: {node.module}")
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
