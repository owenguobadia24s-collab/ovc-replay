from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    PersistentState,
    RATIFIED_STRUCTURAL_ONLY_POLICY,
    StateEvidence,
    apply_trigger,
    build_level_lifecycles,
    contiguous_segments,
    lifecycle_to_dict,
    make_neutral_exit,
    neutral_exit_predicate,
    resolve_compound_trigger,
)
from ovc_opt_b.primitives import atr_before  # noqa: E402
from run_complete_opt_b_replay import (  # noqa: E402
    DeterministicJsonlGzipWriter,
    canonical_hash,
    load_registry,
)
from run_relevance_semantic_sensitivity_review import acceptance_times, verify_replay  # noqa: E402


def evidence_from_row(row: dict) -> StateEvidence | None:
    if row["status"] == "AMBIGUOUS":
        return StateEvidence(1, "AMBIGUOUS", row["direction"], row["reference_level_id"], row["term_record_id"])
    if row["status"] != "CONFIRMED":
        return None
    term = row["term_id"]
    direction = row["direction"]
    level = row["reference_level_id"]
    if term == "B.TERM.ACCEPTANCE.v0.1":
        return StateEvidence(2, "ACCEPTED_ABOVE" if direction == "UP" else "ACCEPTED_BELOW", direction, level, row["term_record_id"])
    if term == "B.TERM.RECLAIM.v0.1":
        return StateEvidence(3, "RECLAIMED_ABOVE" if direction == "UP" else "RECLAIMED_BELOW", direction, level, row["term_record_id"])
    if term == "B.TERM.REJECTION.v0.1":
        return StateEvidence(4, f"REJECTED_{direction}", direction, level, row["term_record_id"])
    if term == "B.TERM.DISPLACEMENT.v0.1":
        return StateEvidence(5, f"DISPLACING_{direction}", direction, None, row["term_record_id"])
    if term == "B.TERM.COMPRESSION.v0.1":
        return StateEvidence(6, "COMPRESSED", "NONE", None, row["term_record_id"])
    return None


def neutral_exit_to_dict(record) -> dict[str, object]:
    return {
        "exit_record_id": record.exit_record_id,
        "prior_state": record.prior_state,
        "first_candidate_time": record.first_candidate_time.astimezone(timezone.utc).isoformat(),
        "confirmed_at": record.confirmed_at.astimezone(timezone.utc).isoformat(),
        "reason": record.reason,
        "input_bar_ids": list(record.input_bar_ids),
        "state_contract_version": "B-STATE-0.2",
    }


