from __future__ import annotations

import ast
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import ovc.research_operations.p1cdi as p1cdi_package
from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p1cdi.identity import build_semantic_projection
from ovc.research_operations.p1cdi import reference as reference_module
from ovc.research_operations.p1cdi.reference import (
    ReferenceEngineError,
    assign_series_generation,
    stage_correspondence,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text()
)
REFERENCE_SOURCE = ROOT / "src/ovc/research_operations/p1cdi/reference.py"
GUARD_SOURCE = ROOT / "src/ovc/research_operations/p1cdi/series_root_guard.py"
INIT_SOURCE = ROOT / "src/ovc/research_operations/p1cdi/__init__.py"


def new_bundle(fields: dict | None = None, when: str | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=when or FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: copy.deepcopy(result[key]) for key in ("series", "generation", "projection")}


def stage_exact(bundle: dict, history: list[dict]) -> dict:
    return stage_correspondence(
        left_projection=bundle["projection"],
        right_projection=copy.deepcopy(bundle["projection"]),
        left_generation_record=bundle["generation"],
        right_generation_record=bundle["generation"],
        left_identity_history=history,
        right_identity_history=copy.deepcopy(history),
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
    )


def forge_later_generation_same_semantics(first: dict) -> dict:
    source_time = "2026-02-01T00:00:00Z"
    series_id = first["series"]["series_id"]
    projection_sha = first["projection"]["projection_sha256"]
    generation_id = "p1:generation:" + canonical_sha256(
        {
            "series_id": series_id,
            "projection_sha256": projection_sha,
            "source_first_valid_time": source_time,
        }
    )
    projection = build_semantic_projection(
        generation_id=generation_id,
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=copy.deepcopy(FIXTURE["identity_a"]),
    )
    generation = {
        "record_type": "P1EmpiricalDistinctionGeneration",
        "schema_version": "0.1",
        "authority_effect": "NONE",
        "generation_id": generation_id,
        "series_id": series_id,
        "profile_id": projection["profile_id"],
        "projection_sha256": projection["projection_sha256"],
        "source_first_valid_time": source_time,
        "immutable": True,
    }
    return {
        "series": copy.deepcopy(first["series"]),
        "generation": generation,
        "projection": projection,
    }


def lawful_successor(first: dict) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:remediation-5:successor",
    )


def test_correct_deterministic_series_id_never_proves_a_non_first_generation() -> None:
    first = new_bundle()
    forged = forge_later_generation_same_semantics(first)
    assert forged["series"]["series_id"] == first["series"]["series_id"]
    assert forged["generation"]["generation_id"] != first["series"]["first_generation_id"]
    with pytest.raises(
        ReferenceEngineError,
        match="does not prove first-generation binding|unchanged semantic rediscovery",
    ):
        stage_exact(forged, [existing(first), existing(forged)])


def test_correct_series_id_with_altered_first_generation_id_fails_closed() -> None:
    first = new_bundle()
    altered = existing(first)
    altered["series"]["first_generation_id"] = "p1:generation:forged-first"
    with pytest.raises(ReferenceEngineError, match="first-generation|conflicting canonical"):
        stage_exact(altered, [altered])


def test_missing_canonical_series_record_or_history_fails_closed() -> None:
    first = new_bundle()
    with pytest.raises(ReferenceEngineError, match="canonical series/root identity history"):
        stage_exact(first, [])
    generation_projection_only = {
        "generation": copy.deepcopy(first["generation"]),
        "projection": copy.deepcopy(first["projection"]),
    }
    with pytest.raises(ReferenceEngineError, match="identity bundle"):
        stage_exact(first, [generation_projection_only])


def test_forged_series_root_record_cannot_override_the_canonical_root() -> None:
    first = new_bundle()
    forged = forge_later_generation_same_semantics(first)
    forged["series"]["first_generation_id"] = forged["generation"]["generation_id"]
    with pytest.raises(ReferenceEngineError, match="conflicting canonical|first-generation"):
        stage_exact(forged, [existing(first), existing(forged)])


def test_exact_rediscovery_uses_existing_root_generation_and_canonical_history() -> None:
    first = new_bundle()
    rediscovered = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=copy.deepcopy(FIXTURE["identity_a"]),
        source_first_valid_time=FIXTURE["first_valid_time"],
        existing=[existing(first)],
    )
    assert rediscovered["resolution"] == "EXACT_REDISCOVERY"
    assert rediscovered["created"] is False
    assert rediscovered["generation"] == first["generation"]
    result = stage_exact(rediscovered, [existing(first)])
    assert result["semantic_identity"] == "EXACT"
    assert result["authority_effect"] == "NONE"


