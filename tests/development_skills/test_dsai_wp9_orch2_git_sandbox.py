from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _run(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def test_real_disposable_git_sandbox_squash_is_single_parent_and_pins_identity(tmp_path: Path):
    root = tmp_path / "orch2-sandbox"
    root.mkdir()
    _run(root, "init", "-b", "main")
    _run(root, "config", "user.email", "dsai-sandbox@ovc.local")
    _run(root, "config", "user.name", "DSAI Sandbox")

    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    _run(root, "add", "baseline.txt")
    _run(root, "commit", "-m", "baseline")
    base_sha = _git(root, "rev-parse", "HEAD")

    _run(root, "checkout", "-b", "packet")
    (root / "packet.txt").write_text("bounded packet\n", encoding="utf-8")
    _run(root, "add", "packet.txt")
    _run(root, "commit", "-m", "packet head")
    head_sha = _git(root, "rev-parse", "HEAD")

    _run(root, "checkout", "main")
    assert _git(root, "rev-parse", "HEAD") == base_sha
    _run(root, "merge", "--squash", "packet")
    _run(root, "commit", "-m", "sandbox squash receipt")
    result_sha = _git(root, "rev-parse", "HEAD")

    lineage = _git(root, "rev-list", "--parents", "-n", "1", result_sha).split()
    assert len(lineage) == 2
    assert lineage[0] == result_sha
    assert lineage[1] == base_sha
    assert head_sha not in lineage[1:]
    assert (root / "packet.txt").read_text(encoding="utf-8") == "bounded packet\n"
    assert all(len(value) == 40 for value in (base_sha, head_sha, result_sha))
    assert len({base_sha, head_sha, result_sha}) == 3


def test_disposable_git_sandbox_detects_base_movement_before_squash(tmp_path: Path):
    root = tmp_path / "orch2-race"
    root.mkdir()
    _run(root, "init", "-b", "main")
    _run(root, "config", "user.email", "dsai-sandbox@ovc.local")
    _run(root, "config", "user.name", "DSAI Sandbox")
    (root / "base.txt").write_text("v1\n", encoding="utf-8")
    _run(root, "add", "base.txt")
    _run(root, "commit", "-m", "base")
    prepared_base = _git(root, "rev-parse", "HEAD")

    _run(root, "checkout", "-b", "packet")
    (root / "packet.txt").write_text("packet\n", encoding="utf-8")
    _run(root, "add", "packet.txt")
    _run(root, "commit", "-m", "packet")
    _run(root, "checkout", "main")
    (root / "base.txt").write_text("v2\n", encoding="utf-8")
    _run(root, "add", "base.txt")
    _run(root, "commit", "-m", "main moved")
    current_base = _git(root, "rev-parse", "HEAD")

    assert current_base != prepared_base
    # The governed ORCH-2 runtime must stop at this comparison; the sandbox deliberately
    # performs no squash merge after detecting the movement.
    assert not (root / "packet.txt").exists()