def state_record(
    *,
    bar,
    current: PersistentState,
    exit_pending_count: int,
    exit_pending_reason: str | None,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    core = {
        "instrument_id": bar.instrument_id,
        "timeframe": bar.timeframe,
        "close_time": bar.close_time.astimezone(timezone.utc).isoformat(),
        "semantic_state": current.semantic_state,
        "precedence_rank": current.rank,
        "support_level_ids": list(current.support_level_ids),
        "trigger_term_record_ids": list(current.trigger_term_record_ids),
        "state_since": current.state_since.astimezone(timezone.utc).isoformat(),
        "exit_pending_count": exit_pending_count,
        "exit_pending_reason": exit_pending_reason,
        "reason_codes": list(reason_codes),
        "state_contract_version": "B-STATE-0.2",
        "relevance_policy_id": RATIFIED_STRUCTURAL_ONLY_POLICY.policy_id,
    }
    return {**core, "state_record_id": f"state:{canonical_hash(core)}"}


def verify_review(path: Path, seal_hash: str, replay_hash: str) -> dict:
    manifest = json.loads((path / "RELEVANCE_REVIEW_MANIFEST.json").read_text(encoding="utf-8"))
    expected = manifest.pop("manifest_hash")
    if canonical_hash(manifest) != expected:
        raise ValueError("relevance review manifest hash mismatch")
    manifest["manifest_hash"] = expected
    if manifest["opt_a_seal_hash"] != seal_hash or manifest["complete_replay_manifest_hash"] != replay_hash:
        raise ValueError("relevance review authority chain mismatch")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "COMPOUND_STATE_REPLAY_MANIFEST.json").exists():
        raise FileExistsError("compound state replay already finalized")

    seal = verify_seal(args.seal_root.resolve())
    all_results = {}
    artifacts = []
    registry_manifest = replay_manifest = review_manifest = None
    for timeframe in ("15M", "2H"):
        registry, registry_manifest = load_registry(args.registry_root.resolve(), timeframe)
        replay_manifest = verify_replay(args.replay_root.resolve(), seal, registry_manifest)
        review_manifest = verify_review(args.review_root.resolve(), seal["seal_hash"], replay_manifest["manifest_hash"])
        bars = read_canonical_bars(args.seal_root.resolve() / f"canonical/accepted_{timeframe.lower()}.csv")
        level_prices = {level.level_id: level.price for level in registry.levels}
        term_path = args.replay_root.resolve() / f"term_records_{timeframe.lower()}.jsonl.gz"
        accepted = acceptance_times(term_path)
        lifecycles = build_level_lifecycles(
            registry.levels,
            policy=RATIFIED_STRUCTURAL_ONLY_POLICY,
            acceptance_times=accepted,
        )
        lifecycle_map = {item.level_id: item for item in lifecycles}
        lifecycle_path = output / f"ratified_lifecycles_{timeframe.lower()}.jsonl"
        lifecycle_path.write_text(
            "".join(json.dumps(lifecycle_to_dict(item), sort_keys=True, separators=(",", ":")) + "\n" for item in lifecycles),
            encoding="utf-8",
        )

        evidence_by_time: dict[datetime, list[StateEvidence]] = defaultdict(list)
        compression_failed: set[datetime] = set()
        import gzip
        with gzip.open(term_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                at = datetime.fromisoformat(row["first_valid_time"])
                if row["term_id"] == "B.TERM.COMPRESSION.v0.1" and row["status"] == "FAILED":
                    compression_failed.add(at)
                level_id = row["reference_level_id"]
                anchor = datetime.fromisoformat(row["anchor_time"])
                if level_id is not None and not lifecycle_map[level_id].is_relevant(anchor):
                    continue
                evidence = evidence_from_row(row)
                if evidence is not None:
                    evidence_by_time[at].append(evidence)

        triggers = {at: resolve_compound_trigger(items) for at, items in evidence_by_time.items()}
        state_path = output / f"compound_state_stream_{timeframe.lower()}.jsonl.gz"
        exit_path = output / f"neutral_exit_records_{timeframe.lower()}.jsonl.gz"
        conflict_path = output / f"conflicting_state_examples_{timeframe.lower()}.jsonl"
        state_writer = DeterministicJsonlGzipWriter(state_path)
        exit_writer = DeterministicJsonlGzipWriter(exit_path)
        state_counts = Counter()
        reason_counts = Counter()
        exit_counts = Counter()
        suppressed = 0
        conflicts = 0
        current = PersistentState("NEUTRAL", None, (), (), bars[0].close_time)
        pending_count = 0
        pending_reason = None
        pending_bar = None
        first_segment = True
        with conflict_path.open("w", encoding="utf-8", newline="\n") as conflict_handle:
            for segment in contiguous_segments(bars):
                gap_carry = not first_segment and current.semantic_state != "NEUTRAL"
                first_segment = False
                pending_count = 0
                pending_reason = None
                pending_bar = None
                for index, bar in enumerate(segment):
                    reasons = []
                    if index == 0 and gap_carry:
                        reasons.append("GAP_CARRY_FORWARD_EXIT_COUNTER_RESET")
                    trigger = triggers.get(bar.close_time)
                    applied = False
                    if trigger is not None:
                        prior = current
                        current, trigger_reason = apply_trigger(current, trigger, bar.close_time)
                        reasons.append(trigger_reason)
                        applied = current != prior or trigger_reason != "LOWER_PRECEDENCE_TRIGGER_SUPPRESSED"
                        if trigger_reason == "LOWER_PRECEDENCE_TRIGGER_SUPPRESSED":
                            suppressed += 1
                        if trigger.semantic_state == "AMBIGUOUS":
                            conflicts += 1
                            if conflicts <= 100:
                                conflict_handle.write(json.dumps({
                                    "close_time": bar.close_time.isoformat(),
                                    "conflicting_semantic_states": list(trigger.conflicting_semantic_states),
                                    "support_level_ids": list(trigger.support_level_ids),
                                    "trigger_term_record_ids": list(trigger.trigger_term_record_ids),
                                }, sort_keys=True, separators=(",", ":")) + "\n")
                    if applied:
                        pending_count = 0
                        pending_reason = None
                        pending_bar = None
                    elif current.semantic_state != "NEUTRAL":
                        atr = atr_before(segment, index) if index >= 21 else None
                        predicate, reason = neutral_exit_predicate(
                            current,
                            bar=bar,
                            previous_bar=segment[index - 1] if index else None,
                            atr=atr,
                            level_prices=level_prices,
                            compression_failed=bar.close_time in compression_failed,
                            coherent_trigger_present=trigger is not None and trigger.semantic_state != "AMBIGUOUS",
                        )
                        if predicate:
                            if pending_count == 1 and pending_reason == reason and pending_bar is not None:
                                exit_record = make_neutral_exit(current, pending_bar, bar, reason)
                                exit_writer.write(neutral_exit_to_dict(exit_record))
                                exit_counts[reason] += 1
                                reasons.append("NEUTRAL_EXIT_CONFIRMED")
                                current = PersistentState("NEUTRAL", None, (), (), bar.close_time)
                                pending_count = 0
                                pending_reason = None
                                pending_bar = None
                            else:
                                pending_count = 1
                                pending_reason = reason
                                pending_bar = bar
                                reasons.append("NEUTRAL_EXIT_PENDING")
                        else:
                            pending_count = 0
                            pending_reason = None
                            pending_bar = None
                    row = state_record(
                        bar=bar,
                        current=current,
                        exit_pending_count=pending_count,
                        exit_pending_reason=pending_reason,
                        reason_codes=tuple(reasons),
                    )
                    state_writer.write(row)
                    state_counts[current.semantic_state] += 1
                    reason_counts.update(reasons)
        state_writer.close()
        exit_writer.close()
        if state_writer.count != len(bars):
            raise AssertionError("compound state stream must contain exactly one row per source bar")
        result = {
            "source_bars": len(bars),
            "registry_levels": len(registry.levels),
            "ratified_lifecycles": len(lifecycles),
            "state_records": state_writer.count,
            "neutral_exit_records": exit_writer.count,
            "state_counts": dict(sorted(state_counts.items())),
            "exit_reason_counts": dict(sorted(exit_counts.items())),
            "state_reason_counts": dict(sorted(reason_counts.items())),
            "suppressed_lower_precedence_triggers": suppressed,
            "conflicting_compound_triggers": conflicts,
            "state_stream_canonical_jsonl_hash": state_writer.canonical_jsonl_hash,
            "neutral_exit_canonical_jsonl_hash": exit_writer.canonical_jsonl_hash,
        }
        all_results[timeframe] = result
        for path in (lifecycle_path, state_path, exit_path, conflict_path):
            artifacts.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})

    assert registry_manifest and replay_manifest and review_manifest
    summary_path = output / "compound_state_replay_summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    manifest_core = {
        "release_id": "B-STATE-GBPUSD-2026H1-v0.2",
        "status": "STRUCTURAL_POLICY_RATIFIED_STATE_CONTRACT_REPLAYED_NOT_RATIFIED",
        "generated_date": "2026-07-19",
        "opt_a_seal_hash": seal["seal_hash"],
        "reference_registry_hash": registry_manifest["combined_registry_hash"],
        "complete_replay_manifest_hash": replay_manifest["manifest_hash"],
        "relevance_review_manifest_hash": review_manifest["manifest_hash"],
        "relevance_policy_id": RATIFIED_STRUCTURAL_ONLY_POLICY.policy_id,
        "state_contract_version": "B-STATE-0.2",
        "results": all_results,
        "artifacts": artifacts,
        "authority_boundary": "B-REF-0.2-STRUCTURAL-ONLY is ratified for active research. B-STATE-0.2 is replayed but requires operator ratification. No outcome, edge, recommendation or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "COMPOUND_STATE_REPLAY_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# OVC OPT-B Compound-State and Neutral-Exit Replay",
        "",
        "**Status:** `STRUCTURAL POLICY RATIFIED; STATE CONTRACT REPLAYED — NOT RATIFIED`  ",
        "**Relevance:** `B-REF-0.2-STRUCTURAL-ONLY`  ",
        "**State contract:** `B-STATE-0.2`",
        "",
        "| Clock | Bars | Neutral exits | Conflicting triggers | Suppressed lower-precedence triggers |",
        "|---|---:|---:|---:|---:|",
    ]
    for tf in ("15M", "2H"):
        item = all_results[tf]
        lines.append(f"| {tf} | {item['source_bars']:,} | {item['neutral_exit_records']:,} | {item['conflicting_compound_triggers']:,} | {item['suppressed_lower_precedence_triggers']:,} |")
    lines.extend([
        "",
        "Coherent same-label level evidence is represented as one compound state. Only contradictory top-precedence labels create `AMBIGUOUS`. State persists until a ratified trigger replaces it or a two-bar neutral-exit predicate confirms. Gaps reset pending exit counters but never manufacture neutrality.",
        "",
        "This replay defines market-description state only. It contains no OPT-C outcome, edge or execution authority.",
    ])
    (output / "OVC_OPT_B_COMPOUND_STATE_NEUTRAL_EXIT_REPLAY_REPORT_v0_2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"], "results": all_results}))


if __name__ == "__main__":
    main()
