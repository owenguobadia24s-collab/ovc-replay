from __future__ import annotations

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
from tools.ci.build_vit_pr_lineage import build_record
from tools.ci.vit_no_late_surprises import compile_prequalification


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class NoLateSurprisesPrequalificationTests(unittest.TestCase):
    def _repo(self) -> tuple[TemporaryDirectory, Path, str]:
        tmp = TemporaryDirectory()
        root = Path(tmp.name)
        git(root, "init", "-q")
        git(root, "config", "user.email", "nls@example.invalid")
        git(root, "config", "user.name", "NLS Test")
        (root / "base.txt").write_text("base\n", encoding="utf-8")
        git(root, "add", "base.txt")
        git(root, "commit", "-qm", "base")
        return tmp, root, git(root, "rev-parse", "HEAD")

    def _record(self, root: Path, base: str, head: str) -> dict:
        return build_record(
            repo=root,
            base=base,
            head=head,
            programme_id="OVC-DSAI-VIT-v0.3",
            packet_id="DSAI3V-NLS-TEST",
            authority_manifest_id="2" * 64,
            dependency_frontier_id="3" * 64,
            completion_transition={"status": "COMPLETED"},
        )

    def test_unrelated_main_movement_does_not_change_prequalification_identity(self) -> None:
        tmp, root, base = self._repo()
        self.addCleanup(tmp.cleanup)
        git(root, "branch", "main", base)
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        git(root, "add", "payload.txt")
        git(root, "commit", "-qm", "candidate")
        head = git(root, "rev-parse", "HEAD")
        record = self._record(root, base, head)
        first = compile_prequalification(root=root, head_sha=head, lineage_record=record)

        git(root, "checkout", "-q", "main")
        (root / "unrelated.txt").write_text("main moved\n", encoding="utf-8")
        git(root, "add", "unrelated.txt")
        git(root, "commit", "-qm", "unrelated main movement")
        self.assertNotEqual(git(root, "rev-parse", "main"), base)

        second = compile_prequalification(root=root, head_sha=head, lineage_record=record)
        self.assertEqual(first, second)
        self.assertNotIn("main", json.dumps(first, sort_keys=True).lower())
        self.assertNotIn("placement", json.dumps(first, sort_keys=True).lower())

    def test_forward_pip_cannot_embed_physical_main_identity(self) -> None:
        tmp, root, base = self._repo()
        self.addCleanup(tmp.cleanup)
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        git(root, "add", "payload.txt")
        git(root, "commit", "-qm", "candidate")
        head = git(root, "rev-parse", "HEAD")
        record = self._record(root, base, head)
        pip = dict(record["pip"])
        pip["main_sha"] = base
        contaminated = build_vit_payload_lineage_record(
            programme_id="OVC-DSAI-VIT-v0.3",
            packet_id="DSAI3V-NLS-TEST",
            pip_identity_payload=pip,
        )
        with self.assertRaisesRegex(RuntimeError, "NLS_PHYSICAL_PLACEMENT_IDENTITY_FORBIDDEN:main_sha"):
            compile_prequalification(root=root, head_sha=head, lineage_record=contaminated)

    def test_shared_systems_undeclared_dependency_fails_before_qualification(self) -> None:
        tmp, root, base = self._repo()
        self.addCleanup(tmp.cleanup)
        path = root / "tests/shared_systems/test_packet.py"
        path.parent.mkdir(parents=True)
        path.write_text("from jsonschema import Draft202012Validator\n", encoding="utf-8")
        git(root, "add", str(path.relative_to(root)))
        git(root, "commit", "-qm", "candidate")
        head = git(root, "rev-parse", "HEAD")
        record = self._record(root, base, head)
        with self.assertRaisesRegex(
            RuntimeError,
            "NLS_SHARED_SYSTEMS_UNDECLARED_DEPENDENCY:tests/shared_systems/test_packet.py:jsonschema",
        ):
            compile_prequalification(root=root, head_sha=head, lineage_record=record)

    def test_shared_systems_stdlib_pytest_and_project_imports_are_accepted(self) -> None:
        tmp, root, base = self._repo()
        self.addCleanup(tmp.cleanup)
        (root / "src/ovc").mkdir(parents=True)
        (root / "src/ovc/__init__.py").write_text("\n", encoding="utf-8")
        path = root / "tests/shared_systems/test_packet.py"
        path.parent.mkdir(parents=True)
        path.write_text(
            "import json\nimport pytest\nfrom ovc import __name__ as project_name\n",
            encoding="utf-8",
        )
        git(root, "add", ".")
        git(root, "commit", "-qm", "candidate")
        head = git(root, "rev-parse", "HEAD")
        record = self._record(root, base, head)
        receipt = compile_prequalification(root=root, head_sha=head, lineage_record=record)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["compiler_version"], "NLS/1")

    def test_declared_pip_blob_must_match_exact_head(self) -> None:
        tmp, root, base = self._repo()
        self.addCleanup(tmp.cleanup)
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        git(root, "add", "payload.txt")
        git(root, "commit", "-qm", "candidate")
        head = git(root, "rev-parse", "HEAD")
        record = self._record(root, base, head)
        pip = dict(record["pip"])
        changes = [dict(change) for change in pip["logical_changes"]]
        changes[0]["blob_sha"] = "1" * 40
        pip["logical_changes"] = changes
        mismatched = build_vit_payload_lineage_record(
            programme_id="OVC-DSAI-VIT-v0.3",
            packet_id="DSAI3V-NLS-TEST",
            pip_identity_payload=pip,
        )
        with self.assertRaisesRegex(RuntimeError, "NLS_PIP_HEAD_BLOB_MISMATCH:payload.txt"):
            compile_prequalification(root=root, head_sha=head, lineage_record=mismatched)


if __name__ == "__main__":
    unittest.main()
