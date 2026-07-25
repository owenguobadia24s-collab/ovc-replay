from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_BINARY_SUFFIXES = {
    ".parquet", ".feather", ".arrow", ".orc", ".h5", ".hdf5",
    ".duckdb", ".sqlite", ".sqlite3", ".db", ".zip", ".7z", ".gz",
}
MARKET_COLUMNS = {"timestamp", "time", "open", "high", "low", "close", "volume", "bid", "ask"}


def tracked_paths() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [Path(item.decode("utf-8")) for item in output.split(b"\0") if item]


class NoRawMarketDataInGitTests(unittest.TestCase):
    def test_no_forbidden_binary_data_formats_are_tracked(self) -> None:
        violations = [path.as_posix() for path in tracked_paths() if path.suffix.lower() in FORBIDDEN_BINARY_SUFFIXES]
        self.assertEqual([], violations)

    def test_csv_files_are_governance_only(self) -> None:
        violations: list[str] = []
        for relative in tracked_paths():
            if relative.suffix.lower() != ".csv":
                continue
            if not (relative.as_posix().startswith("docs/history/") or relative.as_posix().startswith("legacy/quarantine/")):
                violations.append(f"{relative}: CSV outside historical governance roots")
                continue
            first_line = (ROOT / relative).read_text(encoding="utf-8", errors="replace").splitlines()[0].lower()
            columns = {item.strip().strip('"') for item in first_line.split(",")}
            if len(columns & MARKET_COLUMNS) >= 4:
                violations.append(f"{relative}: market-like CSV header")
        self.assertEqual([], violations)

    def test_active_data_root_contains_declarations_only(self) -> None:
        data_root = ROOT / "data"
        violations = [
            path.relative_to(ROOT).as_posix()
            for path in data_root.rglob("*")
            if path.is_file() and path.suffix.lower() not in {".md", ".txt"}
        ]
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
