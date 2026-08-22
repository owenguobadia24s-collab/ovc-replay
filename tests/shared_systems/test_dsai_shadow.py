from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from ovc.development.identity import canonical_json_bytes
from ovc.development.skills.security import (
    build_tool_request,
    decide_tool_request,
    resolve_security_envelope,
)
from ovc.shared_systems.dsai_shadow import (
    DSAIShadowError,
    DSAIShadowExecutionContext,
    DSAISharedSystemsConsumptionManifest,
    DSAISurfaceAdapterBinding,
    adapt_dsai_surface,
    compare_dsai_dual_run,
    compare_security_refusal,
    evaluate_adapter_complexity,
    unwrap_dsai_surface,
)
from ovc.shared_systems.foundation import SECURITY_FACTORS, SecurityRequest, decide_security


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures/shared_systems/dsai_shadow/SHSI_WP7_DSAI_HISTORICAL_SHADOW_FIXTURE_v0_1.json"
BUDGET_PATH = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PILOT_ACCEPTANCE_BUDGET_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


FIXTURE = load(FIXTURE_PATH)


def sources() -> list[tuple[dict, dict]]:
    return [(item, load(ROOT / item["path"])) for item in FIXTURE["sources"]]


def bindings() -> tuple[DSAISurfaceAdapterBinding, ...]:
    return tuple(
        DSAISurfaceAdapterBinding(
            f"SHSI-WP7-DSAI-{item['surface']}-WRAP-v0.1",
            item["surface"],
            item["source_schema"],
            f"ovc://shared-systems/dsai/{item['surface'].casefold()}/v0.1",
        )
        for item in FIXTURE["sources"]
    )


def test_historical_sources_are_exact_lawful_git_blobs() -> None:
    assert FIXTURE["current_binding_changed"] is False
    assert FIXTURE["writes_performed"] == []
    for item, _ in sources():
        raw = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"]
    security = FIXTURE["security_fixture"]
    assert hashlib.sha256((ROOT / security["path"]).read_bytes()).hexdigest() == security["sha256"]


def test_consumption_manifest_and_context_are_shadow_only() -> None:
    manifest = DSAISharedSystemsConsumptionManifest(
        "SHSI-WP7-DSAI-CONSUME-v0.1",
        "OVC-DSAI-v0.1",
        "OVC_DSAI_STATE_v0_31",
        "OVC-SHARED-SYSTEMS-v0.1",
        "SHSI-WP6-FOUNDATION-v0.1",
        ("ENVIRONMENT", "RUN", "ASSURANCE", "RECEIPT", "CURRENTNESS"),
        "registries/implementation/dsai/OVC_DSAI_STATE_v0_31.json",
        "4c1d5f1faf0752b34e63b70c078f2fb0691cb4f3",
    )
    context = DSAIShadowExecutionContext(
        "SHSI-WP7-DSAI-CONTEXT-v0.1",
        manifest.manifest_id,
        "SHSI-WP7-RESOLUTION-MANIFEST-v0.1",
        manifest.consumer_generation,
        tuple(item["git_blob_sha"] for item in FIXTURE["sources"]),
    )
    assert manifest.status == context.status == "SHADOW_ONLY"
    assert not manifest.current_binding_changed and context.writes_performed == ()
    with pytest.raises(DSAIShadowError, match="CURRENT_BINDING_CHANGE"):
        replace(manifest, current_binding_changed=True)
    with pytest.raises(DSAIShadowError, match="WRITE_OR_ACTIVATION"):
        replace(context, writes_performed=("WRITE",))


def test_all_five_surface_wrappers_round_trip_exact_source_identity() -> None:
    by_surface = {item.surface: item for item in bindings()}
    assert set(by_surface) == {item["surface"] for item in FIXTURE["sources"]}
    for item, source in sources():
        binding = by_surface[item["surface"]]
        wrapped = adapt_dsai_surface(binding, source)
        assert unwrap_dsai_surface(binding, wrapped) == source
        assert wrapped["source_logical_sha256"] != wrapped["logical_id"]
        assert wrapped["writes_performed"] == [] and wrapped["authority_effect"] == "NONE"
    with pytest.raises(DSAIShadowError, match="NON_IDENTITY_MAPPING"):
        replace(bindings()[0], field_mapping=(("status", "authority"),))
    with pytest.raises(DSAIShadowError, match="SEMANTIC_FABRICATION"):
        replace(bindings()[0], semantic_inventions=("authority",))


