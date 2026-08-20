from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_BASE = {
    "scripts/research_operations/run_p1cdii_wp4_reference.py": "4900097a6b7e9b5555868c76c3eff6be7e5aee1c6c8fd3574a4958aa9cff1d16",
    "src/ovc/research_operations/p1cdi/__init__.py": "011cc5f36a7820e068aba82b10bc9f8fba324cd4a2aa60e2b89db7fed90055d2",
    "src/ovc/research_operations/p1cdi/reference.py": "2b52408b6a74c9cd9e06ea1ece78faea3d1ba350c8dea149ddd817275c808650",
    "src/ovc/research_operations/p1cdi/series_root_guard.py": "4e58de242f75cc9a6cae3340ae3472156845ffcb8655f0b547a88d9d4d005b2b",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_reference.py": "b26f0de109fdead800ff80dd8136af9fc755b30edf1bd37800236295fa51548a",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_1.py": "599de9cf1eaa60e978767d1b5d0930a7fae59422b2308f9e21f4c72b5b891d38",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_2.py": "8941b4dd5e1dfa90a32858dff451c69a65bfb4c83e9d50cae62ef6f348f99bbc",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_3.py": "4f2bd7b0ee7ab102098c7c8e8f2372dcf5a245bca02e09813b6dc65bed0f2c4a",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_4.py": "24429dcfbe4a4b80c4b005a555bae48dca723b83adf6f9978507b41e0c52d0dd",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_5.py": "8f37f0984f16bcc49a0f6b9778f7cc4fd0774559aeb7fd6e54e51fa20f601745",
}

