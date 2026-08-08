from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import resource
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

POP_START = "2023-11-01T00:00:00Z"
POP_END = "2024-01-01T00:00:00Z"
REF_START = "2023-09-01T00:00:00Z"
REF_END = POP_START
CLOCK_MS = 2 * 60 * 60 * 1000
AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
SIDES = ("BID", "ASK")
ET_DC = (Decimal("0.0005"), Decimal("0.0010"), Decimal("0.0020"), Decimal("0.0040"))
ET_X = (Decimal("0.0050"), Decimal("0.0100"))
ET_VAR = (Decimal("0.0010"), Decimal("0.0020"), Decimal("0.0040"), Decimal("0.0080"))
AL_FIELDS = (
    "AL-01.raw_2h_activity",
    "AL-05.slot_percentile",
    "AL-07.activity_acceleration",
    "AL-08.bid_activity",
    "AL-09.ask_activity",
)
ET_FIELDS = tuple(
    [f"ET-DC.delta_{x}.event_count" for x in ET_DC]
    + [f"ET-X.step_{x}.crossing_count" for x in ET_X]
    + [f"ET-VAR.target_{x}.event_count" for x in ET_VAR]
)
VS_FIELDS = ("VS-01.abs_simple_return", "VS-02.squared_simple_return", "VS-03.raw_high_low_range")
PRICE_FIELDS = tuple(f"C2.axes.{a.lower()}" for a in AXES)
PACKS = {
    "R0": PRICE_FIELDS,
    "R1": PRICE_FIELDS + AL_FIELDS,
    "R2": PRICE_FIELDS + ET_FIELDS,
    "R3": PRICE_FIELDS + VS_FIELDS,
    "R4": PRICE_FIELDS + AL_FIELDS + VS_FIELDS,
    "R4X": PRICE_FIELDS + AL_FIELDS + ET_FIELDS,
    "R5": PRICE_FIELDS + ET_FIELDS + VS_FIELDS,
    "R6": PRICE_FIELDS + AL_FIELDS + ET_FIELDS + VS_FIELDS,
    "D-AL": AL_FIELDS,
    "D-ET": ET_FIELDS,
    "D-VS": VS_FIELDS,
}
RUN_AUTHORITY = "BOUNDED_STAGE_A_RESEARCH_EVIDENCE_ONLY"


