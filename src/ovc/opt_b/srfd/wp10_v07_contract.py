from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from .real_source_packs import compile_real_source_representation
from .serialization import canonical_json_bytes, logical_sha256
from .wp10_execution_resilience import RunBinding

PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v0.7"
FROZEN_POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
FROZEN_ELIGIBLE_COUNT = 8598
FROZEN_ELIGIBLE_IDS_SHA256 = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
FROZEN_DOMAIN_COUNT = 36
FROZEN_PAIR_COUNT = 35380668
FROZEN_FAMILY_CONFIGURATION_COUNT = 1944
FROZEN_SCIENTIFIC_MANIFEST_SHA256 = "6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb"
FROZEN_PREREGISTRATION_SHA256 = "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3"
FROZEN_REPRESENTATION_PACK_SHA256 = "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0"
FROZEN_SEGMENTATION_PACK_SHA256 = "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0"
FROZEN_STABILITY_PACK_SHA256 = "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b"
FROZEN_SOURCE_BINDING_SHA256 = "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7"
FROZEN_CAPACITY_GRID_SHA256 = "68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866"
T0_MAX_WALL_SECONDS = 14400
T0_MAX_PEAK_RSS_BYTES = 17179869184
T0_MAX_EXTERNAL_BYTES = 10737418240

FROZEN_SOURCE_RELEASE_ID = "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9"
FROZEN_SOURCE_COMMIT = "837c9a3e1cbfc18bf01d577896a8f2e01d12f7d2"
FROZEN_SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
FROZEN_SOURCE_MANIFEST_SHA256 = "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
FROZEN_OUTPUT_MANIFEST_SHA256 = "e805eaa0f8603da644d23d83297fdc5e62142f8051d8583c9c28c9469a3b704b"
FROZEN_ACTIVE_C2_RELEASE_ID = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
FROZEN_OPERATION_MODE = "TIME_GATED_REPLAY"
FROZEN_ROLE = "DISCOVERY"

FROZEN_C2_FILE_SHA256 = {
    "C2_15M_ASK_LOCAL": "f0df9558afc5740aabd2dd9f75e958880efd5343b70982d77f4c1e3252ba4e8a",
    "C2_15M_ASK_PARENT": "4b67517f54d02b1f601c451b4f4ed9eb5a1dee05712ef44c1463b06f8500f879",
    "C2_15M_BID_LOCAL": "63a1d24836d3cd0aaad9e5a11e9b9ec51724bfd335fab47f538ed23f36e8c58b",
    "C2_15M_BID_PARENT": "15e487cede1bd8a2ccdbfe4c515c72d10b6e5bea9c54f1c7212a368a146e1b88",
    "C2_2H_ASK_LOCAL": "f671c18b01d840d3cca8a058f905104146f77254b7ca400378818697242170cb",
    "C2_2H_BID_LOCAL": "ce7704f1a29dde6e22e0083fbcfda67fef2929875304c2eb9a0874e63d3d27f5",
}
NON_EVALUATED_PRECEDENCE = (
    "QUARANTINED", "CONFLICT", "CENSORED", "NOT_EVALUABLE", "NOT_EVALUATED"
)
EXPECTED_SEGMENTATION_COUNTS = {
    "RUN_CHANGE_SEGMENTATION": {"stream_count": 264, "segment_count": 7609, "boundary_count": 7345},
    "NULL_BOUNDARY_CONTROL": {"stream_count": 264, "segment_count": 264, "boundary_count": 0},
}
SENSITIVITY_LADDERS = {
    "radius": ("0.04", "0.08", "0.16"),
    "minimum_support": ("2", "4", "8"),
    "k": ("2", "4", "8"),
    "max_assignment_distance": ("0.10", "0.20", "0.40"),
    "max_iterations": ("8",),
}