def test_successor_history_remains_required_exact_and_cross_series_safe() -> None:
    first = new_bundle()
    successor = lawful_successor(first)
    history = [existing(first), existing(successor)]
    assert stage_exact(successor, history)["semantic_identity"] == "EXACT"

    with pytest.raises(ReferenceEngineError, match="first-generation"):
        stage_exact(successor, [existing(successor)])

    corrupt = existing(first)
    corrupt["projection"]["identity_fields"]["structural_predicates"] = ["corrupt"]
    with pytest.raises(ReferenceEngineError):
        stage_exact(successor, [corrupt, existing(successor)])

    other = new_bundle({**copy.deepcopy(FIXTURE["identity_a"]), "unit_type": "OTHER_ROOT"})
    cross = existing(first)
    cross["series"] = copy.deepcopy(other["series"])
    with pytest.raises(ReferenceEngineError, match="series|identity"):
        stage_exact(successor, [cross, existing(successor)])


def test_runtime_exports_have_one_guarded_admission_callable_and_no_wrapped_original() -> None:
    direct = reference_module.stage_correspondence
    package = p1cdi_package.stage_correspondence
    assert direct is package is stage_correspondence
    assert not hasattr(direct, "__wrapped__")
    assert [name for name, value in vars(reference_module).items() if value is direct] == [
        "stage_correspondence"
    ]


def test_static_source_has_no_wrapper_installer_saved_original_or_second_stage() -> None:
    reference_text = REFERENCE_SOURCE.read_text(encoding="utf-8")
    guard_text = GUARD_SOURCE.read_text(encoding="utf-8")
    init_text = INIT_SOURCE.read_text(encoding="utf-8")
    reference_tree = ast.parse(reference_text)
    assert sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "stage_correspondence"
        for node in ast.walk(reference_tree)
    ) == 1
    assert "functools" not in guard_text
    assert "wraps" not in guard_text
    assert "__wrapped__" not in guard_text
    assert "install_reference_series_root_guard" not in guard_text
    assert "install_reference_series_root_guard" not in init_text
    assert "original = reference_module.stage_correspondence" not in guard_text
    assert "reference_module.stage_correspondence =" not in guard_text


_IMPORT_PERMUTATION_SCRIPT = r'''
import copy
import importlib
import json
from pathlib import Path
import sys

root = Path.cwd()
fixture = json.loads((root / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text())
mode = sys.argv[1]

if mode == "package_first":
    package = importlib.import_module("ovc.research_operations.p1cdi")
    alias_before = package.stage_correspondence
    reference = importlib.import_module("ovc.research_operations.p1cdi.reference")
    alias_after = reference.stage_correspondence
else:
    reference = importlib.import_module("ovc.research_operations.p1cdi.reference")
    alias_before = reference.stage_correspondence
    package = importlib.import_module("ovc.research_operations.p1cdi")
    alias_after = package.stage_correspondence

first = reference.assign_series_generation(
    owner_semantic_binding=fixture["owner_semantic_binding"],
    identity_fields=fixture["identity_a"],
    source_first_valid_time=fixture["first_valid_time"],
)
history = [{key: copy.deepcopy(first[key]) for key in ("series", "generation", "projection")}]

aliases = [alias_before, alias_after, reference.stage_correspondence, package.stage_correspondence]
if mode == "reload":
    old_direct = reference.stage_correspondence
    old_package = package.stage_correspondence
    importlib.reload(reference)
    new_direct = reference.stage_correspondence
    aliases.extend([old_direct, old_package, new_direct])
    importlib.reload(package)
    aliases.append(package.stage_correspondence)

for alias in aliases:
    assert not hasattr(alias, "__wrapped__")
    try:
        alias(
            left_projection=first["projection"],
            right_projection=copy.deepcopy(first["projection"]),
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=fixture["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
        )
    except reference.ReferenceEngineError as exc:
        assert "canonical series/root identity history" in str(exc)
    else:
        raise AssertionError("unguarded alias accepted correspondence without canonical root proof")
    result = alias(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        left_identity_history=history,
        right_identity_history=copy.deepcopy(history),
        planes=fixture["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
    )
    assert result["semantic_identity"] == "EXACT"
    assert result["authority_effect"] == "NONE"
'''


@pytest.mark.parametrize("mode", ["reference_first", "package_first", "reload"])
def test_direct_package_alias_and_reload_import_order_permutations_are_guarded(mode: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT)])
    subprocess.run(
        [sys.executable, "-c", _IMPORT_PERMUTATION_SCRIPT, mode],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
