from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, verify_seal  # noqa: E402
from ovc_opt_b import OPT_C_CONTRACT_VERSION, OPT_C_HORIZONS_HOURS, event_direction  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    return manifest


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for item in value.values():
            keys.update(recursive_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(recursive_keys(item))
        return keys
    return set()


def load_states(path: Path) -> dict[str, dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return {row["close_time"]: row for row in (json.loads(line) for line in handle)}


def validate_stream(
    path: Path,
    *,
    expected_rows: int,
    bars_by_close: dict[datetime, object],
    states_by_close: dict[str, dict[str, object]],
    path_open_times: set[datetime],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    prohibited = {
        "endpoint_price",
        "endpoint_return",
        "maximum_upward_excursion",
        "maximum_downward_excursion",
        "mfe",
        "mae",
        "profit",
        "loss",
        "win",
        "execution",
    }
    anchors = []
    anchor_ids = set()
    anchor_times = set()
    components = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            anchors.append(row)
            if row["opt_c_contract_version"] != OPT_C_CONTRACT_VERSION:
                raise ValueError(f"wrong OPT-C contract version in {path.name}")
            if row["horizons_hours"] != list(OPT_C_HORIZONS_HOURS):
                raise ValueError(f"wrong horizon set in {path.name}")
            if row["eligibility_status"] != "ELIGIBLE_PENDING_FORWARD_PATH_COVERAGE":
                raise ValueError(f"event eligibility was altered in {path.name}")
            if recursive_keys(row).intersection(prohibited):
                raise ValueError(f"measured outcome field entered {path.name}")
            if row["event_anchor_id"] in anchor_ids:
                raise ValueError(f"duplicate anchor ID in {path.name}")
            anchor_ids.add(row["event_anchor_id"])
            anchor_key = (row["event_timeframe"], row["anchor_time"])
            if anchor_key in anchor_times:
                raise ValueError(f"duplicate clock/bar observation in {path.name}")
            anchor_times.add(anchor_key)
            if not row["event_components"]:
                raise ValueError(f"componentless eligible anchor in {path.name}")
            component_ids = [item["event_component_id"] for item in row["event_components"]]
            if len(component_ids) != len(set(component_ids)):
                raise ValueError(f"duplicate component inside anchor in {path.name}")
            components += len(component_ids)
            if row["event_direction"] != event_direction(row["event_components"]):
                raise ValueError(f"event direction mismatch in {path.name}")

            at = datetime.fromisoformat(row["anchor_time"])
            bar = bars_by_close.get(at)
            if bar is None or row["anchor_bar_id"] != bar.bar_id or row["anchor_price"] != str(bar.close):
                raise ValueError(f"OPT-A event-bar anchor mismatch in {path.name}")
            state = states_by_close.get(row["anchor_time"])
            if state is None or row["b_state_record_id"] != state["state_record_id"]:
                raise ValueError(f"B-STATE lineage mismatch in {path.name}")
            context_time = row["cross_clock_context"]["state_close_time"]
            if context_time and datetime.fromisoformat(context_time) > at:
                raise ValueError(f"future cross-clock context in {path.name}")
            expected_start = at in path_open_times
            if row["forward_path_authority"]["anchor_start_bar_available"] != expected_start:
                raise ValueError(f"path-start availability mismatch in {path.name}")
            if row["forward_path_authority"]["coverage_status"] != "PENDING_STRICT_HORIZON_AUDIT":
                raise ValueError(f"outcome coverage was measured prematurely in {path.name}")
    if len(anchors) != expected_rows:
        raise ValueError(f"row-count mismatch in {path.name}: {len(anchors)} != {expected_rows}")
    return (
        {
            "path": path.name,
            "rows": len(anchors),
            "unique_anchor_ids": len(anchor_ids),
            "event_components": components,
            "gzip_integrity": "PASS",
        },
        anchors,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--parent-v03a-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    seal_root = args.seal_root.resolve()
    state_root = args.state_root.resolve()
    parent_root = args.parent_v03a_root.resolve()
    manifest = verify_manifest(root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    state_manifest = verify_manifest(state_root, "B_STATE_0_3B_RATIFIED_MANIFEST.json")
    parent_manifest = verify_manifest(parent_root, "B_STATE_0_3A_REPLAY_MANIFEST.json")
    seal = verify_seal(seal_root)
    if manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("OPT-C/OPT-A seal lineage mismatch")
    if manifest["b_state_manifest_hash"] != state_manifest["manifest_hash"]:
        raise ValueError("OPT-C/B-STATE lineage mismatch")
    if manifest["parent_v03a_manifest_hash"] != parent_manifest["manifest_hash"]:
        raise ValueError("OPT-C/parent v0.3a lineage mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    bars = {
        timeframe: read_canonical_bars(seal_root / f"canonical/accepted_{timeframe.lower()}.csv")
        for timeframe in ("15M", "2H")
    }
    bars_by_close = {
        timeframe: {bar.close_time: bar for bar in items}
        for timeframe, items in bars.items()
    }
    path_open_times = {bar.open_time for bar in bars["15M"]}
    states = {
        timeframe: load_states(state_root / f"ratified_parallel_axis_state_stream_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    stream_checks = []
    all_anchors = {}
    for timeframe in ("15M", "2H"):
        check, anchors = validate_stream(
            root / f"opt_c_event_anchor_ledger_{timeframe.lower()}.jsonl.gz",
            expected_rows=manifest["results"][timeframe]["anchors"],
            bars_by_close=bars_by_close[timeframe],
            states_by_close=states[timeframe],
            path_open_times=path_open_times,
        )
        if check["event_components"] != manifest["results"][timeframe]["event_components"]:
            raise ValueError(f"component-count mismatch in {timeframe}")
        if sum(manifest["results"][timeframe]["monthly_anchor_counts"].values()) != check["rows"]:
            raise ValueError(f"monthly coverage mismatch in {timeframe}")
        stream_checks.append(check)
        all_anchors[timeframe] = anchors

    anchor_times = {
        timeframe: {row["anchor_time"] for row in anchors}
        for timeframe, anchors in all_anchors.items()
    }
    expected_cross_times = anchor_times["15M"].intersection(anchor_times["2H"])
    group_counts = Counter()
    for anchors in all_anchors.values():
        for row in anchors:
            group_id = row["cross_clock_event_group_id"]
            if row["anchor_time"] in expected_cross_times:
                if not group_id:
                    raise ValueError("missing same-time cross-clock group")
                group_counts[group_id] += 1
            elif group_id is not None:
                raise ValueError("spurious cross-clock event group")
    if len(group_counts) != manifest["cross_clock_event_groups"] or any(count != 2 for count in group_counts.values()):
        raise ValueError("cross-clock grouping mismatch")

    determinism: dict[str, object] = {"checked": False}
    if args.determinism_root:
        prior = verify_manifest(args.determinism_root.resolve(), "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
        comparisons = {
            timeframe: manifest["results"][timeframe]["ledger_canonical_jsonl_hash"]
            == prior["results"][timeframe]["ledger_canonical_jsonl_hash"]
            for timeframe in ("15M", "2H")
        }
        if not all(comparisons.values()):
            raise ValueError("independent ledger determinism mismatch")
        determinism = {"checked": True, "all_canonical_hashes_match": True, "comparisons": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "cross_clock_groups": len(group_counts),
        "determinism": determinism,
        "semantic_controls": {
            "one_anchor_per_clock_bar": True,
            "compound_components_not_duplicated": True,
            "event_bar_prices_match_opt_a": True,
            "b_state_lineage_matches": True,
            "future_context_absent": True,
            "measured_outcomes_absent": True,
        },
        "authority_boundary": "Validated event eligibility and lineage only; no forward outcome, edge, recommendation, risk or execution authority.",
    }
    (root / "OPT_C_EVENT_ANCHOR_LEDGER_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-C Event-Anchor Ledger Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "Every anchor ID, clock/bar key, component, OPT-A close price, B-STATE record, cross-clock context, path-start flag, artifact hash and canonical ledger hash passed. No measured forward outcome entered the ledger.",
    ]
    (root / "OPT_C_EVENT_ANCHOR_LEDGER_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
