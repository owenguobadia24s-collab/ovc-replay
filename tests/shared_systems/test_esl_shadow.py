from __future__ import annotations

from dataclasses import replace
import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from ovc.development.identity import canonical_json_bytes
from ovc.shared_systems.esl_shadow import (
    ESLShadowError,
    ESLShadowSurfaceBinding,
    ESLSharedSystemsConsumptionManifest,
    adapt_esl_surface,
    compare_esl_reference,
    evaluate_esl_adapter_complexity,
    map_esl_evidence_frontier,
    unwrap_esl_surface,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / (
    "fixtures/shared_systems/esl_shadow/"
    "SHSI_WP9_ESL_HISTORICAL_SHADOW_FIXTURE_v0_1.json"
)
BUDGET_PATH = ROOT / (
    "registries/implementation/shared_systems_v0_1/"
    "SHSI_PILOT_ACCEPTANCE_BUDGET_v0_1.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


FIXTURE = load(FIXTURE_PATH)


def source(role: str) -> dict:
    item = next(row for row in FIXTURE["sources"] if row["role"] == role)
    return load(ROOT / item["path"])


def bindings() -> tuple[ESLShadowSurfaceBinding, ...]:
    roles = {
        "PROFILE": "ESL_PARTIAL_OCCURRENCE",
        "EVIDENCE_FRONTIER": "ESL_PARTIAL_OCCURRENCE",
        "LINEAGE": "C2E_IDENTITY",
        "INTERFACE": "SFC_IDENTITY",
        "READ_MODEL": "ESL_READ_MODEL",
    }
    return tuple(
        ESLShadowSurfaceBinding(
            f"SHSI-WP9-ESL-{surface}-v0.1",
            surface,
            next(row["path"] for row in FIXTURE["sources"] if row["role"] == role),
            f"ovc://shared-systems/esl/{surface.casefold()}/v0.1",
        )
        for surface, role in roles.items()
    )


def test_esl_current_and_historical_records_are_exact_git_blobs() -> None:
    for item in FIXTURE["sources"]:
        raw = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert len(raw) == item["byte_count"]
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]], cwd=ROOT,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"], item["path"]


def test_manifest_is_shadow_only_and_cannot_activate_c3_or_expand_sources() -> None:
    state_item = next(row for row in FIXTURE["sources"] if row["role"] == "CURRENT_STATE")
    manifest = ESLSharedSystemsConsumptionManifest(
        "SHSI-WP9-ESL-CONSUME-v0.1",
        FIXTURE["programme_id"],
        FIXTURE["consumer_generation"],
        state_item["path"],
        state_item["git_blob_sha"],
        "SHSI-WP8-RO-DMRP-SHADOW-v0.1",
        tuple(FIXTURE["expected"]["surfaces"]),
        FIXTURE["c3_activation_state"],
    )
    assert manifest.status == "SHADOW_ONLY" and manifest.authority_effect == "NONE"
    assert not manifest.current_binding_changed and manifest.writes_performed == ()
    with pytest.raises(ESLShadowError, match="C3_ACTIVATION"):
        replace(manifest, c3_activation_state="ACTIVE")
    with pytest.raises(ESLShadowError, match="SOURCE_OR_PROMOTION"):
        replace(manifest, source_expansion=("NEW_SOURCE",))
    with pytest.raises(ESLShadowError, match="SOURCE_OR_PROMOTION"):
        replace(manifest, semantic_promotions=("FAMILY",))


def test_frontier_mapping_preserves_optional_missing_without_poisoning_base() -> None:
    occurrence = source("ESL_PARTIAL_OCCURRENCE")
    mapped = map_esl_evidence_frontier("SHSI-WP9-ESL-FRONTIER-v0.1", occurrence)
    assert mapped.status == "READY"
    assert mapped.required_missing_refs == ()
    assert mapped.optional_missing_refs == ("C2E.EP.1",)
    assert mapped.base_structural_status == "LAWFUL_BASE_PRESERVED"
    assert mapped.declared_loss_fields == ()
    assert mapped.shared_frontier.missing_entries == ("C2E.EP.1",)
    assert mapped.shared_frontier.comparability_domain_ref == "GBPUSD.BID.15M.v1"

    unavailable = copy.deepcopy(occurrence)
    unavailable["dependency_refs"][0]["evidence_state"] = "MISSING"
    unavailable["dependency_refs"][0]["first_valid_time"] = None
    missing = map_esl_evidence_frontier("SHSI-WP9-ESL-REQUIRED-MISSING", unavailable)
    assert missing.status == "NOT_EVALUABLE"
    assert missing.required_missing_refs == ("C2.OBS.1",)
    assert "REQUIRED_DEPENDENCY_MISSING" in missing.shared_frontier.reason_codes


