from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    OPT_C_CONTRACT_VERSION,
    OPT_C_HORIZONS_HOURS,
    context_quality,
    event_direction,
    persistent_trigger_kind,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


B_STATE_VERSION = "B-STATE-0.3b"
B_RATIFICATION_ID = "B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH"
EXPECTED_STEP = {"15M": timedelta(minutes=15), "2H": timedelta(hours=2)}
CONTEXT_MAX_AGE_MINUTES = {"15M": 15, "2H": 120}
MARKET_TRANSITION_AXES = {"ACCEPTANCE", "DISPLACEMENT", "COMPRESSION", "INTERACTION"}


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
    return manifest


def load_jsonl_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def component(
    *,
    family: str,
    subtype: str,
    direction: str,
    evidence_layer: str,
    source_record_ids: list[str] | tuple[str, ...],
    support_level_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, object]:
    core = {
        "family": family,
        "subtype": subtype,
        "direction": direction,
        "evidence_layer": evidence_layer,
        "source_record_ids": sorted(set(source_record_ids)),
        "support_level_ids": sorted(set(support_level_ids)),
    }
    return {**core, "event_component_id": f"opt-c-component:{canonical_hash(core)}"}


def state_direction(state: str) -> str:
    if state.endswith("_UP") or state in ("DISPLACING_UP", "FRONTIER_ADVANCE_UP"):
        return "UP"
    if state.endswith("_DOWN") or state in ("DISPLACING_DOWN", "FRONTIER_ADVANCE_DOWN"):
        return "DOWN"
    if state.startswith("COMPOUND") or state == "CONFLICTING":
        return "MIXED"
    return "NONE"


def build_components(
    row: dict[str, object],
    parent: dict[str, object],
    previous_row: dict[str, object] | None,
    *,
    contiguous: bool,
) -> list[dict[str, object]]:
    components = []
    state_id = row["state_record_id"]
    parent_id = row["parent_v03a_state_record_id"]
    acceptance_state = row["acceptance_event_state"]
    if acceptance_state not in ("NONE", "CONFLICTING"):
        for item in row["acceptance_event_components"]:
            components.append(
                component(
                    family="ACCEPTANCE_FRONTIER",
                    subtype=acceptance_state,
                    direction=item["direction"],
                    evidence_layer="RATIFIED_PRIMARY_EVENT",
                    source_record_ids=[state_id, *item["trigger_term_record_ids"]],
                    support_level_ids=item["support_level_ids"],
                )
            )

    reasons = set(parent["reason_codes"])
    previous_displacement = previous_row["displacement_state"] if previous_row else None
    if "DISPLACEMENT_AXIS_REFRESHED" in reasons:
        trigger_kind = persistent_trigger_kind(previous_displacement, row["displacement_state"], "NONE")
        if not contiguous and trigger_kind == "REFRESH":
            trigger_kind = "REFRESH_AFTER_GAP"
        components.append(
            component(
                family="DISPLACEMENT",
                subtype=trigger_kind,
                direction=state_direction(row["displacement_state"]),
                evidence_layer="RATIFIED_STATE_TRIGGER",
                source_record_ids=[state_id, parent_id],
            )
        )
    if "DISPLACEMENT_AXIS_EXITED" in reasons:
        prior_state = previous_displacement or "NONE"
        components.append(
            component(
                family="DISPLACEMENT",
                subtype="EXIT",
                direction=state_direction(prior_state),
                evidence_layer="RATIFIED_STATE_EXIT",
                source_record_ids=[state_id, parent_id],
            )
        )

    previous_compression = previous_row["compression_state"] if previous_row else None
    if "COMPRESSION_AXIS_REFRESHED" in reasons:
        trigger_kind = persistent_trigger_kind(previous_compression, row["compression_state"], "NORMAL")
        if not contiguous and trigger_kind == "REFRESH":
            trigger_kind = "REFRESH_AFTER_GAP"
        components.append(
            component(
                family="COMPRESSION",
                subtype=trigger_kind,
                direction="NONE",
                evidence_layer="RATIFIED_STATE_TRIGGER",
                source_record_ids=[state_id, parent_id],
            )
        )
    if "COMPRESSION_AXIS_EXITED" in reasons:
        components.append(
            component(
                family="COMPRESSION",
                subtype="EXIT",
                direction="NONE",
                evidence_layer="RATIFIED_STATE_EXIT",
                source_record_ids=[state_id, parent_id],
            )
        )

    if row["interaction_state"] != "NONE":
        for item in row["interaction_components"]:
            components.append(
                component(
                    family="INTERACTION",
                    subtype=item["semantic_state"],
                    direction=item["direction"],
                    evidence_layer="RATIFIED_ONE_BAR_INTERACTION",
                    source_record_ids=[state_id, *item["trigger_term_record_ids"]],
                    support_level_ids=item["support_level_ids"],
                )
            )
    return sorted(components, key=lambda item: item["event_component_id"])


