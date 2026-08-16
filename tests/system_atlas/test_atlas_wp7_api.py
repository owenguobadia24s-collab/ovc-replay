from __future__ import annotations

import json
import hashlib
import runpy
from pathlib import Path

from fastapi.testclient import TestClient

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas.api import create_atlas_app, generate_typescript_client
from ovc.system_atlas.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP6_TEST = ROOT / "tests/system_atlas/test_atlas_wp6_query.py"
OPENAPI = ROOT / "src/ovc/system_atlas/generated/atlas_openapi_v0_1.json"
CLIENT = ROOT / "src/ovc/system_atlas/generated/atlas_client_v0_1.ts"
ENVELOPE_SCHEMA = ROOT / "schemas/system_atlas/atlas_api_envelope_v0_1.schema.json"
WP7 = ROOT / "docs/programmes/system-atlas-v0-1/wp7"
EXTERNAL_WP7 = ROOT.parents[1] / "ovc-replay-external-artifacts/system_atlas/generations/wp7/ATLAS_WP7_API_EVIDENCE.json"


def setup_api(*, permission_resolver=None, missing_family: str | None = None):
    ns = runpy.run_path(str(WP6_TEST))
    predecessor, successor = ns["generations"]()
    receipts = {
        family: {
            "family": family,
            "result": "PASS",
            "optimized_conformance": "ADMITTED",
            "receipt_hash": str(index).zfill(64),
        }
        for index, family in enumerate(ns["QUERY_FAMILIES"], start=1)
        if family != missing_family
    }
    app = create_atlas_app(
        bundle=successor,
        comparison_bundle=predecessor,
        admitted_receipts=receipts,
        permission_resolver=permission_resolver,
    )
    return app, successor


