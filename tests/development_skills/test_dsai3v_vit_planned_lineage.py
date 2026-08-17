from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload
from ovc.development.skills.vit_routing import build_vit_lineage_record, validate_vit_lineage_record
from tools.ci.build_vit_planned_lineage import _compose_tree, _planned_changes


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def test_planned_target_bytes_freeze_pip_before_remote_pr_and_reproduce_tree() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        content = root / "content"
        repo.mkdir()
        content.mkdir()
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "vit@example.invalid")
        _git(repo, "config", "user.name", "VIT Test")
        (repo / "base.txt").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "base.txt")
        _git(repo, "commit", "-qm", "base")
        base = _git(repo, "rev-parse", "HEAD")
        base_tree = _git(repo, "rev-parse", "HEAD^{tree}")

        target_path = "records/development/receipt.json"
        target = content / target_path
        target.parent.mkdir(parents=True)
        target.write_text('{"status":"PASS"}\n', encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        changes = _planned_changes(repo, base, content, [{"path": target_path, "content_sha256": digest}])
        planned_tree = _compose_tree(repo, base_tree, changes)

        source_root = Path(__file__).resolve().parents[2]
        planned = subprocess.run(
            [
                sys.executable,
                str(source_root / "tools" / "ci" / "build_vit_planned_lineage.py"),
                "--repo", str(repo),
                "--base", base,
                "--content-root", str(content),
                "--targets-json", json.dumps([{"path": target_path, "content_sha256": digest}]),
                "--programme-id", "PROGRAMME",
                "--packet-id", "PACKET",
                "--plan-id", "PLAN",
                "--gate-id", "GATE",
                "--authority-sources-json", '["authority/source.json"]',
                "--security-envelope-id", "SECURITY-ENVELOPE",
            ],
            check=True,
            cwd=source_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        planned_output = json.loads(planned.stdout)
        assert planned_output["authority_manifest"]["security_envelope_id"] == "SECURITY-ENVELOPE"
        assert planned_output["expected_result_tree"] == planned_tree

        destination = repo / target_path
        destination.parent.mkdir(parents=True)
        destination.write_bytes(target.read_bytes())
        _git(repo, "add", target_path)
        _git(repo, "commit", "-qm", "materialise")
        actual_tree = _git(repo, "rev-parse", "HEAD^{tree}")
        assert planned_tree == actual_tree

        authority = IntegrationAuthorityManifest(
            plan_id="PLAN",
            packet_id="PACKET",
            gate_id="GATE",
            authority_class="AUTO_EXECUTABLE",
            authority_delta="NONE",
            authority_sources=("authority/source.json",),
            reserved_boundaries=(),
        )
        frontier = DependencyFrontier(
            dependencies=("dependency/source.json",),
            predecessor_requirement="PHYSICAL_MATERIALISATION_REQUIRED",
            owner_bindings=("OWNER",),
        )
        pip = PacketIntegrationPayload(
            programme_id="PROGRAMME",
            packet_id="PACKET",
            logical_changes=tuple(changes),
            authority_manifest=authority,
            dependency_frontier=frontier,
            completion_transition={"status": "PROPOSAL_CANDIDATE_READY"},
        )
        lineage = build_vit_lineage_record(
            programme_id="PROGRAMME",
            packet_id="PACKET",
            pip_identity_payload=pip.identity_payload(),
            train_generation_id="TRAIN",
            ordinal=1,
            predecessor_tree_sha=base_tree,
            result_tree_sha=planned_tree,
            apply_profile=REFERENCE_APPLY_PROFILE,
        )
        validated = validate_vit_lineage_record(lineage)
        assert validated.pip_id == pip.payload_id
        assert lineage["generation"]["predecessor_tree"]["tree_sha"] == base_tree
        assert lineage["generation"]["result_tree"]["tree_sha"] == actual_tree