def utc_ms(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def canonical_no_newline(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(canonical_no_newline(value)).hexdigest()


def write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return {"path": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def write_gzip_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    logical = hashlib.sha256()
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as out:
            for record in records:
                line = canonical_bytes(record)
                logical.update(line)
                out.write(line)
                count += 1
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "record_count": count,
        "logical_sha256": logical.hexdigest(),
    }


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"INVALID_JSONL:{path}:{number}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"NON_OBJECT_JSONL:{path}:{number}")
            yield value


def locate(root: Path, relative: str) -> Path:
    for candidate in (root / relative, root / "files" / relative):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise RuntimeError(f"MISSING_INPUT_PAYLOAD:{relative}")


def slot_id(ms: int) -> str:
    hour = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).hour
    return chr(ord("A") + hour // 2)


def source_bar_id(release_id: str, source_path: str, timestamp_ms: int) -> str:
    return "opt-a:" + hashlib.sha256(f"{release_id}|{source_path}|{timestamp_ms}".encode()).hexdigest()


def state_identity(row: Mapping[str, Any], c1_release_id: str) -> dict[str, Any]:
    return {
        "c1_record_id": row["parent_c1_record_id"],
        "source_bar_id": row["parent_opt_a_bar_id"],
        "c1_release_id": c1_release_id,
        "opt_a_release_id": row["opt_a_release_id"],
        "first_valid_time": row["first_valid_time"],
        "clock": row["clock"],
        "side": row["side"],
        "evaluation_scope_id": row["evaluation_scope_id"],
        "parameter_pack_id": row["parameter_pack_id"],
        "axes": row["axes"],
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"NON_OBJECT_JSON:{path}")
    return value


def verify_frozen_identity(prereg: Path, params: Path, auth: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    p = load_json(prereg)
    r = load_json(params)
    a = load_json(auth)
    if a.get("decision") != "AUTHORIZE_STAGE_A":
        raise RuntimeError("STAGE_A_AUTHORITY_NOT_GRANTED")
    granted = a.get("authority_granted", {})
    if git_blob_sha1(prereg) != granted.get("preregistration_git_blob_sha1"):
        raise RuntimeError("PREREGISTRATION_GIT_BLOB_MISMATCH")
    if git_blob_sha1(params) != granted.get("parameter_registry_git_blob_sha1"):
        raise RuntimeError("PARAMETER_REGISTRY_GIT_BLOB_MISMATCH")
    if p.get("population", {}).get("interval") != f"[{POP_START},{POP_END})":
        raise RuntimeError("FROZEN_POPULATION_INTERVAL_MISMATCH")
    if p.get("normalization_reference", {}).get("interval") != f"[{REF_START},{REF_END})":
        raise RuntimeError("FROZEN_NORMALIZATION_REFERENCE_MISMATCH")
    if tuple(r.get("ET-DC", {}).get("thresholds", ())) != tuple(str(x) for x in ET_DC):
        raise RuntimeError("ET_DC_GRID_MISMATCH")
    if tuple(r.get("ET-X", {}).get("steps", ())) != tuple(str(x) for x in ET_X):
        raise RuntimeError("ET_X_GRID_MISMATCH")
    if tuple(r.get("ET-VAR", {}).get("targets", ())) != tuple(str(x) for x in ET_VAR):
        raise RuntimeError("ET_VAR_GRID_MISMATCH")
    if set(p.get("packs", {})) != set(PACKS):
        raise RuntimeError("PACK_ID_SET_MISMATCH")
    for pack, domains in p["packs"].items():
        expected: list[str] = []
        for domain in domains:
            expected.extend({"PRICE": PRICE_FIELDS, "AL": AL_FIELDS, "ET": ET_FIELDS, "VS": VS_FIELDS}[domain])
        if tuple(expected) != PACKS[pack]:
            raise RuntimeError(f"PACK_FIELD_SURFACE_MISMATCH:{pack}")
    return p, r, a


def verify_opt_a_release(root: Path, prereg: Mapping[str, Any], manifest_spec_path: Path, verification_dir: Path) -> dict[str, Any]:
    from ovc_evidence_store.manifest import build_manifest

    spec = load_json(manifest_spec_path)
    cfg = spec["roles"]["discovery"]
    pop = prereg["population"]
    if cfg["release_id"] != pop["release_id"] or cfg["manifest_id"] != pop["manifest_id"]:
        raise RuntimeError("OPT_A_MANIFEST_SPEC_IDENTITY_MISMATCH")
    if cfg["expected_manifest_sha256"] != pop["manifest_sha256"]:
        raise RuntimeError("OPT_A_MANIFEST_SPEC_SHA_MISMATCH")
    descriptor = load_json(root / "release-descriptor.json")
    if descriptor.get("release_id") != pop["release_id"] or descriptor.get("role") != "DISCOVERY":
        raise RuntimeError("OPT_A_RELEASE_DESCRIPTOR_MISMATCH")
    output = verification_dir / "opt-a-discovery-manifest.rebuilt.json"
    manifest = build_manifest(
        root=root,
        output=output,
        release_id=cfg["release_id"],
        manifest_id=cfg["manifest_id"],
        bucket=spec["bucket"],
        prefix=spec["prefix"],
        authority_state=spec["authority_state"],
        repository_commit=spec["source_commit"],
        source_ref=spec["source_ref"],
    )
    digest = sha256_file(output)
    if digest != cfg["expected_manifest_sha256"]:
        raise RuntimeError(f"OPT_A_MANIFEST_REBUILD_MISMATCH:{digest}")
    if len(manifest["files"]) != cfg["expected_file_count"]:
        raise RuntimeError("OPT_A_MANIFEST_FILE_COUNT_MISMATCH")
    size = sum(int(item["size"]) for item in manifest["files"])
    if size != cfg["expected_total_size_bytes"]:
        raise RuntimeError("OPT_A_MANIFEST_BYTE_COUNT_MISMATCH")
    return {
        "manifest_sha256": digest,
        "file_count": len(manifest["files"]),
        "total_size_bytes": size,
        "release_id": cfg["release_id"],
        "manifest_id": cfg["manifest_id"],
    }


def verify_c2_release(root: Path, prereg: Mapping[str, Any], receipt_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    receipt = load_json(receipt_path)
    r0 = prereg["r0"]
    item = next((x for x in receipt.get("releases", []) if x.get("release_id") == r0["release_id"]), None)
    if item is None or not item.get("remote_verified"):
        raise RuntimeError("C2_REMOTE_VERIFICATION_RECEIPT_MISSING")
    manifest_path = root / "manifest.json"
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["manifest_file_sha256"]:
        raise RuntimeError("C2_MANIFEST_FILE_SHA_MISMATCH")
    manifest = json.loads(raw)
    if manifest.get("release_id") != r0["release_id"] or manifest.get("manifest_id") != r0["manifest_id"]:
        raise RuntimeError("C2_MANIFEST_IDENTITY_MISMATCH")
    if manifest.get("manifest_sha256") != r0["manifest_sha256"]:
        raise RuntimeError("C2_MANIFEST_LOGICAL_SHA_MISMATCH")
    files = {x["path"]: x for x in manifest.get("files", [])}
    result_paths: dict[str, Path] = {}
    for side in SIDES:
        rel = f"states/2H_A_L/{side}/GBPUSD-2H-A-L-LOCAL-v0_1.jsonl"
        itemf = files.get(rel)
        if itemf is None:
            raise RuntimeError(f"C2_2H_STATE_NOT_IN_MANIFEST:{side}")
        path = locate(root, rel)
        if path.stat().st_size != int(itemf["size_bytes"]) or sha256_file(path) != itemf["sha256"]:
            raise RuntimeError(f"C2_2H_STATE_PAYLOAD_MISMATCH:{side}")
        result_paths[side] = path
    return {
        "release_id": r0["release_id"],
        "manifest_id": r0["manifest_id"],
        "manifest_sha256": r0["manifest_sha256"],
        "manifest_file_sha256": item["manifest_file_sha256"],
        "remote_verified": True,
        "physical_schema_note": "ACTIVE_C2_V2_IDENTITY_REPLAY_ENVELOPE; frozen Stage-A consumes exact five axis evidence objects only; no source schema rewrite",
    }, result_paths


def load_bars(root: Path, release_id: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for side in SIDES:
        rows: list[dict[str, Any]] = []
        for path in sorted((root / "canonical" / "2H_A_L" / side).glob("*.csv")):
            rel = path.relative_to(root).as_posix()
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != ["timestamp", "open", "high", "low", "close", "volume"]:
                    raise RuntimeError(f"OPT_A_2H_SCHEMA_MISMATCH:{rel}")
                for row in reader:
                    ms = int(row["timestamp"])
                    o, h, l, c, v = (Decimal(row[x]) for x in ("open", "high", "low", "close", "volume"))
                    if not (l <= o <= h and l <= c <= h) or v < 0:
                        raise RuntimeError(f"OPT_A_BAR_INVALID:{rel}:{ms}")
                    rows.append(
                        {
                            "side": side,
                            "timestamp_ms": ms,
                            "start": iso_ms(ms),
                            "end": iso_ms(ms + CLOCK_MS),
                            "open": o,
                            "high": h,
                            "low": l,
                            "close": c,
                            "volume": v,
                            "source_path": rel,
                            "object_id": source_bar_id(release_id, rel, ms),
                            "slot": slot_id(ms),
                        }
                    )
        rows.sort(key=lambda x: x["timestamp_ms"])
        if len({x["timestamp_ms"] for x in rows}) != len(rows):
            raise RuntimeError(f"OPT_A_DUPLICATE_2H_TIMESTAMP:{side}")
        result[side] = rows
    return result


def load_c2_states(
    paths: Mapping[str, Path],
    prereg: Mapping[str, Any],
    bars: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, Any]]:
    c1_release = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2"
    by_side: dict[str, dict[int, dict[str, Any]]] = {}
    source_mismatch = 0
    id_mismatch = 0
    total = 0
    for side in SIDES:
        bar_map = {b["end"]: b for b in bars[side]}
        states: dict[int, dict[str, Any]] = {}
        for row in iter_jsonl(paths[side]):
            if row.get("role") != "DISCOVERY" or row.get("side") != side or row.get("clock") != "2H_A_L":
                raise RuntimeError(f"C2_STATE_SCOPE_MISMATCH:{side}")
            if row.get("opt_a_release_id") != prereg["population"]["release_id"] or row.get("opt_a_manifest_id") != prereg["population"]["manifest_id"]:
                raise RuntimeError(f"C2_OPT_A_BINDING_MISMATCH:{side}")
            bar = bar_map.get(row.get("first_valid_time"))
            if bar is None:
                raise RuntimeError(f"C2_FIRST_VALID_UNBOUND_TO_OPT_A:{side}:{row.get('first_valid_time')}")
            if row.get("parent_opt_a_bar_id") != bar["object_id"]:
                source_mismatch += 1
            expected_id = stable_id("c2-state:", state_identity(row, c1_release))
            if row.get("c2_state_id") != expected_id:
                id_mismatch += 1
            axes = row.get("axes")
            if not isinstance(axes, dict) or set(axes) != set(AXES):
                raise RuntimeError(f"C2_AXIS_SET_MISMATCH:{side}:{row.get('first_valid_time')}")
            states[bar["timestamp_ms"]] = row
            total += 1
        if len(states) != len(bars[side]):
            raise RuntimeError(f"C2_OPT_A_2H_CARDINALITY_MISMATCH:{side}:{len(states)}:{len(bars[side])}")
        by_side[side] = states
    if source_mismatch or id_mismatch:
        raise RuntimeError(f"C2_IDENTITY_VERIFICATION_FAILURE:source={source_mismatch}:state={id_mismatch}")
    return by_side, {
        "state_records_verified": total,
        "source_bar_id_mismatches": source_mismatch,
        "state_id_mismatches": id_mismatch,
    }


def directional_change_counts(bars: Sequence[Mapping[str, Any]], threshold: Decimal) -> dict[int, int]:
    if not bars:
        return {}
    high = low = bars[0]["close"]
    mode = None
    result = {bars[0]["timestamp_ms"]: 0}
    for bar in bars[1:]:
        c = bar["close"]
        if c > high:
            high = c
        if c < low:
            low = c
        value = 0
        if mode != "DOWN" and high - c >= threshold:
            value = 1
            mode = "DOWN"
            low = c
        elif mode != "UP" and c - low >= threshold:
            value = 1
            mode = "UP"
            high = c
        result[bar["timestamp_ms"]] = value
    return result


def variation_counts(bars: Sequence[Mapping[str, Any]], target: Decimal) -> dict[int, int]:
    if not bars:
        return {}
    acc = Decimal(0)
    previous = bars[0]
    result = {previous["timestamp_ms"]: 0}
    for current in bars[1:]:
        acc += abs(current["close"] - previous["close"])
        value = 0
        if acc >= target:
            value = 1
            acc = Decimal(0)
        result[current["timestamp_ms"]] = value
        previous = current
    return result


def lattice_crossing_count(previous: Decimal, current: Decimal, step: Decimal, lower: Decimal, upper: Decimal) -> int:
    if previous == current:
        return 0
    low_k = int((lower / step).to_integral_value())
    high_k = int((upper / step).to_integral_value())
    count = 0
    for k in range(low_k, high_k + 1):
        level = step * k
        if previous < current and previous < level <= current:
            count += 1
        elif previous > current and previous > level >= current:
            count += 1
    return count


def et_surface(bars: Mapping[str, Sequence[Mapping[str, Any]]], params: Mapping[str, Any]) -> dict[str, dict[int, dict[str, int]]]:
    lower = Decimal(params["ET-X"]["bounds"][0])
    upper = Decimal(params["ET-X"]["bounds"][1])
    out: dict[str, dict[int, dict[str, int]]] = {}
    for side in SIDES:
        series = bars[side]
        surface = {b["timestamp_ms"]: {} for b in series}
        for threshold in ET_DC:
            counts = directional_change_counts(series, threshold)
            for ms, count in counts.items():
                surface[ms][f"ET-DC.delta_{threshold}.event_count"] = count
        for target in ET_VAR:
            counts = variation_counts(series, target)
            for ms, count in counts.items():
                surface[ms][f"ET-VAR.target_{target}.event_count"] = count
        for step in ET_X:
            surface[series[0]["timestamp_ms"]][f"ET-X.step_{step}.crossing_count"] = 0
            previous = series[0]
            for current in series[1:]:
                surface[current["timestamp_ms"]][f"ET-X.step_{step}.crossing_count"] = lattice_crossing_count(
                    previous["close"], current["close"], step, lower, upper
                )
                previous = current
        out[side] = surface
    return out


def r0_signature(axes: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_no_newline({axis: axes[axis] for axis in AXES})).hexdigest()


def build_fresh_records(
    bars: Mapping[str, Sequence[Mapping[str, Any]]],
    states: Mapping[str, Mapping[int, Mapping[str, Any]]],
    prereg: Mapping[str, Any],
    params: Mapping[str, Any],
) -> list[dict[str, Any]]:
    pop_start = utc_ms(POP_START)
    pop_end = utc_ms(POP_END)
    ref_start = utc_ms(REF_START)
    ref_end = utc_ms(REF_END)
    ref: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for side in SIDES:
        for bar in bars[side]:
            if ref_start <= bar["timestamp_ms"] < ref_end:
                ref[(side, bar["slot"])].append(bar["volume"])
    min_ref = int(prereg["normalization_reference"]["minimum_n"])
    et = et_surface(bars, params)
    bar_lookup = {side: {b["timestamp_ms"]: b for b in bars[side]} for side in SIDES}
    records: list[dict[str, Any]] = []
    for side in SIDES:
        series = bars[side]
        index = {b["timestamp_ms"]: i for i, b in enumerate(series)}
        for bar in series:
            ms = bar["timestamp_ms"]
            if not (pop_start <= ms < pop_end):
                continue
            i = index[ms]
            previous = series[i - 1] if i else None
            contiguous = previous is not None and previous["timestamp_ms"] + CLOCK_MS == ms
            fields: dict[str, Any] = {}
            reasons: dict[str, str] = {}
            state = states[side][ms]
            for axis in AXES:
                fields[f"C2.axes.{axis.lower()}"] = state["axes"][axis]
            fields["AL-01.raw_2h_activity"] = decimal_text(bar["volume"])
            reference = ref[(side, bar["slot"])]
            if len(reference) >= min_ref:
                rank = sum(1 for value in reference if value <= bar["volume"])
                fields["AL-05.slot_percentile"] = decimal_text(Decimal(rank) * Decimal(100) / Decimal(len(reference)))
            else:
                fields["AL-05.slot_percentile"] = None
                reasons["AL-05.slot_percentile"] = "INSUFFICIENT_FROZEN_REFERENCE"
            if contiguous:
                fields["AL-07.activity_acceleration"] = decimal_text(bar["volume"] - previous["volume"])
            else:
                fields["AL-07.activity_acceleration"] = None
                reasons["AL-07.activity_acceleration"] = "NO_CONTIGUOUS_PRIOR_BAR"
            bid = bar_lookup["BID"].get(ms)
            ask = bar_lookup["ASK"].get(ms)
            fields["AL-08.bid_activity"] = None if bid is None else decimal_text(bid["volume"])
            fields["AL-09.ask_activity"] = None if ask is None else decimal_text(ask["volume"])
            if bid is None:
                reasons["AL-08.bid_activity"] = "PAIRED_BID_BAR_ABSENT"
            if ask is None:
                reasons["AL-09.ask_activity"] = "PAIRED_ASK_BAR_ABSENT"
            fields.update(et[side][ms])
            if contiguous:
                if previous["close"] == 0:
                    raise RuntimeError("ZERO_PREVIOUS_CLOSE")
                ret = (bar["close"] - previous["close"]) / previous["close"]
                fields["VS-01.abs_simple_return"] = decimal_text(abs(ret))
                fields["VS-02.squared_simple_return"] = decimal_text(ret * ret)
            else:
                fields["VS-01.abs_simple_return"] = None
                fields["VS-02.squared_simple_return"] = None
                reasons["VS-01.abs_simple_return"] = "NO_CONTIGUOUS_PRIOR_BAR"
                reasons["VS-02.squared_simple_return"] = "NO_CONTIGUOUS_PRIOR_BAR"
            fields["VS-03.raw_high_low_range"] = decimal_text(bar["high"] - bar["low"])
            record_core = {
                "source_release_id": prereg["population"]["release_id"],
                "source_manifest_id": prereg["population"]["manifest_id"],
                "source_bar_id": bar["object_id"],
                "c2_release_id": prereg["r0"]["release_id"],
                "c2_manifest_id": prereg["r0"]["manifest_id"],
                "c2_state_id": state["c2_state_id"],
                "side": side,
                "clock": "2H_A_L",
                "slot": bar["slot"],
                "observation_start": bar["start"],
                "observation_end": bar["end"],
                "first_valid_time": bar["end"],
                "r0_signature": r0_signature(state["axes"]),
                "fields": fields,
                "missing_reasons": reasons,
            }
            records.append(
                {
                    "record_id": "MCARB.STAGEA.RECORD." + hashlib.sha256(canonical_no_newline(record_core)).hexdigest(),
                    **record_core,
                    "authority": RUN_AUTHORITY,
                }
            )
    records.sort(key=lambda x: (x["side"], x["observation_start"], x["record_id"]))
    if len(records) != 898:
        raise RuntimeError(f"STAGE_A_RECORD_COUNT_MISMATCH:{len(records)}")
    if len({r["observation_start"] for r in records if r["side"] == "BID"}) != 449:
        raise RuntimeError("STAGE_A_BID_TIMESTAMP_COUNT_MISMATCH")
    if {r["observation_start"] for r in records if r["side"] == "BID"} != {r["observation_start"] for r in records if r["side"] == "ASK"}:
        raise RuntimeError("STAGE_A_BID_ASK_TIMESTAMP_SET_MISMATCH")
    return records


def checkpoint_records(output_root: Path, records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    inventory = []
    for side in SIDES:
        for month in ("2023-11", "2023-12"):
            subset = [r for r in records if r["side"] == side and r["observation_start"].startswith(month)]
            info = write_gzip_jsonl(output_root / "checkpoints" / f"{side}-{month}.jsonl.gz", subset)
            info.update({"side": side, "month": month})
            inventory.append(info)
    return {
        "schema": "ovc-mcarbi-stage-a-checkpoint-inventory/v1",
        "entries": inventory,
        "checkpoint_policy": "SIDE_MONTH_BYTE_IDENTICAL_RESUME",
    }


def load_checkpoints(root: Path) -> list[dict[str, Any]]:
    result = []
    for side in SIDES:
        for month in ("2023-11", "2023-12"):
            path = root / f"{side}-{month}.jsonl.gz"
            if not path.is_file():
                raise RuntimeError(f"MISSING_CHECKPOINT:{path.name}")
            result.extend(iter_jsonl(path))
    result.sort(key=lambda x: (x["side"], x["observation_start"], x["record_id"]))
    if len(result) != 898:
        raise RuntimeError("RESUME_RECORD_COUNT_MISMATCH")
    return result


def numeric_value(value: Any) -> Decimal | None:
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def sse(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        return +sum(((x - mean) ** 2 for x in values), Decimal(0))


def residual_fraction(
    records: Sequence[dict[str, Any]], field: str, override: Mapping[str, Decimal] | None = None
) -> tuple[Decimal | None, int]:
    base: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    conditional: dict[tuple[str, str, str], list[Decimal]] = defaultdict(list)
    n = 0
    for record in records:
        value = override.get(record["record_id"]) if override is not None else numeric_value(record["fields"].get(field))
        if value is None:
            continue
        key = (record["side"], record["slot"])
        base[key].append(value)
        conditional[key + (record["r0_signature"],)].append(value)
        n += 1
    denominator = Decimal(0)
    numerator = Decimal(0)
    for values in base.values():
        item = sse(values)
        if item is not None:
            denominator += item
    for values in conditional.values():
        item = sse(values)
        if item is not None:
            numerator += item
    if denominator == 0:
        return None, n
    return numerator / denominator, n


def deterministic_shuffle(records: Sequence[dict[str, Any]], field: str) -> dict[str, Decimal]:
    strata: dict[tuple[str, str], list[tuple[str, Decimal]]] = defaultdict(list)
    for record in records:
        value = numeric_value(record["fields"].get(field))
        if value is not None:
            strata[(record["side"], record["slot"])].append((record["record_id"], value))
    result: dict[str, Decimal] = {}
    seed = "MCARB.STAGEA.SHUFFLE.v1"
    for values in strata.values():
        source = sorted(values, key=lambda x: x[0])
        targets = sorted(values, key=lambda x: (hashlib.sha256((x[0] + seed).encode()).digest(), x[0]))
        for (target_id, _), (_, source_value) in zip(targets, source):
            result[target_id] = source_value
    return result


def deterministic_noise(records: Sequence[dict[str, Any]], field: str) -> dict[str, Decimal]:
    result = {}
    for record in records:
        if record["fields"].get(field) is None:
            continue
        digest = hashlib.sha256((record["record_id"] + "|" + field + "|MCARB.STAGEA.MATCHED.NOISE.v1").encode()).digest()
        integer = int.from_bytes(digest[:8], "big")
        result[record["record_id"]] = Decimal(integer) / Decimal(2**64 - 1)
    return result


def field_stats(records: Sequence[dict[str, Any]], fields: Sequence[str]) -> dict[str, Any]:
    out = {}
    for field in fields:
        numeric = [numeric_value(r["fields"].get(field)) for r in records]
        numeric = [x for x in numeric if x is not None]
        reasons = Counter(
            r["missing_reasons"].get(field, "") for r in records if r["fields"].get(field) is None
        )
        item: dict[str, Any] = {
            "available": len(numeric),
            "missing": len(records) - len(numeric),
            "missing_reasons": {k: v for k, v in sorted(reasons.items()) if k},
        }
        if numeric:
            item.update(
                {
                    "min": decimal_text(min(numeric)),
                    "max": decimal_text(max(numeric)),
                    "mean": decimal_text(sum(numeric, Decimal(0)) / Decimal(len(numeric))),
                }
            )
        out[field] = item
    return out


def pearson_pairs(pairs: Sequence[tuple[Decimal, Decimal]]) -> Decimal | None:
    if len(pairs) < 3:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        xs = [a for a, _ in pairs]
        ys = [b for _, b in pairs]
        mx = sum(xs, Decimal(0)) / Decimal(len(xs))
        my = sum(ys, Decimal(0)) / Decimal(len(ys))
        dx = [x - mx for x in xs]
        dy = [y - my for y in ys]
        num = sum((a * b for a, b in zip(dx, dy)), Decimal(0))
        sx = sum((a * a for a in dx), Decimal(0))
        sy = sum((b * b for b in dy), Decimal(0))
        if sx == 0 or sy == 0:
            return None
        return +(num / (sx * sy).sqrt())


def average_ranks(values: Sequence[Decimal]) -> list[Decimal]:
    indexed = sorted(enumerate(values), key=lambda x: (x[1], x[0]))
    ranks = [Decimal(0)] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (Decimal(i + 1) + Decimal(j)) / Decimal(2)
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def dependence_surface(records: Sequence[dict[str, Any]], fields: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for side in SIDES:
        for slot in [chr(ord("A") + i) for i in range(12)]:
            subset = [r for r in records if r["side"] == side and r["slot"] == slot]
            for i, left in enumerate(fields):
                for right in fields[i + 1 :]:
                    pairs = []
                    for record in subset:
                        a = numeric_value(record["fields"].get(left))
                        b = numeric_value(record["fields"].get(right))
                        if a is not None and b is not None:
                            pairs.append((a, b))
                    pearson = pearson_pairs(pairs)
                    rank = None
                    if len(pairs) >= 3:
                        rx = average_ranks([x for x, _ in pairs])
                        ry = average_ranks([y for _, y in pairs])
                        rank = pearson_pairs(list(zip(rx, ry)))
                    rows.append(
                        {
                            "side": side,
                            "slot": slot,
                            "left": left,
                            "right": right,
                            "n": len(pairs),
                            "pearson": None if pearson is None else decimal_text(pearson),
                            "rank": None if rank is None else decimal_text(rank),
                            "authority": "DESCRIPTIVE_DEPENDENCE_ONLY_NO_SELECTOR",
                        }
                    )
    return rows


def pack_summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    summary = {}
    for pack, fields in PACKS.items():
        eligible = []
        for record in records:
            missing = [f for f in fields if f not in PRICE_FIELDS and record["fields"].get(f) is None]
            if not missing:
                eligible.append(record)
        aux = [f for f in fields if f not in PRICE_FIELDS]
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for record in eligible:
            groups[(record["side"], record["slot"], record["r0_signature"])].append(record)
        pairs = 0
        separated = 0
        for group in groups.values():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    pairs += 1
                    if any(group[i]["fields"].get(f) != group[j]["fields"].get(f) for f in aux):
                        separated += 1
        noise_sep = 0
        if aux:
            noise = {f: deterministic_noise(eligible, f) for f in aux}
            for group in groups.values():
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if any(noise[f].get(group[i]["record_id"]) != noise[f].get(group[j]["record_id"]) for f in aux):
                            noise_sep += 1
        summary[pack] = {
            "required_field_count": len(fields),
            "auxiliary_field_count": len(aux),
            "eligible_records": len(eligible),
            "abstained_records": len(records) - len(eligible),
            "repeated_r0_comparable_pairs": pairs,
            "aux_exact_vector_separated_pairs": separated,
            "matched_noise_separated_pairs": noise_sep if aux else 0,
            "interpretation": "Exact-vector separation is not scientific improvement; compare matched-noise control and field-level residual diagnostics.",
        }
    return summary


def recurrence_summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for side in SIDES:
        counts = Counter(r["r0_signature"] for r in records if r["side"] == side)
        result[side] = {
            "records": sum(counts.values()),
            "distinct_r0_signatures": len(counts),
            "repeated_signature_groups": sum(1 for value in counts.values() if value > 1),
            "records_in_repeated_groups": sum(value for value in counts.values() if value > 1),
            "max_group_size": max(counts.values()),
        }
    return result


def redundancy_surface(records: Sequence[dict[str, Any]], fields: Sequence[str]) -> dict[str, Any]:
    out = {}
    for field in fields:
        observed, n = residual_fraction(records, field)
        shuffled, _ = residual_fraction(records, field, deterministic_shuffle(records, field))
        noise, _ = residual_fraction(records, field, deterministic_noise(records, field))
        out[field] = {
            "n": n,
            "residual_fraction_after_side_slot_r0": None if observed is None else decimal_text(observed),
            "structural_explained_fraction": None if observed is None else decimal_text(Decimal(1) - observed),
            "shuffled_residual_fraction": None if shuffled is None else decimal_text(shuffled),
            "matched_noise_residual_fraction": None if noise is None else decimal_text(noise),
            "interpretation": "Gross conditional redundancy diagnostic only; high residual means variation remains outside exact R0 state, not that it is useful or predictive.",
        }
    return out


def side_pair_surface(records: Sequence[dict[str, Any]], fields: Sequence[str]) -> dict[str, Any]:
    by = {(r["side"], r["observation_start"]): r for r in records}
    out = {}
    timestamps = sorted({r["observation_start"] for r in records})
    for field in fields:
        pairs = []
        for ts in timestamps:
            bid = by.get(("BID", ts))
            ask = by.get(("ASK", ts))
            if bid is None or ask is None:
                continue
            left = numeric_value(bid["fields"].get(field))
            right = numeric_value(ask["fields"].get(field))
            if left is not None and right is not None:
                pairs.append((left, right))
        pearson = pearson_pairs(pairs)
        out[field] = {
            "n": len(pairs),
            "pearson_bid_ask": None if pearson is None else decimal_text(pearson),
            "interpretation": "paired-side descriptive diagnostic only",
        }
    return out


def build_evidence(records: Sequence[dict[str, Any]], source: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    aux_fields = AL_FIELDS + ET_FIELDS + VS_FIELDS
    deps = dependence_surface(records, aux_fields)
    slot_counts = Counter((r["side"], r["slot"]) for r in records)
    evidence = {
        "schema": "ovc-mcarbi-stage-a-evidence-vector/v1",
        "programme_id": "OVC-MCARB-v0.1",
        "packet_id": "MCARBI-WP8",
        "gate_id": "MCARBI-G8",
        "authority": RUN_AUTHORITY,
        "scope": {
            "purpose": "MACHINERY_SOURCE_SEMANTICS_CHRONOLOGY_MISSINGNESS_CAPACITY_DEPENDENCE_GROSS_REDUNDANCY_ONLY",
            "long_run_stability_claim": "PROHIBITED",
            "population": f"[{POP_START},{POP_END})",
            "normalization_reference": f"[{REF_START},{REF_END})",
        },
        "source_binding": source,
        "population": {
            "record_count": len(records),
            "side_counts": dict(Counter(r["side"] for r in records)),
            "timestamp_pair_count": len({r["observation_start"] for r in records}),
            "slot_counts": {f"{key[0]}:{key[1]}": value for key, value in sorted(slot_counts.items())},
        },
        "r0_recurrence": recurrence_summary(records),
        "field_stats": field_stats(records, aux_fields),
        "gross_redundancy": redundancy_surface(records, aux_fields),
        "pack_summary": pack_summary(records),
        "paired_side_diagnostics": side_pair_surface(records, aux_fields),
        "dependence_summary": {
            "row_count": len(deps),
            "methods": ["PEARSON", "RANK_CORRELATION"],
            "mutual_information": "OMITTED_NOT_PREREGISTERED",
            "use_as_selector": "PROHIBITED",
            "max_abs_pearson": None,
            "max_abs_rank": None,
        },
        "criterion_vector": {
            "SOURCE_BINDING": "PASS",
            "CHRONOLOGY": "PASS_CAUSAL_FIRST_VALID_AT_2H_CLOSE",
            "MISSINGNESS_TOLERANCE": "PASS_ABSTAIN_NO_IMPUTATION",
            "CAPACITY": "PASS_MEASURED",
            "REDUNDANCY": "MEASURED_GROSS_ONLY",
            "DISCRIMINATION": "MEASURED_WITH_MATCHED_NOISE_CONTROL_NO_MERIT_CLAIM",
            "INTERPRETABILITY": "PASS_FIELD_LEVEL_LINEAGE",
            "ROBUSTNESS": "PARTIAL_FROZEN_ET_GRID_ONLY",
            "RECURRENCE": "NOT_EVALUATED_BEYOND_EXACT_R0_COLLISION_DIAGNOSTIC",
            "RESIDUAL_REDUCTION": "NOT_EVALUATED_NO_FAMILY_METHOD_IN_STAGE_A",
            "CHRONOLOGICAL_STABILITY": "NOT_EVALUATED_STAGE_A_SCOPE",
            "CROSS_SCALE_STABILITY": "NOT_EVALUATED_STAGE_A_SCOPE",
            "BOUNDARY_QUALITY": "NOT_EVALUATED_STAGE_A_SCOPE",
            "COUNTEREXAMPLE_SEPARATION": "NOT_EVALUATED_STAGE_A_SCOPE",
        },
        "capacity": {
            "runtime_seconds_budget": 14400,
            "peak_memory_bytes_budget": 17179869184,
            "external_artifact_bytes_budget": 10737418240,
            "sampling": "PROHIBITED",
            "status": "PASS_MEASURED",
        },
        "warnings": [
            "AL_SOURCE_PARTIAL remains binding; provider activity is not centralized FX traded volume or order flow.",
            "AL-05 frozen Sep-Oct reference has insufficient K/L slot sample size and therefore abstains there by preregistration.",
            "Frozen preregistration names c2_parallel_state_v0_1 while active C2 v2 is the verified identity-replay envelope; Stage A consumes only exact five-axis evidence objects without rewriting the source schema.",
            "Exact-vector separation can be reproduced by additional continuous/noise dimensions and is not treated as scientific improvement.",
            "Stage A cannot establish long-run chronological stability or production placement.",
        ],
        "authority_firewall": {
            "validation_2025": "LOCKED_UNCONSUMED",
            "provider_intake": "DENIED",
            "active_discovery": "NONE",
            "selector": "NONE",
            "promotion": "NONE",
            "publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
        },
        "scientific_disposition": "OPERATOR_REQUIRED_AT_MCARBI_G9",
    }
    pearsons = [abs(Decimal(row["pearson"])) for row in deps if row["pearson"] is not None]
    ranks = [abs(Decimal(row["rank"])) for row in deps if row["rank"] is not None]
    if pearsons:
        evidence["dependence_summary"]["max_abs_pearson"] = decimal_text(max(pearsons))
    if ranks:
        evidence["dependence_summary"]["max_abs_rank"] = decimal_text(max(ranks))
    return evidence, deps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt-a-root", type=Path, required=True)
    parser.add_argument("--c2-root", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--parameter-registry", type=Path, required=True)
    parser.add_argument("--authority-decision", type=Path, required=True)
    parser.add_argument("--opt-a-manifest-spec", type=Path, required=True)
    parser.add_argument("--c2-verification-receipt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    args.output_root.mkdir(parents=True, exist_ok=False)
    prereg, params, _auth = verify_frozen_identity(args.preregistration, args.parameter_registry, args.authority_decision)
    verification = args.output_root / "verification"
    verification.mkdir()
    opt_a = verify_opt_a_release(args.opt_a_root, prereg, args.opt_a_manifest_spec, verification)
    c2_meta, c2_paths = verify_c2_release(args.c2_root, prereg, args.c2_verification_receipt)
    bars = load_bars(args.opt_a_root, prereg["population"]["release_id"])
    states, state_qa = load_c2_states(c2_paths, prereg, bars)
    source = {
        "opt_a": opt_a,
        "c2": c2_meta,
        "c2_state_binding": state_qa,
        "preregistration_git_blob_sha1": git_blob_sha1(args.preregistration),
        "parameter_registry_git_blob_sha1": git_blob_sha1(args.parameter_registry),
        "authority_decision_sha256": sha256_file(args.authority_decision),
        "validation_payload_read": False,
        "provider_fetch_or_intake": False,
    }
    if args.resume_from:
        records = load_checkpoints(args.resume_from)
        checkpoint = {"resume_from": str(args.resume_from), "record_count": len(records), "mode": "RESUME"}
    else:
        records = build_fresh_records(bars, states, prereg, params)
        checkpoint = checkpoint_records(args.output_root, records)
        checkpoint["mode"] = "FRESH"
    runtime = {
        "elapsed_seconds_before_evidence": round(time.monotonic() - started, 6),
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "capacity_runtime_seconds": 14400,
        "capacity_peak_memory_bytes": 17179869184,
    }
    evidence, deps = build_evidence(records, source)
    records_info = write_gzip_jsonl(args.output_root / "stage-a-records.jsonl.gz", records)
    dependence_info = write_gzip_jsonl(args.output_root / "stage-a-dependence.jsonl.gz", deps)
    pack_info = write_json(args.output_root / "stage-a-pack-summary.json", evidence["pack_summary"])
    runtime["elapsed_seconds_total_pre_write"] = round(time.monotonic() - started, 6)
    runtime["capacity_status"] = (
        "PASS"
        if runtime["elapsed_seconds_total_pre_write"] <= 14400 and runtime["peak_rss_bytes"] <= 17179869184
        else "CAPACITY_EXCEEDED"
    )
    evidence["criterion_vector"]["CAPACITY"] = "PASS_MEASURED" if runtime["capacity_status"] == "PASS" else "CAPACITY_EXCEEDED"
    evidence["capacity"]["status"] = "PASS_MEASURED" if runtime["capacity_status"] == "PASS" else "CAPACITY_EXCEEDED"
    evidence_info = write_json(args.output_root / "stage-a-evidence-vector.json", evidence)
    checkpoint_info = write_json(args.output_root / "checkpoint-inventory.json", checkpoint)
    inventory = {
        "records": records_info,
        "dependence": dependence_info,
        "pack_summary": pack_info,
        "evidence_vector": evidence_info,
        "checkpoint_inventory": checkpoint_info,
    }
    receipt = {
        "schema": "ovc-mcarbi-stage-a-run-receipt/v1",
        "programme_id": "OVC-MCARB-v0.1",
        "packet_id": "MCARBI-WP8",
        "run_id": "MCARB.STAGEA."
        + hashlib.sha256(
            canonical_no_newline(
                {
                    "prereg": source["preregistration_git_blob_sha1"],
                    "params": source["parameter_registry_git_blob_sha1"],
                    "population": prereg["population"],
                    "source_commit": args.source_commit,
                }
            )
        ).hexdigest()[:24],
        "execution_mode": "RESUME" if args.resume_from else "FRESH",
        "source_commit": args.source_commit,
        "workflow_run_id": str(args.workflow_run_id),
        "authority_decision": "AUTHORIZE_STAGE_A",
        "authority_consumed": True,
        "one_logical_run": True,
        "population_record_count": len(records),
        "output_inventory": inventory,
        "capacity_status": runtime["capacity_status"],
        "runtime": runtime,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "provider_intake": "DENIED",
        "selector_change": "NONE",
        "promotion": "NONE",
        "publication": "NONE",
        "probability": "NONE",
        "risk": "NONE",
        "exposure": "NONE",
        "execution_authority": "NONE",
        "result": "PASS_STAGE_A_MACHINERY" if runtime["capacity_status"] == "PASS" else "CAPACITY_EXCEEDED",
    }
    write_json(args.output_root / "stage-a-run-receipt.json", receipt)
    if receipt["result"] != "PASS_STAGE_A_MACHINERY":
        raise RuntimeError(receipt["result"])
    print(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "mode": receipt["execution_mode"],
                "records": len(records),
                "evidence_sha256": evidence_info["sha256"],
                "record_stream": records_info["logical_sha256"],
                "capacity": receipt["capacity_status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
