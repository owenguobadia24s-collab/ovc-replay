"""Frontier-decoupled PR/VIT public surface.

The implementation body is preserved byte-identically in
``vit_frontier_decoupling_impl``.  This wrapper narrows only the default
integration-harness path set so programme-local development movement does not
masquerade as a global VIT/SIQ/GRT assurance change.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from . import vit_frontier_decoupling_impl as _impl
from .vit_frontier_decoupling_impl import *  # noqa: F401,F403

DEFAULT_GLOBAL_INTEGRATION_PATTERNS = (
    ".github/workflows/ovc-tiered-tests.yml",
    ".github/workflows/tests.yml",
    "tools/ci/vit_*",
    "tools/ci/prvitr_*",
    "tools/ci/ovc_run_with_main_lease.py",
    "src/ovc/development/skills/vit_*",
    "src/ovc/development/skills/siq_*",
    "registries/development/skills/*vit*",
    "registries/development/skills/*siq*",
)


def classify_frontier_movement(
    *,
    pip: Mapping[str, Any],
    source_predecessor_tree: str,
    current_predecessor_tree: str,
    changed_paths: Iterable[str],
    dependency_frontier_changed: bool = False,
    authority_changed: bool = False,
    global_integration_patterns: Iterable[str] = DEFAULT_GLOBAL_INTEGRATION_PATTERNS,
) -> FrontierMovementDecision:
    """Classify movement with only true shared integration surfaces as global.

    Programme-local development code (for example CERS) is ordinary unrelated
    frontier movement unless the PIP dependency footprint explicitly binds it.
    """
    return _impl.classify_frontier_movement(
        pip=pip,
        source_predecessor_tree=source_predecessor_tree,
        current_predecessor_tree=current_predecessor_tree,
        changed_paths=changed_paths,
        dependency_frontier_changed=dependency_frontier_changed,
        authority_changed=authority_changed,
        global_integration_patterns=global_integration_patterns,
    )
