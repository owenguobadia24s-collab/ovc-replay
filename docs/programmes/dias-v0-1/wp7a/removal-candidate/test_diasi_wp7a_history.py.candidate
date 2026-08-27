import json
from pathlib import Path
import subprocess

from ovc.development.skills.dias_history import interpret_diasi_history


ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = ROOT / "registries/implementation/dias_v0_1"
WP7A = ROOT / "docs/programmes/dias-v0-1/wp7a"
SOURCE_COMMIT = "e7531677f544766022e21181b802dab6e0e84227"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def historical(path: str) -> dict:
    raw = subprocess.run(
        ("git", "show", f"{SOURCE_COMMIT}:{path}"),
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return json.loads(raw)


def test_every_retained_programme_state_is_interpretable_without_runtime() -> None:
    states = sorted(STATE_ROOT.glob("DIASI_*.json"))
    assert len(states) >= 10
    interpretations = [interpret_diasi_history(load(path)) for path in states]
    assert all(item.authority_effect == "NONE_INTERPRETATION_ONLY" for item in interpretations)
    assert len({item.interpretation_id for item in interpretations}) == len(interpretations)


def test_archives_preserve_pre_removal_route_and_writer_objects_exactly() -> None:
    route = load(WP7A / "history/VIT_SELECTED_CLASS_ROUTE_v0_1_HISTORICAL.json")
    writer = load(WP7A / "history/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1_HISTORICAL.json")
    assert route == historical("registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
    assert writer == historical("registries/development/skills/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1.json")
    assert interpret_diasi_history(route).old_route_disposition == "DISABLED_RETAINED"
    assert interpret_diasi_history(writer).old_route_disposition == "DISABLED_RETAINED_FENCED_GENERATION_1"
