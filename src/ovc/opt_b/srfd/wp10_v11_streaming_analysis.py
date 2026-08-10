from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .sensitivity import build_correspondence, sensitivity_metrics
from .serialization import canonical_json_bytes
from .stability_metrics_v04 import (
    ambiguity_rate,
    chronological_stability,
    family_survival_rate,
    qualifies_adjacent_sensitivity,
    qualifies_cross_method,
    residual_rate,
)
from .wp10_v07_analysis import build_invariant_core_support_exact, method_disagreement_exact
from .wp10_v07_contract import ConfigurationDescriptor, SENSITIVITY_LADDERS, WP10RunnerError
from .wp10_v07_family import frozen_configuration_plan


@dataclass(frozen=True)
class FileBackedDomainAnalysis:
    path: Path
    domain_id: str
    configuration_count: int
    logical_hash: str
    raw_sha256: str
    raw_bytes: int


def _analysis_descriptor(preparation: Mapping[str, Any], descriptor: ConfigurationDescriptor) -> dict[str, Any]:
    return {
        "configuration_id": descriptor.configuration_id,
        "representation_id": str(preparation["representation_id"]),
        "distance_id": "GOWER_MIXED",
        "family_method_id": descriptor.family_method_id,
        "shared_minimum_support": descriptor.minimum_support,
        "parameters": descriptor.parameters,
    }


def _copy_file(source: Path, write) -> None:
    with source.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                return
            write(block)


def _emit_top_level(
    write,
    *,
    values: Mapping[str, Any],
    correspondence_spool: Path,
    logical_hash: str | None,
) -> None:
    keys = set(values)
    keys.add("family_correspondence_split_merge")
    if logical_hash is not None:
        keys.add("logical_hash")
    write(b"{")
    first = True
    for key in sorted(keys):
        if not first:
            write(b",")
        first = False
        write(canonical_json_bytes(key))
        write(b":")
        if key == "family_correspondence_split_merge":
            _copy_file(correspondence_spool, write)
        elif key == "logical_hash":
            write(canonical_json_bytes(logical_hash))
        else:
            write(canonical_json_bytes(values[key]))
    write(b"}")


def stream_analyse_domain_to_file(
    records: Sequence[Mapping[str, Any]],
    preparation: Mapping[str, Any],
    catalogs: Mapping[str, Mapping[str, Any]],
    output_path: Path,
) -> FileBackedDomainAnalysis:
    """Write the exact v0.7 domain-analysis JSON without retaining correspondence rows.

    Scientific order, qualification rules, correspondence construction and logical
    identity are unchanged. The only change is that the potentially dominant
    ``family_correspondence_split_merge`` list is emitted one qualifying ordered
    pair at a time to disk.
    """
    domain_id = str(preparation["domain_id"])
    descriptors = frozen_configuration_plan(domain_id)
    expected_ids = {item.configuration_id for item in descriptors}
    if set(catalogs) != expected_ids:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", "analysis catalog set mismatch")
    descriptor_map = {
        item.configuration_id: _analysis_descriptor(preparation, item) for item in descriptors
    }
    ordered_ids = sorted(catalogs)
    first_valid = {
        str(record["representation_id"]): str(record["first_valid_time"]) for record in records
    }
    per_configuration = [
        {
            "configuration_id": config_id,
            "residual_rate": residual_rate(catalogs[config_id]),
            "chronological_stability": chronological_stability(catalogs[config_id], first_valid),
        }
        for config_id in ordered_ids
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    correspondence_spool = output_path.with_suffix(output_path.suffix + ".correspondence.tmp")
    pair_ledger: list[dict[str, Any]] = []
    stability_pair_rows: list[dict[str, Any]] = []
    try:
        with correspondence_spool.open("wb") as spool:
            spool.write(b"[")
            first_row = True
            for left_id, right_id in combinations(ordered_ids, 2):
                left_desc = descriptor_map[left_id]
                right_desc = descriptor_map[right_id]
                sensitivity_ok = qualifies_adjacent_sensitivity(left_desc, right_desc, SENSITIVITY_LADDERS)
                cross_method_ok = qualifies_cross_method(left_desc, right_desc)
                pair_ledger.append(
                    {
                        "left_configuration_id": left_id,
                        "right_configuration_id": right_id,
                        "adjacent_sensitivity_qualifies": sensitivity_ok,
                        "cross_method_qualifies": cross_method_ok,
                        "status": "QUALIFYING" if sensitivity_ok or cross_method_ok else "NONQUALIFYING_FROZEN_PAIR",
                    }
                )
                if not (sensitivity_ok or cross_method_ok):
                    continue
                metric_id = (
                    "CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR"
                    if sensitivity_ok
                    else "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR"
                )
                for anchor_id, counterpart_id in ((left_id, right_id), (right_id, left_id)):
                    anchor = catalogs[anchor_id]
                    counterpart = catalogs[counterpart_id]
                    row = {
                        "metric_pair_class": metric_id,
                        "anchor_configuration_id": anchor_id,
                        "counterpart_configuration_id": counterpart_id,
                        "correspondence": build_correspondence(anchor, counterpart),
                    }
                    if not first_row:
                        spool.write(b",")
                    first_row = False
                    spool.write(canonical_json_bytes(row))
                    stability_pair_rows.append(
                        {
                            "metric_id": metric_id,
                            "anchor_configuration_id": anchor_id,
                            "counterpart_configuration_id": counterpart_id,
                            "survival_or_exact_correspondence": family_survival_rate(anchor, counterpart, metric_id=metric_id),
                            "ambiguity": ambiguity_rate(anchor, counterpart),
                        }
                    )
            spool.write(b"]")
            spool.flush()
            os.fsync(spool.fileno())

        catalog_values = [catalogs[key] for key in ordered_ids]
        values = {
            "schema": "ovc-srfdi-wp10-v07-domain-analysis/v1",
            "domain_id": domain_id,
            "configuration_count": len(ordered_ids),
            "sensitivity_metrics": sensitivity_metrics(catalog_values),
            "per_configuration_stability": per_configuration,
            "pair_qualification_ledger": pair_ledger,
            "ordered_pair_stability": stability_pair_rows,
            "invariant_core_support": build_invariant_core_support_exact(catalog_values),
            "method_disagreement": method_disagreement_exact(catalog_values),
            "scientific_disposition": "NOT_PERFORMED_WP10_EVIDENCE_ONLY_PENDING_G10",
            "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
        }

        payload_hasher = sha256()
        _emit_top_level(payload_hasher.update, values=values, correspondence_spool=correspondence_spool, logical_hash=None)
        logical_hash = payload_hasher.hexdigest()

        raw_hasher = sha256()
        raw_bytes = 0
        tmp = output_path.with_name(output_path.name + ".tmp")
        with tmp.open("wb") as target:
            def write(data: bytes) -> None:
                nonlocal raw_bytes
                target.write(data)
                raw_hasher.update(data)
                raw_bytes += len(data)
            _emit_top_level(write, values=values, correspondence_spool=correspondence_spool, logical_hash=logical_hash)
            target.flush()
            os.fsync(target.fileno())
        os.replace(tmp, output_path)
        return FileBackedDomainAnalysis(
            path=output_path,
            domain_id=domain_id,
            configuration_count=len(ordered_ids),
            logical_hash=logical_hash,
            raw_sha256=raw_hasher.hexdigest(),
            raw_bytes=raw_bytes,
        )
    finally:
        correspondence_spool.unlink(missing_ok=True)
