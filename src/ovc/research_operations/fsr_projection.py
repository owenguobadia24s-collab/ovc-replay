"""Research Operations projection for the FSR synthetic rehearsal.

All durable records remain research-only, synthetic and non-promotable. The projection
uses the existing Research Operations envelope, freeze verification, QA runner,
artifact catalogue object model and deterministic read model. It never writes active
selectors or Validation payloads.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .canonical import canonical_sha256
from .catalogue import ArtifactCatalogue, ArtifactNode
from .lifecycle import freeze_record, verify_frozen_record
from .qa import QAAssertion, QARunner
from .read_model import ReadModelBuilder

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
CREATED_AT = "2026-08-08T10:14:00Z"
SOURCE_CUTOFF = "2023-06-06T00:00:00Z"


def _lineage(*, derived_from: Sequence[str] = ()) -> dict[str, Any]:
    return {"parent": None, "derived_from": list(derived_from), "supersedes": None, "adjudicates": None}


def _artifact_ref(name: str, sha256: str) -> dict[str, Any]:
    return {
        "artifact_id": f"FSR.ARTIFACT.{name}",
        "sha256": sha256,
        "availability": "VERIFIED",
        "required": True,
        "available_at": SOURCE_CUTOFF,
        "authority": "SYNTHETIC_REHEARSAL_EVIDENCE_ONLY",
    }


def _draft(
    *, record_type: str, payload: Mapping[str, Any], source_release_refs: Sequence[Mapping[str, Any]] = (),
    artifact_refs: Sequence[Mapping[str, Any]] = (), derived_from: Sequence[str] = (), missingness: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "schema_version": "0.1",
        "lifecycle_state": "DRAFT",
        "created_at": CREATED_AT,
        "frozen_at": None,
        "operator_id": "OVC.FSR.OPERATOR",
        "admissible_cutoff": SOURCE_CUTOFF,
        "source_release_refs": [dict(item) for item in source_release_refs],
        "artifact_refs": [dict(item) for item in artifact_refs],
        "model_refs": [],
        "missingness": list(missingness),
        "lineage": _lineage(derived_from=derived_from),
        "authority_state": "DRAFT",
        "reproducibility_state": "REPRODUCIBLE",
        "payload": dict(payload),
    }


def _catalogue(stage_hashes: Mapping[str, str], *, source_commit: str, fixture_id: str) -> ArtifactCatalogue:
    order = ("OPT_A", "C1", "C2", "C2E", "SRFD", "MARKET_GRAMMAR")
    nodes: list[ArtifactNode] = []
    prior: str | None = None
    for name in order:
        if name not in stage_hashes:
            continue
        artifact_id = f"FSR.ARTIFACT.{name}"
        nodes.append(
            ArtifactNode(
                artifact_id=artifact_id,
                artifact_type="MANIFEST",
                owner=PROGRAMME_ID,
                authority="DERIVED_ASSURANCE_ONLY",
                release_id=fixture_id,
                sha256=stage_hashes[name],
                size_bytes=None,
                media_type="application/json",
                locations=({"root_alias": "FSR_DERIVED", "relative_path": f"{name}.json"},),
                availability="LOCAL_VERIFIED",
                dependencies=(prior,) if prior else (),
                source_kind="LOCAL",
                metadata={"synthetic": True, "promotable": False},
            )
        )
        prior = artifact_id
    logical = canonical_sha256([node.logical_dict() for node in nodes])
    return ArtifactCatalogue(
        schema="ovc-research-operations-artifact-catalogue/v0.1",
        generated_at=CREATED_AT,
        source_commit=source_commit,
        nodes=tuple(nodes),
        issues=(),
        logical_inventory_sha256=logical,
    )


def _checks():
    def authority_check(target: dict[str, Any]) -> QAAssertion:
        forbidden = []
        for field in ("selector_mutation", "publication", "validation_consumption", "promotion"):
            value = target.get(field)
            if field == "validation_consumption" and value in {"DENIED", "LOCKED_UNCONSUMED"}:
                continue
            if field != "validation_consumption" and value in {"NONE", None}:
                continue
            forbidden.append(f"{field}={value}")
        return QAAssertion(
            "FSR-QA-AUTHORITY",
            str(target["fixture_id"]),
            "PASS" if not forbidden else "BLOCK",
            "BLOCKING",
            "reserved authorities unchanged" if not forbidden else ";".join(forbidden),
        )

    def chronology_check(target: dict[str, Any]) -> QAAssertion:
        ok = bool(target.get("chronology_pass"))
        return QAAssertion(
            "FSR-QA-CHRONOLOGY", str(target["fixture_id"]), "PASS" if ok else "BLOCK", "BLOCKING",
            "first-valid chronology preserved" if ok else "chronology assertion failed",
        )

    def hidden_check(target: dict[str, Any]) -> QAAssertion:
        ok = not bool(target.get("hidden_construction_consumed"))
        return QAAssertion(
            "FSR-QA-HIDDEN-FIREWALL", str(target["fixture_id"]), "PASS" if ok else "BLOCK", "BLOCKING",
            "hidden construction ledger not consumed" if ok else "hidden construction leak",
        )

    def lineage_check(target: dict[str, Any]) -> QAAssertion:
        expected = ("OPT_A", "C1", "C2", "C2E", "SRFD")
        missing = [name for name in expected if not target.get("stage_hashes", {}).get(name)]
        return QAAssertion(
            "FSR-QA-LINEAGE", str(target["fixture_id"]), "PASS" if not missing else "BLOCK", "BLOCKING",
            "required stage identities present" if not missing else "missing stage hashes:" + ",".join(missing),
        )

    return (authority_check, chronology_check, hidden_check, lineage_check)


def project_fsr_research_operations(
    *,
    source_commit: str,
    opt_a: Mapping[str, Any],
    c1_logical_sha256: str,
    c2: Mapping[str, Any],
    c2e: Mapping[str, Any],
    srfd: Mapping[str, Any],
    grammar: Mapping[str, Any],
    upper_layer_boundary_sha256: str,
) -> dict[str, Any]:
    stage_hashes = {
        "OPT_A": str(opt_a["manifest_sha256"]),
        "C1": c1_logical_sha256,
        "C2": str(c2["logical_sha256"]),
        "C2E": str(c2e["logical_sha256"]),
        "SRFD": str(srfd["logical_sha256"]),
        "MARKET_GRAMMAR": str(grammar["logical_sha256"]),
        "UPPER_LAYER_BOUNDARY": upper_layer_boundary_sha256,
    }
    artifact_refs = [_artifact_ref(name, digest) for name, digest in sorted(stage_hashes.items())]
    source_ref = {
        "release_id": opt_a["fixture_id"],
        "manifest_id": opt_a["manifest_id"],
        "manifest_sha256": opt_a["manifest_sha256"],
        "first_valid_time": SOURCE_CUTOFF,
        "validation_access_state": "LOCKED_UNCONSUMED",
        "payload_access": "SYNTHETIC_FIXTURE_ONLY",
    }
    release_record = freeze_record(
        _draft(
            record_type="DATA_RELEASE_REF",
            payload={
                "release_id": opt_a["fixture_id"],
                "manifest_id": opt_a["manifest_id"],
                "manifest_sha256": opt_a["manifest_sha256"],
                "role": "SYNTHETIC_FRESH_DISCOVERY_REHEARSAL",
                "instrument": "GBPUSD",
                "coverage_start": "2023-06-05T00:00:00Z",
                "coverage_end": SOURCE_CUTOFF,
                "clocks": ["M1", "15M", "H1_PROVIDER_NATIVE", "H1_M1_DERIVED", "2H_A_L"],
                "sides": ["BID", "ASK"],
                "qa_state": "SYNTHETIC_ONLY",
                "validation_access_state": "LOCKED_UNCONSUMED",
            },
            artifact_refs=[_artifact_ref("OPT_A", stage_hashes["OPT_A"])],
        ),
        frozen_at=CREATED_AT,
    )
    verify_frozen_record(release_record)

    case_record = freeze_record(
        _draft(
            record_type="CASE_BUNDLE",
            payload={
                "title": "Full-stack synthetic fresh-discovery rehearsal v0.1",
                "record_refs": [release_record["record_id"]],
                "artifact_refs": [item["artifact_id"] for item in artifact_refs],
                "review_state": "SYNTHETIC_REHEARSAL_FROZEN_PRE_ADJUDICATION",
            },
            source_release_refs=[source_ref],
            artifact_refs=artifact_refs,
            derived_from=[release_record["record_id"]],
            missingness=["OccurrenceContext forward object not implemented", "C2P persistent structural objects not implemented", "revised C2.5 forward event layer not implemented"],
        ),
        frozen_at=CREATED_AT,
    )
    verify_frozen_record(case_record)

    decision_record = freeze_record(
        _draft(
            record_type="DECISION_RECORD",
            payload={
                "decision_scope": "FSR-G4 UPPER-LAYER SYNTHETIC READINESS",
                "disposition": "PASS_AVAILABLE_COMPONENTS_WITH_EXPLICIT_NOT_REACHED_BOUNDARIES",
                "reason": "C2E, SRFD and inactive market-grammar components are executable in bounded synthetic shadow mode; OccurrenceContext, forward C2P and revised C2.5 are not fabricated.",
                "authority_delta": "NONE",
                "rollback": "Delete FSR derived artifacts; upstream authorities and selectors remain unchanged.",
            },
            source_release_refs=[source_ref],
            artifact_refs=artifact_refs,
            derived_from=[case_record["record_id"]],
        ),
        frozen_at=CREATED_AT,
    )
    verify_frozen_record(decision_record)

    qa_target = {
        "fixture_id": opt_a["fixture_id"],
        "stage_hashes": stage_hashes,
        "selector_mutation": "NONE",
        "publication": "NONE",
        "validation_consumption": "DENIED",
        "promotion": "NONE",
        "chronology_pass": bool(c2["chronology"]["all_c2_first_valid_not_before_interval_end"] and c2["chronology"]["all_formula_as_of_not_after_snapshot"] and c2["cross_segment_transition_count"] == 0),
        "hidden_construction_consumed": any((c2["chronology"]["hidden_construction_consumed"], c2e["hidden_construction_consumed"], srfd["hidden_construction_consumed"], grammar["hidden_construction_consumed"])),
    }
    qa_run = QARunner(_checks()).run(qa_target, target_id=str(opt_a["fixture_id"]), source_commit=source_commit)
    catalogue = _catalogue(stage_hashes, source_commit=source_commit, fixture_id=str(opt_a["fixture_id"]))
    read_model = ReadModelBuilder().build(
        source_commit=source_commit,
        catalogue=catalogue,
        records=[release_record, case_record, decision_record],
        qa_runs=[qa_run.to_dict()],
    )
    body = {
        "schema": "ovc-fsr-research-operations-projection/v1",
        "programme_id": PROGRAMME_ID,
        "fixture_id": opt_a["fixture_id"],
        "stage_hashes": stage_hashes,
        "records": [release_record, case_record, decision_record],
        "qa_run": qa_run.to_dict(),
        "catalogue": catalogue.to_dict(),
        "read_model": read_model.to_dict(),
        "authority": {
            "research_record_authority": "FROZEN_SYNTHETIC_REHEARSAL_ONLY",
            "market_authority": "NONE",
            "selector": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    body["logical_sha256"] = canonical_sha256(body)
    return body