EXPECTED_FINAL = {
    "scripts/research_operations/run_p1cdii_wp4_reference.py": "2eae2c97b8c5ef55d22ba1a5c069b1ea8e6cc03437618208c5f86c5ffe97bcbc",
    "src/ovc/research_operations/p1cdi/__init__.py": "4dee0be265634d5857332f3dee48609098564714434238b15268d88cca16fe95",
    "src/ovc/research_operations/p1cdi/reference.py": "2a82d0b8072ed4820cfb24dd8d624e9dc1ea7c7ec069341f1a308c61fddf1530",
    "src/ovc/research_operations/p1cdi/series_root_guard.py": "bef52e846da7bfc6495c2bb99b302168ec5c5a08289a258a89cf882b90156c1a",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_reference.py": "363b6b7b15de8164c8f4cd07b7c12dd11449f1a4475472065b899fac0b6da6fc",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_1.py": "9a0418fbbfe3599ea865ba9e2a37eb3af2e3fedb005661b201c9165b029c0bf3",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_2.py": "baba611cbfb3d7f1b6e74ddb785fdddb6a7e4c362ba67694bf3d09eaed472c62",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_3.py": "49658c44da188d1e493c6b2ff32441fd760a130a0fbf6b2af89d89b5dd78c9b7",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_4.py": "2be6337959759b98259625864f865fa191f820a26812356bfcc0c68c3c95890b",
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_5.py": "8f37f0984f16bcc49a0f6b9778f7cc4fd0774559aeb7fd6e54e51fa20f601745",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hashes(expected: dict[str, str], phase: str) -> None:
    observed = {path: sha256(ROOT / path) for path in expected}
    if observed != expected:
        raise RuntimeError(f"{phase} hash mismatch: {observed}")


def insert_histories(path: str, mapping: dict[int, tuple[str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    calls = {
        node.lineno: node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "stage_correspondence"
    }
    if not set(mapping).issubset(calls):
        raise RuntimeError(f"stage call mapping mismatch for {path}: {sorted(set(mapping) - set(calls))}")
    for start in sorted(mapping, reverse=True):
        node = calls[start]
        keywords = {item.arg for item in node.keywords}
        if "left_identity_history" in keywords or "right_identity_history" in keywords:
            raise RuntimeError(f"history already present for {path}:{start}")
        closing_index = node.end_lineno - 1
        closing = lines[closing_index]
        indent = closing[: len(closing) - len(closing.lstrip())] + "    "
        left, right = mapping[start]
        lines[closing_index:closing_index] = [
            f"{indent}left_identity_history={left},\n",
            f"{indent}right_identity_history={right},\n",
        ]
    target.write_text("".join(lines), encoding="utf-8")


require_hashes(EXPECTED_BASE, "base")

(ROOT / "src/ovc/research_operations/p1cdi/series_root_guard.py").write_text(
    '''from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def validate_correspondence_series_root(
    reference_module: Any,
    *,
    projection: Mapping[str, Any],
    generation: Mapping[str, Any] | None,
    identity_history: Sequence[Mapping[str, Any]],
) -> None:
    """Prove canonical Series/root reachability before correspondence admission.

    A deterministic Series identifier is identity evidence only.  It never proves that
    the generation being staged is ``Series.first_generation_id``.  Every admission
    therefore requires an exact, reconciled identity history containing both the
    canonical Series root and the generation/projection currently being staged.
    """

    validated_generation = reference_module._validate_projection_generation_binding(
        projection, generation
    )
    canonical_projection = reference_module._validate_projection(projection)

    if not identity_history:
        raise reference_module.ReferenceEngineError(
            "correspondence requires exact canonical series/root identity history"
        )

    try:
        reconciled = reference_module._reconcile_identity_bundles(identity_history)
    except reference_module.ReferenceEngineError as exc:
        if str(exc) == "same series identity has conflicting canonical series content":
            raise reference_module.ReferenceEngineError(
                "series first-generation binding conflicts across canonical series/root identity history"
            ) from exc
        raise

    current_matches = [
        bundle
        for bundle in reconciled
        if bundle[1]["generation_id"] == canonical_projection["generation_id"]
    ]
    if len(current_matches) != 1:
        raise reference_module.ReferenceEngineError(
            "correspondence generation is unavailable from canonical series/root identity history"
        )

    series, historical_generation, historical_projection = current_matches[0]
    if series["series_id"] != validated_generation["series_id"]:
        raise reference_module.ReferenceEngineError(
            "correspondence generation crosses canonical series identity"
        )
    if reference_module._canonical_bytes(historical_generation) != reference_module._canonical_bytes(
        validated_generation
    ):
        raise reference_module.ReferenceEngineError(
            "correspondence generation differs from canonical identity history"
        )
    if reference_module._canonical_bytes(historical_projection) != reference_module._canonical_bytes(
        canonical_projection
    ):
        raise reference_module.ReferenceEngineError(
            "correspondence projection differs from canonical identity history"
        )

    first_generation_id = series["first_generation_id"]
    root_matches = [
        bundle
        for bundle in reconciled
        if bundle[1]["generation_id"] == first_generation_id
    ]
    if len(root_matches) != 1:
        raise reference_module.ReferenceEngineError(
            "series first-generation binding is unavailable or unverifiable"
        )
    root_series, root_generation, root_projection = root_matches[0]
    if (
        root_series["series_id"] != series["series_id"]
        or root_generation["series_id"] != series["series_id"]
    ):
        raise reference_module.ReferenceEngineError(
            "series first-generation binding crosses series identity"
        )
    if reference_module._canonical_bytes(root_series) != reference_module._canonical_bytes(series):
        raise reference_module.ReferenceEngineError(
            "series root record differs from canonical current-series record"
        )

    expected_root_series_id = (
        "p1:series:"
        + reference_module.canonical_sha256(
            {
                "owner": root_projection["owner_semantic_binding"],
                "projection_sha256": root_projection["projection_sha256"],
            }
        )
    )
    if series["series_id"] != expected_root_series_id:
        raise reference_module.ReferenceEngineError(
            "series first-generation deterministic identity mismatch"
        )

    current_direct_series_id = (
        "p1:series:"
        + reference_module.canonical_sha256(
            {
                "owner": canonical_projection["owner_semantic_binding"],
                "projection_sha256": canonical_projection["projection_sha256"],
            }
        )
    )
    current_generation_id = validated_generation["generation_id"]
    if validated_generation["series_id"] == current_direct_series_id:
        if first_generation_id != current_generation_id:
            raise reference_module.ReferenceEngineError(
                "deterministic series identity does not prove first-generation binding; "
                "exact rediscovery must resolve to the canonical root generation"
            )
    elif first_generation_id == current_generation_id:
        raise reference_module.ReferenceEngineError(
            "first-generation series identity does not bind its canonical projection"
        )

    if (
        reference_module.exact_semantic_equal(canonical_projection, root_projection)
        and current_generation_id != first_generation_id
    ):
        raise reference_module.ReferenceEngineError(
            "unchanged semantic rediscovery must resolve to the canonical first generation"
        )
''',
    encoding="utf-8",
)

reference_path = ROOT / "src/ovc/research_operations/p1cdi/reference.py"
reference_text = reference_path.read_text(encoding="utf-8")
reference_text = reference_text.replace(
    "import json\nfrom pathlib import Path",
    "import json\nfrom pathlib import Path\nimport sys",
)
identity_import = '''from .identity import (
    PROFILE_ID,
    build_semantic_projection,
    exact_semantic_equal,
    projection_bytes,
)
'''
if reference_text.count(identity_import) != 1:
    raise RuntimeError("identity import anchor mismatch")
reference_text = reference_text.replace(
    identity_import,
    identity_import + "from .series_root_guard import validate_correspondence_series_root\n",
)
old_signature = '''    independence_evidence: Sequence[Mapping[str, Any]] = (),
    as_of_time: str | None = None,
) -> dict[str, Any]:
    """Stage plane-local correspondence without transferring truth across planes."""

'''
new_signature = '''    independence_evidence: Sequence[Mapping[str, Any]] = (),
    as_of_time: str | None = None,
    left_identity_history: Sequence[Mapping[str, Any]] = (),
    right_identity_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Stage plane-local correspondence without transferring truth across planes."""

    reference_module = sys.modules[__name__]
    validate_correspondence_series_root(
        reference_module,
        projection=left_projection,
        generation=left_generation_record,
        identity_history=left_identity_history,
    )
    validate_correspondence_series_root(
        reference_module,
        projection=right_projection,
        generation=right_generation_record,
        identity_history=right_identity_history,
    )

'''
if reference_text.count(old_signature) != 1:
    raise RuntimeError("stage signature anchor mismatch")
reference_path.write_text(reference_text.replace(old_signature, new_signature), encoding="utf-8")

init_path = ROOT / "src/ovc/research_operations/p1cdi/__init__.py"
init_text = init_path.read_text(encoding="utf-8")
old_init = '''from .intake import build_intake_envelope, classify_exact_intake
from . import reference as _reference
from .series_root_guard import install_reference_series_root_guard

install_reference_series_root_guard(_reference)

from .reference import (
'''
new_init = '''from .intake import build_intake_envelope, classify_exact_intake
from .reference import (
'''
if init_text.count(old_init) != 1:
    raise RuntimeError("package wrapper-install anchor mismatch")
init_path.write_text(init_text.replace(old_init, new_init), encoding="utf-8")

insert_histories(
    "tests/research_operations/p1cdi/test_p1cdii_wp4_reference.py",
    {
        120: ("[existing(first)]", "[existing(first)]"),
        141: ("[existing(first)]", "[existing(changed_bundle)]"),
    },
)
insert_histories(
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_1.py",
    {
        248: ("[existing(first)]", "[existing(first)]"),
        260: ("[existing(first)]", "[existing(first)]"),
        272: ("[existing(first)]", "[existing(first)]"),
        347: ("[existing(first)]", "[existing(changed)]"),
    },
)
insert_histories(
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_2.py",
    {
        95: ("[existing(first)]", "[existing(right)]"),
        137: ("[existing(first)]", "[existing(first)]"),
        156: ("[existing(first)]", "[existing(first)]"),
        185: ("[existing(first)]", "[existing(first)]"),
        193: ("[existing(first)]", "[existing(first)]"),
        223: ("[existing(first)]", "[existing(first)]"),
        242: ("[existing(first)]", "[existing(first)]"),
        260: ("[existing(first)]", "[existing(first)]"),
        291: ("[existing(first)]", "[existing(first)]"),
        308: ("[existing(first)]", "[existing(first)]"),
        372: ("[existing(first)]", "[existing(first)]"),
        388: ("[existing(first)]", "[existing(first)]"),
        409: ("[existing(first)]", "[existing(first)]"),
    },
)
insert_histories(
    "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_3.py",
    {
        74: ("[existing(first)]", "[existing(first)]"),
        115: ("[existing(first)]", "[existing(first)]"),
        130: ("[existing(first)]", "[existing(first)]"),
        153: ("[existing(first)]", "[existing(first)]"),
    },
)
insert_histories(
    "scripts/research_operations/run_p1cdii_wp4_reference.py",
    {61: ("[identity_bundle(first)]", "[identity_bundle(first)]")},
)
runner_path = ROOT / "scripts/research_operations/run_p1cdii_wp4_reference.py"
runner_text = runner_path.read_text(encoding="utf-8")
runner_anchor = '''FIXTURE_PATH = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json"


def rebuild() -> bytes:
'''
runner_replacement = '''FIXTURE_PATH = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json"


def identity_bundle(result: dict) -> dict:
    return {key: result[key] for key in ("series", "generation", "projection")}


def rebuild() -> bytes:
'''
if runner_text.count(runner_anchor) != 1:
    raise RuntimeError("runner identity helper anchor mismatch")
runner_path.write_text(runner_text.replace(runner_anchor, runner_replacement), encoding="utf-8")

rem4_path = ROOT / "tests/research_operations/p1cdi/test_p1cdii_wp4_remediation_4.py"
rem4_text = rem4_path.read_text(encoding="utf-8")
old_rem4 = '''def test_direct_deterministic_first_generation_remains_valid_without_history_reconstruction() -> None:
    first = new_bundle()
    result = stage_partial(first)
    assert result["semantic_identity"] == "EXACT"
    assert result["record"] is None
    assert result["executability"] == "BLOCKED_UNRESOLVED_PLANES"
'''
new_rem4 = '''def test_direct_deterministic_first_generation_requires_and_accepts_canonical_root_history() -> None:
    first = new_bundle()
    with pytest.raises(ReferenceEngineError, match="canonical series/root identity history"):
        stage_partial(first)
    history = [existing(first)]
    result = stage_partial(first, left_history=history, right_history=history)
    assert result["semantic_identity"] == "EXACT"
    assert result["record"] is None
    assert result["executability"] == "BLOCKED_UNRESOLVED_PLANES"
'''
if rem4_text.count(old_rem4) != 1:
    raise RuntimeError("remediation-4 direct-root regression anchor mismatch")
rem4_path.write_text(rem4_text.replace(old_rem4, new_rem4), encoding="utf-8")

require_hashes(EXPECTED_FINAL, "final")
print("P1CDII_REMEDIATION_5_APPLY=PASS")