class WP10RunnerError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class ConfigurationDescriptor:
    configuration_id: str
    family_method_id: str
    minimum_support: int
    kind: str
    linkage: str | None = None
    radius: str | None = None
    k: int | None = None
    max_assignment_distance: str | None = None
    max_iterations: int | None = None

    @property
    def parameters(self) -> dict[str, str]:
        output = {"minimum_support": str(self.minimum_support)}
        if self.radius is not None:
            output["radius"] = str(self.radius)
        if self.k is not None:
            output["k"] = str(self.k)
        if self.max_assignment_distance is not None:
            output["max_assignment_distance"] = str(self.max_assignment_distance)
        if self.max_iterations is not None:
            output["max_iterations"] = str(self.max_iterations)
        return output

    def to_dict(self) -> dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "family_method_id": self.family_method_id,
            "shared_minimum_support": self.minimum_support,
            "kind": self.kind,
            "linkage": self.linkage,
            "parameters": self.parameters,
        }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WP10RunnerError(
                    "QA_SCHEMA_FAILURE", f"{path.name}:{line_number}:{exc}"
                ) from exc
            if not isinstance(row, Mapping):
                raise WP10RunnerError(
                    "QA_SCHEMA_FAILURE", f"{path.name}:{line_number}:mapping required"
                )
            rows.append(dict(row))
    return rows


def verify_frozen_run_binding(binding: RunBinding) -> None:
    expected = {
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "population_id": FROZEN_POPULATION_ID,
        "eligible_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256,
        "scientific_manifest_sha256": FROZEN_SCIENTIFIC_MANIFEST_SHA256,
        "preregistration_sha256": FROZEN_PREREGISTRATION_SHA256,
        "representation_pack_sha256": FROZEN_REPRESENTATION_PACK_SHA256,
        "segmentation_pack_sha256": FROZEN_SEGMENTATION_PACK_SHA256,
        "stability_pack_sha256": FROZEN_STABILITY_PACK_SHA256,
        "source_binding_sha256": FROZEN_SOURCE_BINDING_SHA256,
        "capacity_grid_sha256": FROZEN_CAPACITY_GRID_SHA256,
    }
    actual = binding.to_dict()
    for key, value in expected.items():
        if actual.get(key) != value:
            raise WP10RunnerError("RUN_BINDING_SCIENCE_DRIFT", f"{key}:{actual.get(key)}")
    implementation = str(actual.get("implementation_commit") or "")
    if len(implementation) != 64 or any(ch not in "0123456789abcdef" for ch in implementation):
        raise WP10RunnerError(
            "RUN_BINDING_IMPLEMENTATION_INVALID", "implementation binding must be SHA-256 hex"
        )


def verify_durable_workspace(root: Path) -> dict[str, Any]:
    destination = Path(root).expanduser().resolve()
    module_path = Path(__file__).resolve()
    candidate_repo = module_path.parents[4] if len(module_path.parents) > 4 else None
    if candidate_repo is not None and (candidate_repo / ".git").exists():
        try:
            destination.relative_to(candidate_repo)
        except ValueError:
            pass
        else:
            raise WP10RunnerError(
                "AUTH_SCOPE_EXPANSION", "durable run artifacts must not be stored inside Git"
            )
    destination.mkdir(parents=True, exist_ok=True)
    probe = destination / ".wp10-durable-probe"
    tmp = destination / ".wp10-durable-probe.tmp"
    payload = b"OVC-WP10-DURABLE-PROBE\n"
    try:
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, probe)
        if probe.read_bytes() != payload:
            raise WP10RunnerError("DURABLE_STORE_UNAVAILABLE", "durability probe mismatch")
    except OSError as exc:
        raise WP10RunnerError("DURABLE_STORE_UNAVAILABLE", str(exc)) from exc
    finally:
        tmp.unlink(missing_ok=True)
        probe.unlink(missing_ok=True)
    return {"status": "PASS", "atomic_replace": True, "file_fsync": True, "inside_git": False}


