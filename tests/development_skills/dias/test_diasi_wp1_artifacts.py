from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
WP1 = ROOT / "docs/programmes/dias-v0-1/wp1"
SOURCE = ROOT / "src/ovc/development/skills/dias.py"
SCHEMA = ROOT / "schemas/development/dias/diasi_common_substrate_v0_1.schema.json"
CONTRACT = ROOT / "contracts/development/dias/DIASI_COMMON_SUBSTRATE_CONTRACT_v0_1.md"
CORPUS = ROOT / "fixtures/development_skills/dias/DIASI_WP1_ADVERSARIAL_CLASSIFIER_CORPUS_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_identity_bearing_wp1_records_are_canonical() -> None:
    authority = load(WP1 / "DIASI_WP1_AUTHORITY_ENVELOPE.json")
    dependencies = load(WP1 / "DIASI_WP1_TEST_DEPENDENCY_MANIFEST.json")
    projection = load(WP1 / "DIASI_WP1_CURRENT_EXECUTION_PROJECTION_SHADOW.json")
    assert canonical_sha256(authority["payload"], role="programme-authority-envelope/v1") == authority["envelope_id"]
    assert canonical_sha256(dependencies["payload"], role="test-dependency-manifest/v1") == dependencies["manifest_id"]
    assert canonical_sha256(projection["payload"], role="current-execution-projection/v1") == projection["projection_id"]


def test_projection_binds_wp0_physical_completion_without_becoming_authority() -> None:
    projection = load(WP1 / "DIASI_WP1_CURRENT_EXECUTION_PROJECTION_SHADOW.json")["payload"]
    facts = {fact["fact_key"]: fact for fact in projection["resolved_facts"]}
    assert facts["wp0_physical_completion"]["value"] is True
    assert facts["wp0_physical_completion"]["controlling_source_blobs"] == [
        "acaedc95097b844436a4a7d9e62ec165fde2ffbd40d2e047c816b44104a22b6b"
    ]
    assert projection["shadow_only"] is True
    assert projection["derivative"] is True
    assert projection["authority_effect"] == "NONE"


def test_contract_schema_and_corpus_are_frozen_and_parseable() -> None:
    assert "creates no scheduler" in CONTRACT.read_text(encoding="utf-8")
    schema = load(SCHEMA)
    corpus = load(CORPUS)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["$defs"]) == {
        "sha",
        "nonEmpty",
        "authorityEnvelope",
        "consequenceClassification",
        "testDependencyManifest",
        "currentExecutionProjection",
    }
    assert len(corpus["cases"]) == 12
    assert len(corpus["negative_cases"]) == 3
    assert corpus["authority_effect"] == "NONE"


def test_common_substrate_has_no_runtime_or_io_surface() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imports & {"asyncio", "subprocess", "threading", "multiprocessing", "socket", "requests", "urllib"}
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"write_text", "write_bytes", "open", "connect", "send", "start"}


def test_conflict_free_review_tool_is_executable_in_fresh_process() -> None:
    tool = ROOT / "tools/ci/diasi_algorithmic_review.py"
    result = subprocess.run(
        ["python", str(tool), "--repo", str(ROOT), "--subject-head", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT)))},
    )
    review = json.loads(result.stdout)
    assert review["decision"] == "PASS"
    assert review["external_human_or_model_claim"] is False
    assert review["classifier"]["authority_dominance_checks"] == 28
    assert review["owner_precedence"]["recency_override_rejected"] is True