def test_all_surfaces_round_trip_and_historical_identities_do_not_change() -> None:
    by_surface = {row.surface: row for row in bindings()}
    sources = {
        "PROFILE": source("ESL_PARTIAL_OCCURRENCE"),
        "EVIDENCE_FRONTIER": source("ESL_PARTIAL_OCCURRENCE")["evidence_frontier"],
        "LINEAGE": source("C2E_IDENTITY")["lineage"],
        "INTERFACE": source("SFC_IDENTITY"),
        "READ_MODEL": source("ESL_READ_MODEL"),
    }
    for surface, record in sources.items():
        wrapped = adapt_esl_surface(by_surface[surface], record)
        shadow = unwrap_esl_surface(by_surface[surface], wrapped)
        assert shadow == record and wrapped["declared_loss_fields"] == []
        assert compare_esl_reference(
            f"SHSI-WP9-{surface}-COMPARE", by_surface[surface].source_ref, record, shadow
        ).status == "PASS"
    for role in ("C2E_IDENTITY", "SFC_IDENTITY", "C2_5_IDENTITY_BLOCKED"):
        record = source(role)
        binding = by_surface["INTERFACE"]
        shadow = unwrap_esl_surface(binding, adapt_esl_surface(binding, record))
        assert compare_esl_reference(role, role, record, shadow).status == "PASS"
    with pytest.raises(ESLShadowError, match="NON_IDENTITY_MAPPING"):
        replace(bindings()[0], field_mapping=(("facets", "profile"),))
    with pytest.raises(ESLShadowError, match="SEMANTIC_FABRICATION"):
        replace(bindings()[0], semantic_inventions=("family",))


def test_no_family_and_partial_states_remain_non_promotional() -> None:
    no_family = source("SFC_NO_FAMILY")
    assert no_family["evidence_status"] == "NO_STABLE_FAMILY"
    assert no_family["families"] == []
    assert no_family["authority_state"] == "INACTIVE_CONFORMANCE_ONLY"
    c3 = source("C3_ACTIVATION_DENY")
    assert c3 == {
        "activation_state": "NONE", "bindings": [], "authority": "NONE",
        "mutable": False,
        "note": "Deny-by-default. ESLI-WP4 cannot populate active vocabulary bindings.",
        "schema": "ovc-esl-c3-vocabulary-activation/v1",
    }
    c25 = source("C2_5_IDENTITY_BLOCKED")
    assert c25["status"] == "BLOCKED"
    assert c25["authority"]["draft_contract_or_shadow"] == "DENIED_BY_OPERATOR_BLOCK"


def test_adapter_complexity_is_inside_frozen_budget() -> None:
    import ovc.shared_systems.esl_shadow as module

    rows = bindings()
    role_by_surface = {
        "PROFILE": "ESL_PARTIAL_OCCURRENCE", "EVIDENCE_FRONTIER": "ESL_PARTIAL_OCCURRENCE",
        "LINEAGE": "C2E_IDENTITY", "INTERFACE": "SFC_IDENTITY", "READ_MODEL": "ESL_READ_MODEL",
    }
    byte_delta = 0
    for row in rows:
        raw = source(role_by_surface[row.surface])
        wrapped = adapt_esl_surface(row, raw)
        byte_delta += max(0, len(canonical_json_bytes(wrapped)) - len(canonical_json_bytes(raw)))
    source_text = Path(inspect.getsourcefile(module.adapt_esl_surface)).read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "adapt_esl_surface")
    code_lines = node.end_lineno - node.lineno + 1
    budget = load(BUDGET_PATH)["pilot_acceptance_budget"]
    ledger = evaluate_esl_adapter_complexity(
        "SHSI-WP9-ESL-LEDGER-v0.1", rows, budget=budget,
        code_surface_lines=code_lines, artifact_byte_delta=byte_delta,
    )
    assert ledger.status == "PASS"
    assert ledger.active_adapter_count == 0 and ledger.adapter_mapping_count == 1
    blocked = evaluate_esl_adapter_complexity(
        "SHSI-WP9-ESL-LEDGER-BAD", rows, budget=budget,
        code_surface_lines=46, artifact_byte_delta=byte_delta,
    )
    assert blocked.status == "BLOCK"
    assert blocked.exceeded_dimensions == ("ADAPTER_CODE_SURFACE_LINES",)


def test_wp9_schema_declares_all_shadow_objects() -> None:
    schema = load(ROOT / "schemas/shared_systems/esl_shadow_consumer_v0_1.schema.json")
    assert {
        "ESLSharedSystemsConsumptionManifest", "ESLShadowSurfaceBinding",
        "ESLEvidenceFrontierMapping", "ESLReferenceComparison",
        "ESLAdapterComplexityLedger",
    } <= set(schema["$defs"])
