import json
from pathlib import Path

from ovc.development.skills.dias_history import interpret_diasi_history


ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = ROOT / "registries/implementation/dias_v0_1"
WP7A = ROOT / "docs/programmes/dias-v0-1/wp7a"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_retained_programme_state_is_interpretable_without_runtime() -> None:
    states = sorted(STATE_ROOT.glob("DIASI_*.json"))
    assert len(states) == 11
    interpretations = [interpret_diasi_history(load(path)) for path in states]
    assert all(item.authority_effect == "NONE_INTERPRETATION_ONLY" for item in interpretations)
    assert len({item.interpretation_id for item in interpretations}) == len(interpretations)


def test_route_and_writer_generations_are_data_only_interpretable() -> None:
    route = interpret_diasi_history(load(WP7A / "history/VIT_SELECTED_CLASS_ROUTE_v0_1_HISTORICAL.json"))
    writer = interpret_diasi_history(load(WP7A / "history/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1_HISTORICAL.json"))
    assert route.route_generation == route.writer_generation == 2
    assert route.old_route_disposition == "DISABLED_RETAINED"
    assert writer.writer_generation == 2
    assert writer.old_route_disposition == "DISABLED_RETAINED_FENCED_GENERATION_1"


def test_archives_are_exact_copies_of_pre_removal_active_records() -> None:
    assert load(WP7A / "history/VIT_SELECTED_CLASS_ROUTE_v0_1_HISTORICAL.json") == load(
        ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json"
    )
    assert load(WP7A / "history/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1_HISTORICAL.json") == load(
        ROOT / "registries/development/skills/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1.json"
    )