def test_historical_dual_run_agrees_on_every_mandatory_semantic() -> None:
    by_surface = {item.surface: item for item in bindings()}
    for item, source in sources():
        shadow = unwrap_dsai_surface(by_surface[item["surface"]], adapt_dsai_surface(by_surface[item["surface"]], source))
        comparison = compare_dsai_dual_run(
            f"COMPARE.{item['surface']}",
            item["path"],
            source,
            shadow,
            mandatory_semantic_paths=item["mandatory_paths"],
        )
        assert comparison.status == "PASS"
        assert comparison.divergent_paths == ()
    changed = dict(sources()[0][1])
    changed["status"] = "ILLEGAL_DIFFERENCE"
    blocked = compare_dsai_dual_run(
        "COMPARE.BAD",
        FIXTURE["sources"][0]["path"],
        sources()[0][1],
        changed,
        mandatory_semantic_paths=("status",),
    )
    assert blocked.status == "BLOCK" and blocked.divergent_paths == ("status",)
    with pytest.raises(DSAIShadowError, match="EXPECTED_MANDATORY_DIVERGENCE"):
        replace(blocked, expected_divergence_paths=("status",))


def test_dsai_and_shared_security_refusals_are_exact_parity() -> None:
    envelope = resolve_security_envelope(
        skill_id="OVC-SKILL-SHADOW",
        capability_ids=("READ",),
        allowed_semantic_actions=("READ_FILE",),
        read_prefixes=("src",),
    )
    request = build_tool_request(action="VALIDATION_READ", resource_class="VALIDATION")
    dsai = decide_tool_request(envelope, request)
    shared_request = SecurityRequest(
        "SHSI.REQUEST.1", "DSAI.PRINCIPAL.1", "VALIDATION.PROTECTED", "CAP.READ",
        "PERMISSION.READ", "AUTHORITY.NONE", "SCOPE.SHADOW", "POLICY.DENY", "VALIDATION",
    )
    factors = {name: True for name in SECURITY_FACTORS}
    factors["runtime_policy_allows"] = False
    shared = decide_security(
        "SHSI.DECISION.1", shared_request, factor_results=factors, dsai_decision_ref=dsai["decision_id"]
    )
    parity = compare_security_refusal(
        "PARITY.1", "VALIDATION_READ", dsai_decision=dsai, shared_decision=shared
    )
    assert parity.status == "PASS"
    false_allow = compare_security_refusal(
        "PARITY.BAD", "VALIDATION_READ", dsai_decision={**dsai, "decision": "ALLOW"}, shared_decision=shared
    )
    assert false_allow.status == "BLOCK"


def test_adapter_complexity_and_overhead_remain_inside_frozen_budget() -> None:
    import ovc.shared_systems.dsai_shadow as module

    source_text = Path(inspect.getsourcefile(module.adapt_dsai_surface)).read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "adapt_dsai_surface")
    code_lines = node.end_lineno - node.lineno + 1
    by_surface = {item.surface: item for item in bindings()}
    byte_delta = 0
    for item, source in sources():
        wrapped = adapt_dsai_surface(by_surface[item["surface"]], source)
        byte_delta += max(0, len(canonical_json_bytes(wrapped)) - len(canonical_json_bytes(source)))
    budget = load(BUDGET_PATH)["pilot_acceptance_budget"]
    ledger = evaluate_adapter_complexity(
        "SHSI-WP7-DSAI-ADAPTER-LEDGER-v0.1",
        bindings(),
        budget=budget,
        code_surface_lines=code_lines,
        artifact_byte_delta=byte_delta,
    )
    assert ledger.status == "PASS"
    assert ledger.active_adapter_count == 0
    assert ledger.max_adapter_mapping_count == 1
    assert ledger.surface_coverage == tuple(sorted(item["surface"] for item in FIXTURE["sources"]))
    blocked = evaluate_adapter_complexity(
        "SHSI-WP7-DSAI-ADAPTER-LEDGER-BAD",
        bindings(),
        budget=budget,
        code_surface_lines=code_lines,
        artifact_byte_delta=byte_delta,
        incident_contribution_count=1,
    )
    assert blocked.status == "BLOCK"
    assert blocked.exceeded_dimensions == ("ADAPTER_INCIDENT_CONTRIBUTION_COUNT",)


def test_wp7_schema_declares_every_shadow_object() -> None:
    schema = load(ROOT / "schemas/shared_systems/dsai_shadow_consumer_v0_1.schema.json")
    expected = {
        "DSAISharedSystemsConsumptionManifest",
        "DSAIShadowExecutionContext",
        "DSAISurfaceAdapterBinding",
        "DSAIDualRunComparison",
        "DSAISecurityRefusalParity",
        "DSAIAdapterComplexityLedger",
    }
    assert expected <= set(schema["$defs"])
    assert FIXTURE["expected"]["surface_count"] == 5
    assert FIXTURE["expected"]["active_adapter_count"] == 0
