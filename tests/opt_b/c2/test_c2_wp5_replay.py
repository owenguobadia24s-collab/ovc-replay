from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from ovc.opt_b.c2.price_parent import (
    OptAReleaseBinding,
    PriceParentError,
    verify_opt_a_release,
)
from ovc.opt_b.c2.replay import (
    DISCOVERY_MANIFEST,
    DISCOVERY_RELEASE,
    FirstValidParentResolver,
    ReleaseBinding,
    ReplayError,
    run_verified_role_replay,
    verify_canonical_release,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"", "-0"} else rendered


def primitive(
    *,
    record_index: int,
    release_id: str,
    manifest_id: str,
    clock: str,
    side: str,
    source_path: str,
    timestamp_ms: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> dict:
    o, h, l, c = map(Decimal, (open_, high, low, close))
    range_abs = h - l
    body = c - o
    upper = h - max(o, c)
    lower = min(o, c) - l
    measurements = {
        "range_abs": _text(range_abs),
        "range_ticks": _text(range_abs / Decimal("0.00001")),
        "body_signed": _text(body),
        "body_abs": _text(abs(body)),
        "body_utilisation": _text(abs(body) / range_abs),
        "upper_wick_abs": _text(upper),
        "lower_wick_abs": _text(lower),
        "upper_wick_share": _text(upper / range_abs),
        "lower_wick_share": _text(lower / range_abs),
        "wick_balance": _text((upper - lower) / range_abs),
        "open_location": _text((o - l) / range_abs),
        "close_location": _text((c - l) / range_abs),
        "signed_efficiency": _text(body / range_abs),
        "true_range_abs": None,
        "true_range_ticks": None,
        "close_change": None,
        "open_gap": None,
    }
    return {
        "schema": "ovc-c1-bar-primitives/v0.1",
        "formula_registry_id": "C1.FORMULAS.v0.1",
        "authority_state": "CANDIDATE_LOCAL_ONLY",
        "market_authority": "NONE",
        "release_parent_eligibility": "DENIED_PENDING_FREEZE",
        "role": "DISCOVERY",
        "parent_release_id": release_id,
        "parent_manifest_id": manifest_id,
        "parent_manifest_sha256": "0" * 64,
        "instrument": "GBPUSD",
        "clock": clock,
        "price_side": side,
        "timestamp_ms": timestamp_ms,
        "source_path": source_path,
        "source_bar_id": "opt-a:" + hashlib.sha256(f"{release_id}|{source_path}|{timestamp_ms}".encode()).hexdigest(),
        "measurements": measurements,
        "categorical": {"direction": "UP" if c > o else "DOWN" if c < o else "FLAT"},
        "null_reasons": {
            "true_range_abs": "NO_PRIOR_BAR",
            "true_range_ticks": "NO_PRIOR_BAR",
            "close_change": "NO_PRIOR_BAR",
            "open_gap": "NO_PRIOR_BAR",
        },
        "record_id": f"c1:{record_index:064x}",
    }


def c1_root(root: Path, records_by_path: dict[str, list[dict]]) -> tuple[Path, ReleaseBinding]:
    release = root / "c1"
    files = release / "files"
    entries = []
    scopes: dict[tuple[str, str], int] = {}
    for relative, records in records_by_path.items():
        path = files / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
                for record in records:
                    handle.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
        entries.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": _hash(path)})
        parts = Path(relative).parts
        scopes[(parts[1], parts[2])] = scopes.get((parts[1], parts[2]), 0) + 1
    descriptor = files / "release-descriptor.json"
    descriptor.write_text(
        json.dumps(
            {
                "schema": "ovc-c1-release-descriptor/v1",
                "release_id": DISCOVERY_RELEASE,
                "role": "DISCOVERY",
                "formula_registry_id": "C1.FORMULAS.v0.1",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    entries.append({"path": "release-descriptor.json", "size_bytes": descriptor.stat().st_size, "sha256": _hash(descriptor)})
    manifest = release / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "ovc-c1-release-manifest/v1",
                "manifest_id": DISCOVERY_MANIFEST,
                "release_id": DISCOVERY_RELEASE,
                "files": entries,
                "file_count": len(entries),
                "payload_bytes": sum(item["size_bytes"] for item in entries),
                "record_file_count": len(records_by_path),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    binding = ReleaseBinding(
        "DISCOVERY",
        DISCOVERY_RELEASE,
        DISCOVERY_MANIFEST,
        _hash(manifest),
        len(records_by_path),
        len(entries),
        tuple((clock, side, count) for (clock, side), count in sorted(scopes.items())),
    )
    return release, binding


def opt_a_root(
    root: Path,
    *,
    release_id: str,
    manifest_id: str,
    rows_by_path: dict[str, list[dict[str, str]]],
) -> tuple[Path, OptAReleaseBinding]:
    release = root / "opt-a"
    files = release / "files"
    entries = []
    scopes: dict[tuple[str, str], int] = {}
    for relative, rows in rows_by_path.items():
        path = files / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        entries.append({"path": relative, "size": path.stat().st_size, "sha256": _hash(path)})
        parts = Path(relative).parts
        scopes[(parts[1], parts[2])] = scopes.get((parts[1], parts[2]), 0) + 1
    descriptor = files / "release-descriptor.json"
    descriptor.write_text(
        json.dumps(
            {
                "schema": "ovc-opt-a-role-release-descriptor/v1",
                "release_id": release_id,
                "role": "DISCOVERY",
                "lifecycle_state": "RELEASE_FROZEN",
                "validation_consumption": "NOT_APPLICABLE",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    entries.append({"path": "release-descriptor.json", "size": descriptor.stat().st_size, "sha256": _hash(descriptor)})
    manifest = release / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "ovc-evidence-release-manifest/v1",
                "release_id": release_id,
                "manifest_id": manifest_id,
                "bucket": "test",
                "prefix": "canonical",
                "authority_state": "CANDIDATE",
                "repository_commit": "0" * 40,
                "source_ref": "test",
                "files": entries,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    binding = OptAReleaseBinding(
        role="DISCOVERY",
        release_id=release_id,
        manifest_id=manifest_id,
        manifest_sha256=_hash(manifest),
        payload_file_count=len(entries),
        payload_bytes=sum(item["size"] for item in entries),
        price_file_count=len(rows_by_path),
        scope_file_counts=tuple((clock, side, count) for (clock, side), count in sorted(scopes.items())),
    )
    return release, binding


def complete_fixture(root: Path) -> tuple[Path, ReleaseBinding, Path, OptAReleaseBinding]:
    release_id = "OPT-A.GBPUSD.DISCOVERY.TEST.v2"
    manifest_id = "MANIFEST.OPT-A.GBPUSD.DISCOVERY.TEST.v2"
    rows_by_path: dict[str, list[dict[str, str]]] = {}
    records_by_path: dict[str, list[dict]] = {}
    index = 0
    for clock, step in (("15M", 15 * 60 * 1000), ("2H_A_L", 2 * 60 * 60 * 1000)):
        for side in ("BID", "ASK"):
            source_path = f"canonical/{clock}/{side}/test.csv"
            rows = []
            records = []
            for number in range(2):
                timestamp = 1_609_459_200_000 + number * step
                row = {"timestamp": str(timestamp), "open": "1.1000", "high": "1.1020", "low": "1.0990", "close": "1.1010", "volume": "1"}
                rows.append(row)
                records.append(
                    primitive(
                        record_index=index,
                        release_id=release_id,
                        manifest_id=manifest_id,
                        clock=clock,
                        side=side,
                        source_path=source_path,
                        timestamp_ms=timestamp,
                        open_=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                    )
                )
                index += 1
            rows_by_path[source_path] = rows
            records_by_path[f"records/{clock}/{side}/test.c1.jsonl.gz"] = records
    price_release, price_binding = opt_a_root(root, release_id=release_id, manifest_id=manifest_id, rows_by_path=rows_by_path)
    for records in records_by_path.values():
        for record in records:
            record["parent_manifest_sha256"] = price_binding.manifest_sha256
    c1_release, c1_binding = c1_root(root, records_by_path)
    return c1_release, c1_binding, price_release, price_binding


class WP5ReplayTests(unittest.TestCase):
    def test_both_canonical_parent_releases_are_fully_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            c1_release, c1_binding, price_release, price_binding = complete_fixture(Path(tmp))
            verified_c1 = verify_canonical_release(c1_release, c1_binding)
            verified_price = verify_opt_a_release(price_release, price_binding)
            self.assertEqual(len(verified_c1.record_paths), 4)
            self.assertEqual(len(verified_price.price_paths), 4)

    def test_changed_opt_a_price_file_is_rejected_before_join(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, _, price_release, price_binding = complete_fixture(Path(tmp))
            price = price_release / "files" / "canonical" / "15M" / "BID" / "test.csv"
            price.write_text(price.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(PriceParentError, "OPT_A_PAYLOAD_SIZE_MISMATCH"):
                verify_opt_a_release(price_release, price_binding)

    def test_exact_parent_replay_emits_local_and_parent_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c1_release, c1_binding, price_release, price_binding = complete_fixture(root)
            summary = run_verified_role_replay(
                verify_canonical_release(c1_release, c1_binding),
                verify_opt_a_release(price_release, price_binding),
                root / "out",
            )
            self.assertEqual(summary.input_records, 8)
            self.assertEqual(summary.state_records, 12)
            self.assertEqual(summary.scope_count, 6)
            self.assertEqual(summary.transition_records, 0)

    def test_combined_scope_never_selects_a_future_2h_parent(self) -> None:
        earlier = ({"level_type": "RANGE_LOW", "value": "1.0"},)
        future = ({"level_type": "RANGE_LOW", "value": "2.0"},)
        resolver = FirstValidParentResolver(
            [
                ("2021-01-01T02:00:00Z", earlier),
                ("2021-01-01T04:00:00Z", future),
            ]
        )
        self.assertEqual(resolver({"close_time": "2021-01-01T01:45:00Z"}), ())
        self.assertEqual(resolver({"close_time": "2021-01-01T02:00:00Z"}), earlier)
        self.assertEqual(resolver({"close_time": "2021-01-01T03:45:00Z"}), earlier)
        self.assertEqual(resolver({"close_time": "2021-01-01T04:00:00Z"}), future)

    def test_c1_price_primitive_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c1_release, c1_binding, price_release, price_binding = complete_fixture(root)
            shard = c1_release / "files" / "records" / "15M" / "BID" / "test.c1.jsonl.gz"
            records = []
            with gzip.open(shard, "rt", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            records[0]["measurements"]["range_abs"] = "9"
            with shard.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
                    for record in records:
                        handle.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
            manifest = json.loads((c1_release / "manifest.json").read_text(encoding="utf-8"))
            item = next(entry for entry in manifest["files"] if entry["path"] == "records/15M/BID/test.c1.jsonl.gz")
            item["size_bytes"] = shard.stat().st_size
            item["sha256"] = _hash(shard)
            manifest["payload_bytes"] = sum(entry["size_bytes"] for entry in manifest["files"])
            (c1_release / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            rebound = replace(c1_binding, manifest_sha256=_hash(c1_release / "manifest.json"))
            with self.assertRaisesRegex(ReplayError, "C1_PRICE_PRIMITIVE_MISMATCH"):
                run_verified_role_replay(
                    verify_canonical_release(c1_release, rebound),
                    verify_opt_a_release(price_release, price_binding),
                    root / "out",
                )

    def test_wrong_c1_manifest_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            c1_release, c1_binding, _, _ = complete_fixture(Path(tmp))
            wrong = replace(c1_binding, manifest_id="MANIFEST.C1.WRONG")
            with self.assertRaisesRegex(ReplayError, "WRONG_MANIFEST_ID"):
                verify_canonical_release(c1_release, wrong)


if __name__ == "__main__":
    unittest.main()
