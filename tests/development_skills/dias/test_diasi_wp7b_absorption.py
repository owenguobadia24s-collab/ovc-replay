import json
import os
from pathlib import Path
import subprocess
import sys

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
WP7B = ROOT / "docs/programmes/dias-v0-1/wp7b"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_removal_tree_and_post_merge_receipts_are_bound() -> None:
    evidence = load(WP7B / "DIASI_WP7B_POST_REMOVAL_ASSURANCE.json")
    assert evidence["tree_equal"] is True
    assert evidence["expected_post_removal_tree"] == evidence["observed_post_removal_tree"] == "a0f45e49f9036e281ad044c51aad8124fb38210f"
    assert evidence["post_merge_completion"]["four_content_addressed_receipts_present"] is True
    assert evidence["frozen_suite"] == {"command": "python -m pytest tests/development_skills/dias tests/development_skills/test_pes_vit_qualification_producer.py -q", "passed": 137, "failed": 0}


def test_history_and_owner_local_restart_survive_without_retired_runtime() -> None:
    evidence = load(WP7B / "DIASI_WP7B_POST_REMOVAL_ASSURANCE.json")
    assert evidence["history"]["all_retained_generations_parseable"] is True
    assert evidence["history"]["retired_runtime_required"] is False
    command = "import json; from pathlib import Path; from ovc.development.skills.dias_cutover import validate_live_registry; p=Path('registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json'); assert validate_live_registry(json.loads(p.read_text())).route_generation == 3"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
    subprocess.run([sys.executable, "-c", command], cwd=ROOT, check=True, env=environment)


def test_absorption_has_no_diasi_control_plane_or_replacement_supervisor() -> None:
    absorption = load(WP7B / "DIASI_WP7B_OWNER_ABSORPTION_MANIFEST.json")
    assert all(item["owner"] != "DIASI" for item in absorption["bindings"])
    for field in ("diasi_active_scheduler", "diasi_active_physical_writer", "diasi_independent_currentness_authority", "diasi_liveness_service", "diasi_generic_authority_platform", "generic_replacement_supervisor"):
        assert absorption[field] is False
    route_source = (ROOT / "src/ovc/development/skills/dias_cutover.py").read_text(encoding="utf-8")
    assert route_source.count('"old_route"') == 1
    assert route_source.count('"incumbent_writer"') == 1
    assert "supervisor" not in route_source.lower()


def test_shared_cers_pes_scope_is_explicitly_not_globally_retired() -> None:
    evidence = load(WP7B / "DIASI_WP7B_POST_REMOVAL_ASSURANCE.json")
    cers = load(ROOT / "registries/development/skills/cers/CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_4.json")
    assert len(cers["entries"]) == evidence["shared_scope"]["global_cers_active_admissions"] == 5
    assert evidence["shared_scope"]["global_cers_retired"] is False
    assert evidence["shared_scope"]["global_pes_retired"] is False


def test_racpr_is_lawfully_reference_only_and_performance_is_not_invented() -> None:
    disposition = load(WP7B / "DIASI_WP7B_RACPR_REFERENCE_SAFE_DISPOSITION.json")
    assert disposition["classification"] == "REFERENCE_ONLY"
    assert disposition["decision_bearing_proof_substitution"] is False
    assert disposition["reference_fallback"] == "COMPLETE_INDEPENDENTLY_USABLE"
    assert disposition["diasi_operator_proof_gate"] == "NOT_REACHED"
    assert disposition["performance"]["cohort_denominator"] == 0
    assert disposition["performance"]["p90_t_certificate_seconds"] is None
    assert disposition["terminal_branch"] == "DIAS_COMPLETED_REFERENCE_SAFE"


def test_vit_bindings_and_wp7b_state_are_self_consistent() -> None:
    for name in ("DIASI_WP7B_VIT_AUTHORITY_MANIFEST.json", "DIASI_WP7B_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP7B / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])
    state = load(ROOT / "registries/implementation/dias_v0_1/DIASI_CURRENT_v0_12.json")
    assert state["retirement"] is True and state["owner_absorbed"] is True
    assert state["racpr_disposition"] == "REFERENCE_ONLY"
    assert state["terminal_target"] == "DIAS_COMPLETED_REFERENCE_SAFE"
    assert state["next_packet"] == "DIASI-WP9" and state["operator_decision_required"] is False