def assert_envelope(body: dict, bundle) -> None:
    assert body["schema"] == "ovc-atlas-api-envelope/v1"
    assert body["graph_generation"] == bundle.root_hash
    assert body["repository_tree"] == bundle.root_manifest["repository_tree"]
    assert body["query_policy_version"] == "0.1"
    assert body["completeness_profile"] == bundle.root_manifest["completeness_profile"]
    assert body["write_effect"] == "NONE"
    validate_against_schema(body, json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8")))


def test_api_meta_and_query_are_generation_bound_and_receipted() -> None:
    app, bundle = setup_api()
    client = TestClient(app)
    meta = client.get("/api/v1/atlas/meta")
    assert meta.status_code == 200
    assert_envelope(meta.json(), bundle)
    assert len(meta.json()["data"]["admitted_query_families"]) == 10
    result = client.post("/api/v1/atlas/query", json={"family": "SEARCH", "term": "Atlas"})
    assert result.status_code == 200
    assert_envelope(result.json(), bundle)
    assert result.json()["data"]["family"] == "SEARCH"
    assert result.json()["data"]["authority_effect"] == "NONE_READ_ONLY_QUERY"


def test_missing_family_receipt_and_mutation_methods_fail_closed() -> None:
    app, bundle = setup_api(missing_family="IMPACT")
    client = TestClient(app)
    denied = client.post(
        "/api/v1/atlas/query",
        json={"family": "IMPACT", "changed_entity_ids": ["ovc:gate:atlas-g-observability-activate"]},
    )
    assert denied.status_code == 422
    assert_envelope(denied.json(), bundle)
    assert denied.json()["data"]["reason_code"] == "ATLAS_QUERY_FAMILY_RECEIPT_REQUIRED:IMPACT"
    for method, path in (("put", "/api/v1/atlas/meta"), ("patch", "/api/v1/atlas/query"), ("delete", "/api/v1/atlas/meta"), ("post", "/api/v1/atlas/unknown")):
        response = client.request(method.upper(), path, json={})
        assert response.status_code == 405
        assert_envelope(response.json(), bundle)


def test_permissions_are_server_resolved_and_restricted_data_does_not_leak() -> None:
    public_app, bundle = setup_api(permission_resolver=lambda _request: ("ATLAS_PUBLIC_METADATA",))
    public = TestClient(public_app)
    hidden = public.post("/api/v1/atlas/query", json={"family": "SEARCH", "term": "Hidden Atlas Service"})
    assert hidden.json()["data"]["result"]["matches"] == []
    assert hidden.json()["security_visibility"] == ["ATLAS_PUBLIC_METADATA"]
    restricted_app, _ = setup_api(
        permission_resolver=lambda _request: ("ATLAS_PUBLIC_METADATA", "ATLAS_INTERNAL", "ATLAS_RESTRICTED")
    )
    visible = TestClient(restricted_app).post(
        "/api/v1/atlas/query",
        json={"family": "SEARCH", "term": "Hidden Atlas Service"},
        headers={"x-atlas-partitions": "ATLAS_PUBLIC_METADATA"},
    )
    assert visible.json()["data"]["result"]["matches"][0]["entity"]["entity_id"] == "synthetic:service:wp6-restricted"
    assert_envelope(visible.json(), bundle)


def test_server_side_view_is_bounded_and_omits_evidence_locators() -> None:
    app, bundle = setup_api()
    client = TestClient(app)
    view = client.post("/api/v1/atlas/view", json={"maximum_entities": 200})
    assert view.status_code == 200
    assert_envelope(view.json(), bundle)
    projection = view.json()["data"]
    assert projection["status"] == "PASS"
    assert projection["nodes"] and projection["groups"]
    assert "evidence" not in json.dumps(projection).lower()
    capacity = client.post("/api/v1/atlas/view", json={"maximum_entities": 1})
    assert capacity.json()["data"]["status"] == "INCOMPLETE_CAPACITY"
    assert capacity.json()["data"]["nodes"] == []


def test_openapi_and_generated_typescript_are_exact_read_only_outputs() -> None:
    app, _ = setup_api()
    observed = app.openapi()
    assert observed == json.loads(OPENAPI.read_text(encoding="utf-8"))
    methods = {
        method.upper()
        for operations in observed["paths"].values()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    assert methods == {"GET", "POST"}
    assert generate_typescript_client(observed) == CLIENT.read_text(encoding="utf-8")
    assert "write_effect: \"NONE\"" in CLIENT.read_text(encoding="utf-8")


def test_wp7_packet_is_canonical_auto_pass_without_console_or_write_authority() -> None:
    implementation = json.loads((WP7 / "ATLAS_WP7_IMPLEMENTATION_PACKET.json").read_text(encoding="utf-8"))
    qa = json.loads((WP7 / "ATLAS_WP7_QA_PACKET.json").read_text(encoding="utf-8"))
    gate = json.loads((WP7 / "ATLAS_G7_GATE_PACKET.json").read_text(encoding="utf-8"))
    authority = json.loads((WP7 / "ATLAS_WP7_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    dependency = json.loads((WP7 / "ATLAS_WP7_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))

    assert gate["gate_class"] == "AUTO_NON_RESERVED"
    assert gate["decision"] == "AUTO_PASS"
    assert implementation["write_routes"] == 0
    assert implementation["research_console_binding_created"] is False
    assert implementation["canonical_assertions_published"] == 0
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert dependency["logical_id"] == canonical_sha256(dependency["payload"])
    assert "NO_RESEARCH_CONSOLE_SOURCE_OR_BINDING" in authority["payload"]["reserved_boundaries"]
    assert "NO_AA0_REUSE_WITHOUT_VALID_ACTUATION_MARKER" in authority["payload"]["reserved_boundaries"]
    assert len(qa["external_api_evidence"]["sha256"]) == 64
    if EXTERNAL_WP7.is_file():
        assert hashlib.sha256(EXTERNAL_WP7.read_bytes()).hexdigest() == qa["external_api_evidence"]["sha256"]
