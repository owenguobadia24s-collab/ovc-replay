from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ActiveStackError(ValueError):
    pass


POINTER_PATH = Path("registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActiveStackError(f"ACTIVE_STACK_UNREADABLE:{path}") from exc
    if not isinstance(value, dict):
        raise ActiveStackError(f"ACTIVE_STACK_INVALID_OBJECT:{path}")
    return value


def load_active_stack(repository_root: Path) -> dict[str, Any]:
    pointer = _read_json(repository_root / POINTER_PATH)
    state_rel = pointer.get("authoritative_state")
    if not isinstance(state_rel, str) or not state_rel:
        raise ActiveStackError("ACTIVE_STACK_POINTER_MISSING_STATE")
    state = _read_json(repository_root / state_rel)
    if state.get("programme_id") != pointer.get("programme_id"):
        raise ActiveStackError("ACTIVE_STACK_POINTER_PROGRAMME_MISMATCH")
    # QA_REVIEW is usable on an isolated candidate branch, APPROVED after the
    # delegated implementation-assurance gate, and COMPLETED after main merge.
    # All other terminal/failure states fail closed.
    if state.get("status") not in {"QA_REVIEW", "APPROVED", "COMPLETED"}:
        raise ActiveStackError(f"ACTIVE_STACK_NOT_USABLE:{state.get('status')}")
    if state.get("active_spine") != ["OPT-A", "OPT-B.C1.v2", "OPT-B.C2.vNext", "OPT-B.C2E.v0.2"]:
        raise ActiveStackError("ACTIVE_STACK_SPINE_MISMATCH")
    return state


def classification(state: dict[str, Any], layer_id: str) -> str:
    classes = state.get("classifications")
    if not isinstance(classes, dict):
        raise ActiveStackError("ACTIVE_STACK_CLASSIFICATIONS_MISSING")
    matches = [name for name, members in classes.items() if isinstance(members, list) and layer_id in members]
    if len(matches) != 1:
        raise ActiveStackError(f"ACTIVE_STACK_CLASSIFICATION_AMBIGUOUS:{layer_id}:{matches}")
    return matches[0]


def require_active_producer(state: dict[str, Any], layer_id: str) -> None:
    resolved = classification(state, layer_id)
    if resolved != "ACTIVE":
        raise ActiveStackError(f"ACTIVE_STACK_PRODUCER_NOT_ACTIVE:{layer_id}:{resolved}")


def require_market_envelope(
    state: dict[str, Any], *, instrument: str, side: str, clock: str, research_role: str
) -> None:
    envelope = state.get("market_envelope")
    if not isinstance(envelope, dict):
        raise ActiveStackError("ACTIVE_STACK_MARKET_ENVELOPE_MISSING")
    if instrument != envelope.get("instrument"):
        raise ActiveStackError(f"ACTIVE_STACK_INSTRUMENT_DENIED:{instrument}")
    if side not in envelope.get("sides", []):
        raise ActiveStackError(f"ACTIVE_STACK_SIDE_DENIED:{side}")
    if clock not in envelope.get("clocks", []):
        raise ActiveStackError(f"ACTIVE_STACK_CLOCK_DENIED:{clock}")
    if research_role not in envelope.get("research_roles", []):
        raise ActiveStackError(f"ACTIVE_STACK_ROLE_DENIED:{research_role}")
    if envelope.get("validation") != "LOCKED_UNCONSUMED":
        raise ActiveStackError("ACTIVE_STACK_VALIDATION_FIREWALL_DRIFT")


def require_new_evidence_route(
    repository_root: Path, *, instrument: str, side: str, clock: str, research_role: str
) -> dict[str, Any]:
    state = load_active_stack(repository_root)
    require_market_envelope(
        state, instrument=instrument, side=side, clock=clock, research_role=research_role
    )
    for layer_id in state["active_spine"]:
        require_active_producer(state, layer_id)
    if classification(state, "OPT-B.C2.v2") != "LEGACY_INACTIVE":
        raise ActiveStackError("ACTIVE_STACK_LEGACY_C2_NOT_RETIRED")
    return state