def verify_and_load_frozen_source(
    source_paths: Mapping[str, str | Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if set(source_paths) != set(FROZEN_C2_FILE_SHA256):
        raise WP10RunnerError(
            "SOURCE_BINDING_MISMATCH",
            f"required={sorted(FROZEN_C2_FILE_SHA256)} actual={sorted(source_paths)}",
        )
    all_rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for source_key in sorted(source_paths):
        path = Path(source_paths[source_key])
        if not path.is_file():
            raise WP10RunnerError("ARTIFACT_UNAVAILABLE", f"{source_key}:{path}")
        actual_sha = _file_sha256(path)
        if actual_sha != FROZEN_C2_FILE_SHA256[source_key]:
            raise WP10RunnerError(
                "SOURCE_BINDING_MISMATCH", f"{source_key}:{actual_sha}"
            )
        rows = _load_jsonl(path)
        receipts.append(
            {
                "source_key": source_key,
                "sha256": actual_sha,
                "record_count": len(rows),
            }
        )
        all_rows.extend(rows)
    if len(all_rows) != 9420:
        raise WP10RunnerError("SOURCE_BINDING_MISMATCH", f"record_count={len(all_rows)}")
    eligible_ids = sorted(
        str(row["c2_state_id"]) for row in all_rows if bool(row.get("target_eligible"))
    )
    eligible_hash = sha256(canonical_json_bytes(eligible_ids)).hexdigest()
    if len(eligible_ids) != FROZEN_ELIGIBLE_COUNT or eligible_hash != FROZEN_ELIGIBLE_IDS_SHA256:
        raise WP10RunnerError(
            "POPULATION_BINDING_MISMATCH", f"eligible={len(eligible_ids)} hash={eligible_hash}"
        )
    return all_rows, receipts


def _computability(axes: Mapping[str, Mapping[str, Any]]) -> tuple[str, str | None]:
    for status in NON_EVALUATED_PRECEDENCE:
        if any(str(item["status"]) == status for item in axes.values()):
            reasons = [
                f"{name}:{item['status']}:{item.get('reason_code') or 'UNSPECIFIED'}"
                for name, item in axes.items()
                if item["status"] != "EVALUATED"
            ]
            return status, "|".join(reasons)
    return "EVALUABLE", None


def adapted_capacity_record(row: Mapping[str, Any]) -> dict[str, Any]:
    if str(row.get("active_c2_model_release_id")) != FROZEN_ACTIVE_C2_RELEASE_ID:
        raise WP10RunnerError("SOURCE_BINDING_MISMATCH", "active C2 release")
    if str(row.get("source_slice_id")) != FROZEN_SOURCE_SLICE_ID:
        raise WP10RunnerError("SOURCE_BINDING_MISMATCH", "source slice")
    if str(row.get("operation_mode")) != FROZEN_OPERATION_MODE or str(row.get("role")) != FROZEN_ROLE:
        raise WP10RunnerError("AUTH_SCOPE_EXPANSION", "operation mode/role")
    if bool(row.get("release_membership")):
        raise WP10RunnerError("AUTH_SCOPE_EXPANSION", "release membership")
    if str(row.get("live_prospective_append", "DENIED")) != "DENIED":
        raise WP10RunnerError("AUTH_SCOPE_EXPANSION", "live prospective append")
    raw_axes = row.get("axes")
    if not isinstance(raw_axes, Mapping):
        raise WP10RunnerError("QA_SCHEMA_FAILURE", "native C2 axes required")
    axis_payload: dict[str, dict[str, Any]] = {}
    for axis_name in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"):
        axis = raw_axes.get(axis_name)
        if not isinstance(axis, Mapping):
            raise WP10RunnerError("QA_SCHEMA_FAILURE", f"axis={axis_name}")
        status = str(axis.get("status") or "").upper()
        if not status:
            raise WP10RunnerError("QA_SCHEMA_FAILURE", f"axis status={axis_name}")
        value = axis.get("value")
        reason = axis.get("reason_code")
        measurement = axis.get("measurement")
        axis_payload[axis_name] = {
            "status": status,
            "value": str(value) if value is not None else None,
            "reason_code": str(reason) if reason is not None else None,
            "measurement": str(measurement) if measurement is not None else None,
        }
    computability_status, computability_reason = _computability(axis_payload)
    scope = str(row.get("evaluation_scope_id") or "")
    record_id = str(row.get("c2_state_id") or "")
    parent_c1 = str(row.get("parent_c1_record_id") or "")
    source_lineage = {
        "source_release_id": FROZEN_SOURCE_RELEASE_ID,
        "source_commit": FROZEN_SOURCE_COMMIT,
        "source_slice_id": FROZEN_SOURCE_SLICE_ID,
        "source_manifest_sha256": FROZEN_SOURCE_MANIFEST_SHA256,
        "output_manifest_sha256": FROZEN_OUTPUT_MANIFEST_SHA256,
        "active_c2_model_release_id": FROZEN_ACTIVE_C2_RELEASE_ID,
        "c1_record_id": parent_c1,
        "c1_release_id": str(row.get("c1_release_id") or ""),
        "c1_manifest_id": str(row.get("c1_manifest_id") or ""),
        "opt_a_release_id": str(row.get("opt_a_release_id") or ""),
        "opt_a_manifest_id": str(row.get("opt_a_manifest_id") or ""),
        "parent_opt_a_bar_id": str(row.get("parent_opt_a_bar_id") or ""),
    }
    return {
        "record_id": record_id,
        "first_valid_time": str(row.get("first_valid_time") or ""),
        "instrument": "GBPUSD",
        "side": str(row.get("side") or "").upper(),
        "clock": str(row.get("clock") or ""),
        "units": "MIXED_TYPED_C2",
        "representation_schema": f"C2_TYPED_AXES:{FROZEN_ACTIVE_C2_RELEASE_ID}:{scope}",
        "source_quality": "ACCEPTED_FROZEN_C2",
        "evaluation_scope_id": scope,
        "eligibility_class": str(row.get("eligibility_class") or ""),
        "target_eligible": bool(row.get("target_eligible")),
        "computability_status": computability_status,
        "not_evaluable_reason": computability_reason,
        "native_c2": {
            "axes": axis_payload,
            "level_ids": sorted(str(item) for item in row.get("level_ids", ())),
            "container_ids": sorted(str(item) for item in row.get("container_ids", ())),
            "relation_set_id": str(row.get("relation_set_id") or ""),
            "persistence": dict(row["persistence"]) if isinstance(row.get("persistence"), Mapping) else row.get("persistence"),
            "continuity": str(row.get("continuity") or ""),
            "parameter_pack_id": str(row.get("parameter_pack_id") or ""),
        },
        "source_lineage": source_lineage,
        "source_logical_sha256": logical_sha256(dict(row)),
        "adapter_semantics": "SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION",
        "adapter_id": "SRFDI-SOURCE-ADAPTER-v0.2",
        "evaluated_reason_policy": "PRESERVE_OPTIONAL_DESCRIPTIVE_REASON_CODE",
    }


def compile_frozen_domains(
    rows: Iterable[Mapping[str, Any]], pack_registry: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    domains: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for row in rows:
        if not bool(row.get("target_eligible")):
            continue
        source = adapted_capacity_record(row)
        evaluable = source["computability_status"] == "EVALUABLE"
        requests: list[tuple[str, str | None]] = []
        if evaluable:
            requests.append(("SRFDI-R1", None))
            requests.extend(
                ("SRFDI-R6", variant)
                for variant in (
                    "SRFDI-R6-DROP-LOCATION",
                    "SRFDI-R6-DROP-MOTION",
                    "SRFDI-R6-DROP-ORGANISATION",
                    "SRFDI-R6-DROP-INTERACTION",
                    "SRFDI-R6-DROP-QUALITY",
                )
            )
        requests.extend((("SRFDI-R8", None), ("SRFDI-R9", None)))
        for implementation_class_id, variant_id in requests:
            compiled = compile_real_source_representation(
                source,
                pack_registry,
                implementation_class_id,
                source_population_id=FROZEN_POPULATION_ID,
                variant_id=variant_id,
            )
            domain_id = str(compiled["comparability_domain_id"])
            domains.setdefault(domain_id, []).append(compiled)
            key = variant_id or implementation_class_id
            counts[key] = counts.get(key, 0) + 1
    expected_counts = {
        "SRFDI-R1": 4996,
        "SRFDI-R6-DROP-LOCATION": 4996,
        "SRFDI-R6-DROP-MOTION": 4996,
        "SRFDI-R6-DROP-ORGANISATION": 4996,
        "SRFDI-R6-DROP-INTERACTION": 4996,
        "SRFDI-R6-DROP-QUALITY": 4996,
        "SRFDI-R8": 8598,
        "SRFDI-R9": 8598,
    }
    if counts != expected_counts:
        raise WP10RunnerError("REPRESENTATION_BINDING_MISMATCH", f"counts={counts}")
    for records in domains.values():
        records.sort(key=lambda item: str(item["representation_id"]))
    pair_count = sum(len(records) * (len(records) - 1) // 2 for records in domains.values())
    if len(domains) != FROZEN_DOMAIN_COUNT or pair_count != FROZEN_PAIR_COUNT:
        raise WP10RunnerError(
            "COMPARABILITY_DOMAIN_MISMATCH", f"domains={len(domains)} pairs={pair_count}"
        )
    return dict(sorted(domains.items()))