def context_record(
    *,
    anchor_time: datetime,
    context_timeframe: str,
    context_times: list[datetime],
    context_rows: list[dict[str, object]],
) -> dict[str, object]:
    index = bisect_right(context_times, anchor_time) - 1
    row = context_rows[index] if index >= 0 else None
    at = context_times[index] if index >= 0 else None
    quality = context_quality(
        anchor_time,
        at,
        maximum_age_minutes=CONTEXT_MAX_AGE_MINUTES[context_timeframe],
    )
    return {
        "timeframe": context_timeframe,
        "state_record_id": row["state_record_id"] if row else None,
        "state_close_time": at.astimezone(timezone.utc).isoformat() if at else None,
        "age_minutes": int((anchor_time - at).total_seconds() // 60) if at else None,
        "quality": quality,
        "state_snapshot": (
            {
                "acceptance_event_state": row["acceptance_event_state"],
                "displacement_state": row["displacement_state"],
                "compression_state": row["compression_state"],
                "interaction_state": row["interaction_state"],
                "quality_state": row["quality_state"],
            }
            if row
            else None
        ),
    }


def make_anchor(
    *,
    timeframe: str,
    row: dict[str, object],
    parent: dict[str, object],
    bar,
    components: list[dict[str, object]],
    transitions: list[dict[str, object]],
    context: dict[str, object],
    path_start_available: bool,
    path_source_release_id: str,
) -> dict[str, object]:
    anchor_core = {
        "instrument_id": row["instrument_id"],
        "event_timeframe": timeframe,
        "anchor_time": row["close_time"],
        "anchor_bar_id": bar.bar_id,
        "b_state_record_id": row["state_record_id"],
    }
    anchor_id = f"opt-c-anchor:{canonical_hash(anchor_core)}"
    market_transitions = [item for item in transitions if item["axis"] in MARKET_TRANSITION_AXES]
    return {
        **anchor_core,
        "event_anchor_id": anchor_id,
        "anchor_price": str(bar.close),
        "anchor_price_side": bar.price_side,
        "anchor_source_release_id": bar.source_release_id,
        "event_direction": event_direction(components),
        "event_families": sorted({item["family"] for item in components}),
        "event_components": components,
        "event_component_count": len(components),
        "compound_event": len(components) > 1,
        "market_axis_transitions": market_transitions,
        "b_state_snapshot": {
            "acceptance_event_state": row["acceptance_event_state"],
            "displacement_state": row["displacement_state"],
            "compression_state": row["compression_state"],
            "interaction_state": row["interaction_state"],
            "quality_state": row["quality_state"],
            "acceptance_frontier_summary": row["acceptance_frontier_summary"],
            "full_relation_inventory_hash": row["full_relation_inventory_hash"],
        },
        "parent_v03a_state_record_id": parent["state_record_id"],
        "cross_clock_context": context,
        "cross_clock_event_group_id": None,
        "forward_path_authority": {
            "timeframe": "15M",
            "source_release_id": path_source_release_id,
            "price_side": "BID",
            "anchor_start_bar_available": path_start_available,
            "coverage_status": "PENDING_STRICT_HORIZON_AUDIT",
        },
        "horizons_hours": list(OPT_C_HORIZONS_HOURS),
        "overlap_policy": "SEPARATE_OBSERVATIONS_WITH_EXPLICIT_OUTCOME_WINDOW_FLAGS",
        "eligibility_status": "ELIGIBLE_PENDING_FORWARD_PATH_COVERAGE",
        "opt_c_contract_version": OPT_C_CONTRACT_VERSION,
        "b_state_contract_version": B_STATE_VERSION,
        "b_state_ratification_id": B_RATIFICATION_ID,
    }


def summarize(anchors: list[dict[str, object]]) -> dict[str, object]:
    families = Counter()
    subtypes = Counter()
    directions = Counter()
    contexts = Counter()
    monthly = Counter()
    component_counts = Counter()
    path_start_available = 0
    for anchor in anchors:
        directions[anchor["event_direction"]] += 1
        contexts[anchor["cross_clock_context"]["quality"]] += 1
        anchor_time = datetime.fromisoformat(anchor["anchor_time"])
        event_timeframe = anchor["event_timeframe"]
        monthly[(anchor_time - EXPECTED_STEP[event_timeframe]).strftime("%Y-%m")] += 1
        component_counts[str(anchor["event_component_count"])] += 1
        path_start_available += int(anchor["forward_path_authority"]["anchor_start_bar_available"])
        for item in anchor["event_components"]:
            families[item["family"]] += 1
            subtypes[f"{item['family']}:{item['subtype']}"] += 1
    return {
        "anchors": len(anchors),
        "event_components": sum(component_counts_key * count for component_counts_key, count in ((int(k), v) for k, v in component_counts.items())),
        "compound_anchors": sum(1 for anchor in anchors if anchor["compound_event"]),
        "multi_family_anchors": sum(1 for anchor in anchors if len(anchor["event_families"]) > 1),
        "family_component_counts": dict(sorted(families.items())),
        "subtype_component_counts": dict(sorted(subtypes.items())),
        "direction_counts": dict(sorted(directions.items())),
        "component_count_distribution": dict(sorted(component_counts.items(), key=lambda item: int(item[0]))),
        "cross_clock_context_quality_counts": dict(sorted(contexts.items())),
        "path_start_available": path_start_available,
        "path_start_unavailable": len(anchors) - path_start_available,
        "monthly_anchor_counts": dict(sorted(monthly.items())),
    }


def write_report(output: Path, summaries: dict[str, object], cross_clock_groups: int) -> Path:
    lines = [
        "# OVC OPT-C Event-Anchor Ledger Report v0.1",
        "",
        "**Status:** `CONTRACT RATIFIED — EVENT LEDGER BUILT — OUTCOMES NOT MEASURED`  ",
        f"**Contract:** `{OPT_C_CONTRACT_VERSION}`  ",
        "**Outcome / edge / execution authority:** `NONE`",
        "",
        "## Ledger coverage",
        "",
        "| Clock | Anchors | Components | Compound anchors | Multi-family anchors | 15M path start available |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for timeframe in ("15M", "2H"):
        item = summaries[timeframe]
        lines.append(
            f"| {timeframe} | {item['anchors']:,} | {item['event_components']:,} | "
            f"{item['compound_anchors']:,} | {item['multi_family_anchors']:,} | "
            f"{item['path_start_available']:,} |"
        )
    lines.extend([
        "",
        f"Same-time cross-clock event groups: **{cross_clock_groups:,}**.",
        "",
        "## Component counts",
        "",
        "| Clock | Acceptance frontier | Displacement | Compression | Interaction |",
        "|---|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        counts = summaries[timeframe]["family_component_counts"]
        lines.append(
            f"| {timeframe} | {counts.get('ACCEPTANCE_FRONTIER', 0):,} | "
            f"{counts.get('DISPLACEMENT', 0):,} | {counts.get('COMPRESSION', 0):,} | "
            f"{counts.get('INTERACTION', 0):,} |"
        )
    lines.extend([
        "",
        "Every row is anchored to an OPT-A event-bar close and one ratified B-STATE record. Simultaneous evidence is compound in that row; no term is duplicated into a second outcome observation.",
        "",
        "## Next gate",
        "",
        "The next build is the strict 15M forward-path coverage and censoring audit for all seven horizons. No forward price, excursion or outcome value has entered this ledger release.",
    ])
    path = output / "OVC_OPT_C_EVENT_ANCHOR_LEDGER_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--parent-v03a-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seal_root = args.seal_root.resolve()
    state_root = args.state_root.resolve()
    parent_root = args.parent_v03a_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json").exists():
        raise FileExistsError("OPT-C event ledger already finalized")

    seal = verify_seal(seal_root)
    state_manifest = verify_manifest(state_root, "B_STATE_0_3B_RATIFIED_MANIFEST.json")
    parent_manifest = verify_manifest(parent_root, "B_STATE_0_3A_REPLAY_MANIFEST.json")
    if state_manifest["parent_v03a_manifest_hash"] != parent_manifest["manifest_hash"]:
        raise ValueError("ratified state/parent lineage mismatch")
    if parent_manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("B-STATE/OPT-A seal lineage mismatch")

    bars = {
        timeframe: read_canonical_bars(seal_root / f"canonical/accepted_{timeframe.lower()}.csv")
        for timeframe in ("15M", "2H")
    }
    bar_by_close = {
        timeframe: {bar.close_time: bar for bar in items}
        for timeframe, items in bars.items()
    }
    path_open_times = {bar.open_time for bar in bars["15M"]}
    states = {
        timeframe: load_jsonl_gzip(state_root / f"ratified_parallel_axis_state_stream_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    parents = {
        timeframe: load_jsonl_gzip(parent_root / f"acceptance_relation_state_stream_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    transitions = {
        timeframe: load_jsonl_gzip(state_root / f"ratified_parallel_axis_transitions_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    transition_index = {
        timeframe: defaultdict(list)
        for timeframe in ("15M", "2H")
    }
    for timeframe in ("15M", "2H"):
        for item in transitions[timeframe]:
            transition_index[timeframe][item["at"]].append(item)

    state_times = {
        timeframe: [datetime.fromisoformat(row["close_time"]) for row in states[timeframe]]
        for timeframe in ("15M", "2H")
    }
    anchors_by_timeframe: dict[str, list[dict[str, object]]] = {"15M": [], "2H": []}
    path_source_release_id = bars["15M"][0].source_release_id
    for timeframe in ("15M", "2H"):
        if len(states[timeframe]) != len(parents[timeframe]):
            raise ValueError("state/parent cardinality mismatch")
        previous_row = None
        previous_time = None
        context_timeframe = "2H" if timeframe == "15M" else "15M"
        for row, parent in zip(states[timeframe], parents[timeframe]):
            if row["close_time"] != parent["close_time"]:
                raise ValueError("state/parent timestamp mismatch")
            if row["parent_v03a_state_record_id"] != parent["state_record_id"]:
                raise ValueError("state/parent record lineage mismatch")
            at = datetime.fromisoformat(row["close_time"])
            contiguous = previous_time is not None and at - previous_time == EXPECTED_STEP[timeframe]
            components = build_components(row, parent, previous_row, contiguous=contiguous)
            if components:
                bar = bar_by_close[timeframe].get(at)
                if bar is None:
                    raise ValueError("eligible event has no canonical anchor bar")
                context = context_record(
                    anchor_time=at,
                    context_timeframe=context_timeframe,
                    context_times=state_times[context_timeframe],
                    context_rows=states[context_timeframe],
                )
                anchors_by_timeframe[timeframe].append(
                    make_anchor(
                        timeframe=timeframe,
                        row=row,
                        parent=parent,
                        bar=bar,
                        components=components,
                        transitions=sorted(
                            transition_index[timeframe].get(row["close_time"], []),
                            key=lambda item: item["transition_record_id"],
                        ),
                        context=context,
                        path_start_available=at in path_open_times,
                        path_source_release_id=path_source_release_id,
                    )
                )
            previous_row = row
            previous_time = at

    anchors_at = defaultdict(set)
    for timeframe, anchors in anchors_by_timeframe.items():
        for anchor in anchors:
            anchors_at[anchor["anchor_time"]].add(timeframe)
    cross_clock_times = {at for at, clocks in anchors_at.items() if clocks == {"15M", "2H"}}
    for anchors in anchors_by_timeframe.values():
        for anchor in anchors:
            if anchor["anchor_time"] in cross_clock_times:
                group_core = {"instrument_id": anchor["instrument_id"], "anchor_time": anchor["anchor_time"]}
                anchor["cross_clock_event_group_id"] = f"opt-c-cross-clock:{canonical_hash(group_core)}"

    artifacts = []
    summaries = {}
    for timeframe in ("15M", "2H"):
        anchors = anchors_by_timeframe[timeframe]
        path = output / f"opt_c_event_anchor_ledger_{timeframe.lower()}.jsonl.gz"
        writer = DeterministicJsonlGzipWriter(path)
        seen = set()
        for anchor in anchors:
            if anchor["event_anchor_id"] in seen:
                raise ValueError("duplicate event anchor ID")
            seen.add(anchor["event_anchor_id"])
            writer.write(anchor)
        writer.close()
        summaries[timeframe] = {
            **summarize(anchors),
            "ledger_canonical_jsonl_hash": writer.canonical_jsonl_hash,
        }
        artifacts.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})

    summary_path = output / "opt_c_event_anchor_ledger_summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, summaries, len(cross_clock_times))
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/OPT_C_OUTCOME_0_1_APPROVAL_RECORD.md",
        ROOT / "contracts/OVC_OPT_C_NEUTRAL_FORWARD_OUTCOME_CONTRACT_v0_1.md",
        ROOT / "contracts/B_STATE_0_3B_RATIFICATION_RECORD.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-C-EVENT-LEDGER-GBPUSD-2026H1-v0.1",
        "status": "CONTRACT_RATIFIED_EVENT_LEDGER_BUILT_OUTCOMES_NOT_MEASURED",
        "generated_date": "2026-07-19",
        "opt_c_contract_version": OPT_C_CONTRACT_VERSION,
        "opt_a_seal_hash": seal["seal_hash"],
        "b_state_manifest_hash": state_manifest["manifest_hash"],
        "parent_v03a_manifest_hash": parent_manifest["manifest_hash"],
        "horizons_hours": list(OPT_C_HORIZONS_HOURS),
        "forward_path_authority": {
            "timeframe": "15M",
            "source_release_id": path_source_release_id,
            "price_side": "BID",
            "strict_complete_path": True,
        },
        "cross_clock_event_groups": len(cross_clock_times),
        "results": summaries,
        "artifacts": artifacts,
        "implementation_hashes": {
            "opt_c.py": sha256(ROOT / "src/ovc_opt_b/opt_c.py"),
            "build_opt_c_event_anchor_ledger.py": sha256(Path(__file__).resolve()),
            "test_opt_c.py": sha256(ROOT / "tests/test_opt_c.py"),
        },
        "authority_boundary": "Event eligibility and lineage only. No forward price, outcome, edge, recommendation, risk or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
