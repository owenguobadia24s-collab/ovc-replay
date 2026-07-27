from __future__ import annotations

import argparse
import csv
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from . import dukascopy_intake as base

APPROVED_GATE = "RPS-G1A"
APPROVED_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
APPROVED_START = datetime(2026, 6, 22, tzinfo=timezone.utc)
APPROVED_END = datetime(2026, 6, 25, tzinfo=timezone.utc)
COMPRESSED_BYTE_LIMIT = 25 * 1024 * 1024
EXPANDED_BYTE_LIMIT = 100 * 1024 * 1024
PROVIDER = "DUKASCOPY"
INSTRUMENT = "GBPUSD"
ADAPTER = "OVC_DIRECT_BI5_CANDLE_ADAPTER"
ADAPTER_VERSION = "1.2.0-rps-g1a-candidate"
USER_AGENT = (
    "ovc-replay-rps-g1a/1.2 "
    "(+https://github.com/owenguobadia24s-collab/ovc-replay)"
)
DATE_TOKEN = "20260622_20260625"

FetchResult = base.FetchResult
CandleRow = base.CandleRow
IntakeError = base.IntakeError
Fetcher = base.Fetcher


def _m1_relative(day: datetime, side: str) -> str:
    return base._m1_relative(day, side)


def _h1_relative(start: datetime, side: str) -> str:
    return base._h1_relative(start, side)


def _profile_source_object_id(clock: str, side: str) -> str:
    return f"SRC.DUKASCOPY.GBPUSD.{clock}.{side}.{DATE_TOKEN}.v1"


def _profile_write_csv(
    root: Path,
    *,
    clock: str,
    side: str,
    rows: Sequence[CandleRow],
) -> tuple[Path, bytes]:
    filename = f"GBPUSD_{clock}_{side}_{DATE_TOKEN}_UTC.csv"
    path = root / "source-objects" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntakeError(f"refusing to overwrite source object: {path}")
    lines = [",".join(base.ORDERED_COLUMNS)]
    lines.extend(",".join(row.csv_row()) for row in rows)
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return path, payload


@contextmanager
def _amended_profile() -> Iterator[None]:
    replacements = {
        "APPROVED_GATE": APPROVED_GATE,
        "APPROVED_SLICE_ID": APPROVED_SLICE_ID,
        "APPROVED_START": APPROVED_START,
        "APPROVED_END": APPROVED_END,
        "COMPRESSED_BYTE_LIMIT": COMPRESSED_BYTE_LIMIT,
        "EXPANDED_BYTE_LIMIT": EXPANDED_BYTE_LIMIT,
        "ADAPTER_VERSION": ADAPTER_VERSION,
        "USER_AGENT": USER_AGENT,
        "_write_csv": _profile_write_csv,
        "_source_object_id": _profile_source_object_id,
    }
    previous = {name: getattr(base, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def preflight(
    *,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    with _amended_profile():
        return base.preflight(repository_root=repository_root, environ=environ)


def execute_intake(
    *,
    repository_root: Path,
    gate: str,
    environ: Mapping[str, str] | None = None,
    fetcher: Fetcher = base._request,
) -> dict[str, object]:
    with _amended_profile():
        return base.execute_intake(
            repository_root=repository_root,
            gate=gate,
            environ=environ,
            fetcher=fetcher,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-local exact RPS-G1A Dukascopy intake candidate; "
            "provider execution is denied in CI and requires operator approval."
        )
    )
    parser.add_argument("command", choices=("preflight", "execute"))
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path.cwd(),
    )
    parser.add_argument(
        "--gate",
        default=None,
        help=f"Required for execute; must equal {APPROVED_GATE}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root=repository_root)
        else:
            result = execute_intake(
                repository_root=repository_root,
                gate=arguments.gate or "",
            )
    except IntakeError as exc:
        print(f"RPS-G1A intake blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
