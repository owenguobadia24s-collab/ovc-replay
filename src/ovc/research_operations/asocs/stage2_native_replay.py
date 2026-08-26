"""Bounded Session-1 adapter for the approved C2 native-observation audit replay.

This module changes no C1/C2 semantics.  It verifies and adapts the exact frozen
ASOCS source/case population, calls the existing frozen C1 formula and C2 vNext
real-source runtime, and projects only Horizon/Level/Container/Relation evidence
for the replacement Stage-2 human boundary.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import types
from typing import Any, Mapping

from ovc.opt_b.c1.formulas import C1_IMPLEMENTATION_ID, FORMULA_REGISTRY_ID, calculate as calculate_c1
from ovc.research_operations.asocs.population_aggregate import build_15m, build_2h
from ovc.research_operations.asocs.population_core import read_source
from ovc.research_operations.asocs.audit_execution import MorphologyBar
from ovc.opt_b.c2_vnext import real_source_materialisation as c2_runtime


REPLAY_CLASS = "C2_NATIVE_RUNTIME_AUDIT_REPLAY_NONAUTHORITATIVE"
SOURCE_SHA256 = "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
SOURCE_BYTE_SIZE = 11_048_144
SOURCE_ROW_COUNT = 186_145
SEQUENCE_SHA256 = "7d0f9e48b7b1ccfd44e3c38820c7dba186d0864f1be03c593ed19526ddbda986"
C2_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
PRICE_SIDE = "BID"
TIMEZONE = "UTC"
FORENSIC_CLASS = "FORENSICALLY_SUPPORTED_NOT_DECLARED"
SOURCE_SLICE_ID = "ASOCSI.S01.SOURCE.BID.UTC.FORENSIC.AUDIT.v1"
C1_RELEASE_ID = "ASOCSI.S01.C1.AUDIT.NONAUTHORITATIVE.v1"
MATERIALISATION_ID = "ASOCSI.WP8.S01.C2.NATIVE.OBSERVATION.AUDIT.REPLAY.v1"


class NativeReplayError(ValueError):
    """The bounded replay failed closed."""


def json_value(value: Any) -> Any:
    """Return a recursively JSON-safe projection of a runtime value."""
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, set):
        items = [json_value(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _z(value: str) -> str:
    return value if value.endswith("Z") else value + "Z"


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z"))


def _git_blob(repo_root: Path, path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], cwd=repo_root, text=True).strip()


def _git_object(repo_root: Path, blob_sha: str) -> bytes:
    return subprocess.check_output(["git", "cat-file", "blob", blob_sha], cwd=repo_root)


def bind_exact_runtime(repo_root: Path) -> dict[str, Any]:
    """Verify package identities and bind the exact frozen FORMULA blob if main advanced it."""
    freeze = json.loads((repo_root / "docs/programmes/asocs-v0-1/implementation/wp3/ASOCSI_G2_RUNTIME_IDENTITY_FREEZE_v0_1.json").read_text())
    c1 = freeze["c1"]
    if c1["implementation_id"] != C1_IMPLEMENTATION_ID or c1["formula_registry_id"] != FORMULA_REGISTRY_ID:
        raise NativeReplayError("C1_RUNTIME_IDENTITY_MISMATCH")
    expected_c1 = next(item["blob_sha"] for item in c1["implementation_blobs"] if item["path"].endswith("/formulas.py"))
    actual_c1 = _git_blob(repo_root, "src/ovc/opt_b/c1/formulas.py")
    if actual_c1 != expected_c1:
        raise NativeReplayError("C1_FROZEN_FORMULA_BLOB_MISMATCH")

    manifest_path = repo_root / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp11/C2AR_WP11_INTEGRATED_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["package_id"] != C2_PACKAGE_ID or manifest["package_sha256"] != C2_PACKAGE_SHA256:
        raise NativeReplayError("C2_PACKAGE_IDENTITY_MISMATCH")
    resolutions = []
    for component in manifest["components"]:
        for role in ("implementation", "registry"):
            path = component[f"{role}_path"]
            expected = component[f"{role}_blob_sha"]
            actual = _git_blob(repo_root, path)
            if actual == expected:
                resolutions.append({"component": component["component"], "role": role, "expected_blob": expected, "observed_blob": actual, "resolution": "WORKTREE_EXACT"})
                continue
            if component["component"] != "FORMULA" or role != "implementation":
                raise NativeReplayError(f"C2_FROZEN_COMPONENT_BLOB_MISMATCH:{component['component']}:{role}")
            exact_source = _git_object(repo_root, expected)
            if hashlib.sha1(f"blob {len(exact_source)}\0".encode() + exact_source).hexdigest() != expected:
                raise NativeReplayError("C2_FROZEN_FORMULA_OBJECT_INVALID")
            module = types.ModuleType("ovc_c2_frozen_formula_profiles")
            exec(compile(exact_source, f"git-blob:{expected}", "exec"), module.__dict__)
            for name in ("evaluate_location_profile", "evaluate_motion_profile", "evaluate_organisation_profile", "evaluate_interaction_profile"):
                setattr(c2_runtime, name, getattr(module, name))
            resolutions.append({"component": "FORMULA", "role": "implementation", "expected_blob": expected, "observed_blob": actual, "resolution": "EXACT_FROZEN_GIT_BLOB_EXECUTED"})
    return {
        "c1": {"implementation_id": C1_IMPLEMENTATION_ID, "formula_registry_id": FORMULA_REGISTRY_ID, "formula_blob": actual_c1},
        "c2": {"package_id": C2_PACKAGE_ID, "package_sha256": C2_PACKAGE_SHA256, "components": resolutions},
    }


def forensic_binding() -> dict[str, Any]:
    return {
        "schema": "ovc-asocsi-forensic-audit-source-binding/v0_1",
        "binding_scope": "SESSION1_C2_NATIVE_RUNTIME_AUDIT_REPLAY_ONLY",
        "price_side": {"value": PRICE_SIDE, "classification": FORENSIC_CLASS},
        "timestamp_timezone": {"value": TIMEZONE, "classification": FORENSIC_CLASS},
        "historical_wp1_wp4_provenance_mutated": False,
        "declared_provider_provenance": False,
        "active_source_identity": False,
        "authority_effect": "NONE",
        "replay_class": REPLAY_CLASS,
    }


def _c1_for_bar(bar: Mapping[str, Any], prior: Mapping[str, Any] | None) -> dict[str, Any]:
    def model(item: Mapping[str, Any]) -> MorphologyBar:
        return MorphologyBar(*(Decimal(str(item[key])) for key in ("open", "high", "low", "close")), None)
    contiguous = prior is not None and _parse(str(prior["interval_end"])) == _parse(str(bar["interval_start"]))
    measurements, categorical, nulls = calculate_c1(model(bar), model(prior) if contiguous else None, None if contiguous else "SOURCE_CONTINUITY_UNRESOLVED_OR_GAP")
    return {"schema": "ovc-asocs-c1-morphology-audit/v0_1", "categorical": categorical, "measurements": measurements, "null_reasons": nulls}


def _adapter_row(bar: Mapping[str, Any], c1: Mapping[str, Any], clock: str, *, target: bool = False) -> dict[str, Any]:
    payload = {
        "source_bar_id": bar["bar_id"], "clock": clock, "open_time": _z(str(bar["interval_start"])),
        "close_time": _z(str(bar["interval_end"])), "side": PRICE_SIDE, "c1": c1,
        "source_slice_id": SOURCE_SLICE_ID, "c1_release_id": C1_RELEASE_ID,
    }
    return {
        **payload,
        "c1_record_id": "ASOCSI.C1.AUDIT." + sha256_obj(payload)[:32],
        "opt_a_release_id": SOURCE_SLICE_ID,
        "source_manifest_sha256": SOURCE_SHA256,
        "quality_state": "COMPLETE",
        "prices": {key: str(bar[key]) for key in ("open", "high", "low", "close")},
        "target_eligible": target,
    }


def prepare_population(source_path: Path, sequence_path: Path) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    if len(source_bytes) != SOURCE_BYTE_SIZE or sha256_bytes(source_bytes) != SOURCE_SHA256:
        raise NativeReplayError("EXACT_SOURCE_BYTES_MISMATCH")
    sequence_bytes = sequence_path.read_bytes()
    if sha256_bytes(sequence_bytes) != SEQUENCE_SHA256:
        raise NativeReplayError("EXACT_CASE_SEQUENCE_BYTES_MISMATCH")
    sequence = json.loads(sequence_bytes)
    if sequence.get("case_count") != 25 or len(sequence.get("cases", [])) != 25:
        raise NativeReplayError("CASE_POPULATION_MISMATCH")
    rows, byte_size = read_source(source_path, SOURCE_SHA256)
    if byte_size != SOURCE_BYTE_SIZE or len(rows) != SOURCE_ROW_COUNT:
        raise NativeReplayError("SOURCE_COUNT_OR_SIZE_MISMATCH")
    surface15, complete15 = build_15m(rows, SOURCE_SHA256)
    surface2h = build_2h(rows, complete15, SOURCE_SHA256)
    complete_order = sorted(complete15)
    c1_15: dict[str, dict[str, Any]] = {}
    previous: Mapping[str, Any] | None = None
    for start in complete_order:
        bar = complete15[start]
        c1 = _c1_for_bar(bar, previous)
        c1_15[str(bar["interval_start"])] = _adapter_row(bar, c1, "15M")
        previous = bar
    c1_2h: dict[str, dict[str, Any]] = {}
    previous = None
    for bar in surface2h:
        if bar["status"] != "COMPLETE":
            previous = None
            continue
        c1 = _c1_for_bar(bar, previous)
        c1_2h[str(bar["interval_start"])] = _adapter_row(bar, c1, "2H_A_L")
        previous = bar

    surface_by_start = {str(item["interval_start"]): item for item in surface15}
    parity_count = 0
    seen: dict[str, str] = {}
    for case in sequence["cases"]:
        for frozen in case["sequence"]:
            start = str(frozen["interval_start"])
            observed = surface_by_start.get(start)
            if observed is None or observed["status"] != frozen["status"]:
                raise NativeReplayError(f"FROZEN_SEQUENCE_STATUS_MISMATCH:{case['case_id']}:{start}")
            # Scope memberships are case-relative presentation metadata; the
            # underlying frozen bucket identity/content must agree on overlap.
            digest = sha256_obj({key: value for key, value in frozen.items() if key != "scope_memberships"})
            if start in seen and seen[start] != digest:
                raise NativeReplayError(f"OVERLAPPING_FROZEN_CASE_ROW_MISMATCH:{start}")
            seen[start] = digest
            if frozen["status"] == "COMPLETE":
                adapted = c1_15[start]
                if adapted["prices"] != frozen["ohlc"] or adapted["c1"] != frozen["c1"] or adapted["source_bar_id"] != frozen["bar_id"]:
                    raise NativeReplayError(f"FROZEN_C1_PARITY_MISMATCH:{case['case_id']}:{start}")
                parity_count += 1
    return {
        "sequence": sequence, "surface15": surface15, "c1_15": c1_15, "c1_2h": c1_2h,
        "preflight": {"source_rows": len(rows), "g1_15m_surface_rows": len(surface15), "frozen_case_rows_checked": sum(len(c["sequence"]) for c in sequence["cases"]), "complete_c1_rows_checked": parity_count, "unique_frozen_bucket_count": len(seen)},
    }


def _select_anchor(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    anchor = _z(str(case["review_anchor_time"]))
    observations = [item for item in result["complete15"] if item["first_valid_time"] == anchor]
    if len(observations) != 1:
        raise NativeReplayError(f"ANCHOR_OBSERVATION_NOT_UNIQUE:{case['case_id']}:{len(observations)}")
    observation = observations[0]
    bundles = [item for item in result["bundles"] if item["observation_id"] == observation["observation_id"]]
    if len(bundles) != 1:
        raise NativeReplayError(f"ANCHOR_BUNDLE_NOT_UNIQUE:{case['case_id']}")
    bundle = bundles[0]
    memberships = [item for item in result["memberships"] if item["membership_id"] in set(bundle["horizon_membership_ids"])]
    levels = [item for item in result["levels"] if item["level_id"] in set(bundle["level_ids"])]
    containers = [item for item in result["containers"] if item["container_id"] in set(bundle["container_ids"])]
    relation_sets = [item for item in result["relation_sets"] if item["relation_set_id"] in set(bundle["relation_set_ids"])]
    relation_ids = {identity for item in relation_sets for identity in item["relation_ids"]}
    relations = [item for item in result["relations"] if item.get("relation_id") in relation_ids]
    return {
        "case_id": case["case_id"], "presentation_ordinal": case["presentation_ordinal"],
        "review_anchor_time": case["review_anchor_time"], "status": "C2_NATIVE_OBSERVATION_AVAILABLE",
        "observation": observation, "horizons": memberships, "levels": levels,
        "containers": containers, "relation_sets": relation_sets, "relations": relations,
        "authority": {"replay_class": REPLAY_CLASS, "active": False, "canonical": False, "publication": False},
    }


def execute_replay(repo_root: Path, source_path: Path, sequence_path: Path, run_label: str) -> dict[str, Any]:
    mutable_bindings = (
        "CONTEXT_START", "CONTEXT_END", "TARGET_START", "TARGET_END", "PARTITION_ID",
        "SOURCE_SLICE_ID", "C1_RELEASE_ID", "MATERIALISATION_ID",
        "evaluate_location_profile", "evaluate_motion_profile",
        "evaluate_organisation_profile", "evaluate_interaction_profile",
    )
    original = {name: getattr(c2_runtime, name) for name in mutable_bindings}
    try:
        runtime = bind_exact_runtime(repo_root)
        prepared = prepare_population(source_path, sequence_path)
        cases_out = []
        totals = {"case_runtime_invocations": 0, "complete_15m_observations": 0, "horizon_memberships": 0, "levels": 0, "containers": 0, "relations": 0}
        for case in prepared["sequence"]["cases"]:
            if case["presentation_ordinal"] == 19:
                cases_out.append({"case_id": case["case_id"], "presentation_ordinal": 19, "review_anchor_time": case["review_anchor_time"], "status": "SOURCE_GAP_C2_NOT_FABRICATED", "horizons": [], "levels": [], "containers": [], "relation_sets": [], "relations": [], "authority": {"replay_class": REPLAY_CLASS, "active": False, "canonical": False, "publication": False}})
                continue
            wider = case["navigation_window"]["wider"]
            start, end = str(wider["start"]), str(wider["end"])
            c2_runtime.CONTEXT_START, c2_runtime.CONTEXT_END = _z(start), _z(end)
            c2_runtime.TARGET_START = c2_runtime.TARGET_END = _z(str(case["review_anchor_time"]))
            c2_runtime.PARTITION_ID = f"ASOCSI.S01.CASE.{case['presentation_ordinal']:02d}.AUDIT.v1"
            c2_runtime.SOURCE_SLICE_ID, c2_runtime.C1_RELEASE_ID = SOURCE_SLICE_ID, C1_RELEASE_ID
            c2_runtime.MATERIALISATION_ID = MATERIALISATION_ID
            rows15 = []
            for frozen in case["sequence"]:
                if frozen["status"] == "COMPLETE":
                    row = copy.deepcopy(prepared["c1_15"][str(frozen["interval_start"])])
                    row["target_eligible"] = str(frozen["interval_end"]) == str(case["review_anchor_time"])
                    rows15.append(row)
            floor2 = _parse(start).replace(hour=_parse(start).hour // 2 * 2, minute=0, second=0, microsecond=0)
            ceil2 = _parse(end) + timedelta(hours=2)
            rows2h = [copy.deepcopy(row) for key, row in prepared["c1_2h"].items() if floor2 <= _parse(key) < ceil2]
            result = c2_runtime.build_side(PRICE_SIDE, rows15, rows2h)
            anchor = _select_anchor(case, result)
            anchor["case_runtime_sha256"] = sha256_obj(result)
            anchor["case_runtime_counts"] = {key: len(result[key]) for key in ("full15", "complete15", "complete2h", "memberships", "levels", "containers", "relations", "relation_sets", "profiles", "contexts", "bundles")}
            cases_out.append(anchor)
            totals["case_runtime_invocations"] += 1
            totals["complete_15m_observations"] += len(result["complete15"])
            totals["horizon_memberships"] += len(result["memberships"])
            totals["levels"] += len(result["levels"])
            totals["containers"] += len(result["containers"])
            totals["relations"] += len(result["relations"])
    finally:
        for name, value in original.items():
            setattr(c2_runtime, name, value)
    output = {
        "schema": "ovc-asocsi-stage2-c2-native-observation-replay-run/v0_1",
        "programme_id": "OVC-ASOCS-6M-v0.1", "packet_id": "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-REPLAY",
        "run_label": run_label, "replay_class": REPLAY_CLASS, "forensic_binding": forensic_binding(),
        "source": {"sha256": SOURCE_SHA256, "byte_size": SOURCE_BYTE_SIZE, "row_count": SOURCE_ROW_COUNT},
        "case_sequence": {"sha256": SEQUENCE_SHA256, "case_count": 25}, "runtime": runtime,
        "preflight": prepared["preflight"], "totals": totals, "cases": cases_out,
        "firewall": {"c2e_revealed": False, "occurrence_context_revealed": False, "stage3_revealed": False, "construct_survival_decided": False, "validation": "DENIED", "publication_probability_risk_exposure_trading_execution_agent_write": "NONE"},
    }
    output["identity_bearing_sha256"] = sha256_obj({key: value for key, value in output.items() if key != "run_label"})
    output["logical_sha256"] = sha256_obj(output)
    return output


def write_run(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            handle.write(canonical_bytes(value) + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sequence", type=Path, required=True)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = execute_replay(args.repo.resolve(), args.source, args.sequence, args.run_label)
    write_run(args.out, result)
    print(json.dumps({"logical_sha256": result["logical_sha256"], "totals": result["totals"], "case_statuses": {x["status"]: sum(1 for c in result["cases"] if c["status"] == x["status"]) for x in result["cases"]}}, sort_keys=True))


if __name__ == "__main__":
    main()
