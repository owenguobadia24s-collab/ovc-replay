"""Final direct-typed impact closure for full-G3 shadow replay.

The previous convergence experiment demonstrated that recursively following reverse
textual referrers is not a constitutional relationship graph: it expands ownership
through documentation chains and manufactures unrelated owner-count changes. Full G3
requires source-bound relationship closure for the candidate delta, not transitive
lexical reachability. This facade therefore freezes the closure as:

1. changed artifacts;
2. their exact declared repository-path references (bounded forward closure);
3. direct source-bound owner/consumer records that explicitly reference those paths;
4. exact current-state pointer/status sources used only for dependency evaluation.

No reverse referrer of a reverse referrer is admitted. Capacity remains fail-closed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import full_enforcement as _base
from . import full_enforcement_bounded as _impl

_MAX_FORWARD_PATHS = 256
_MAX_FORWARD_ROUNDS = 4
_REVERSE_SOURCE_CLASSES = set(_base._SOURCE_BOUND_OWNER_CLASSES) | {"TEST", "IMPLEMENTATION"}


def _direct_typed_impact(
    root: Path,
    *,
    commit: str,
    inventory: Mapping[str, Mapping[str, Any]],
    seed_paths: Sequence[str],
) -> tuple[set[str], dict[str, str], dict[str, list[str]], set[str], list[dict[str, str]], list[str]]:
    known = set(inventory)
    impact = {path for path in seed_paths if path in known}
    texts: dict[str, str] = {}
    referrers: dict[str, set[str]] = defaultdict(set)
    errors: list[str] = []

    def read(path: str) -> str:
        if path not in texts:
            texts[path] = _impl._read_text(root, commit, path)
        return texts[path]

    # Current-state pointers are status evidence only; they do not recursively
    # enlarge the changed-artifact impact graph.
    pointer_paths = sorted(path for path in known if path.endswith("CURRENT_STATE_POINTER.json"))
    for path in pointer_paths:
        read(path)
    current_targets, status_targets, pointer_violations = _impl._pointer_catalog(inventory=inventory, texts=texts)
    for path in sorted(status_targets | current_targets):
        if path in known:
            read(path)

    # Forward declared-path closure is bounded and deterministic.
    frontier = set(impact)
    for _ in range(_MAX_FORWARD_ROUNDS):
        if not frontier:
            break
        additions: set[str] = set()
        for path in sorted(frontier):
            for target in _base._path_refs(read(path), known):
                if _base._artifact_type(target) is None:
                    continue
                referrers[target].add(path)
                additions.add(target)
        new = additions - impact
        impact.update(additions)
        if len(impact) > _MAX_FORWARD_PATHS:
            errors.append("IMPACT_FRONTIER_CAPACITY_EXCEEDED")
            break
        frontier = new
    else:
        if frontier:
            errors.append("IMPACT_FRONTIER_FORWARD_CLOSURE_NOT_BOUNDED")

    if not errors:
        # One direct reverse pass supplies owner/companion/consumer evidence.
        # Reverse sources are *not* themselves reverse-expanded.
        query_targets = sorted(impact)
        for source in sorted(_impl._grep_referrer_sources(root, commit, query_targets)):
            if source not in known or _base._artifact_type(source) not in _REVERSE_SOURCE_CLASSES:
                continue
            source_text = read(source)
            referenced = _base._path_refs(source_text, known) & impact
            if not referenced:
                continue
            for target in referenced:
                referrers[target].add(source)
            impact.add(source)
            if len(impact) > _MAX_FORWARD_PATHS:
                errors.append("IMPACT_FRONTIER_CAPACITY_EXCEEDED")
                break

    # Read all admitted impact sources and record in-impact direct references.
    for path in sorted(impact):
        for target in _base._path_refs(read(path), known):
            if target in impact:
                referrers[target].add(path)

    return (
        impact,
        texts,
        {key: sorted(value) for key, value in referrers.items()},
        status_targets | current_targets,
        pointer_violations,
        errors,
    )


_impl._read_impact_evidence_bounded = _direct_typed_impact

REQUIRED_FULL_G3_RULE_FAMILIES = _impl.REQUIRED_FULL_G3_RULE_FAMILIES
FullG3ReplayError = _impl.FullG3ReplayError
replay_full_g3_candidate = _impl.replay_full_g3_candidate
