from __future__ import annotations

"""C2P2-RS0 execution adapter binding current-source materialisation to canonical C2E2-WP6 runtime.

The current C2E source replay module retains historical projection helpers. Its
canonical WP6 execution surface is source_replay_runtime, which binds only
lawful upstream dependency rows before the reverse-dependency firewall. This
adapter imports that runtime first, binds the in-memory current-C2 output to the
same persisted JSON boundary consumed by canonical C2E source replay, and then
delegates to the bounded RS0 source materialiser without changing C2E rules or
pack semantics.
"""

import json
from typing import Any, Mapping

from ovc.opt_b.c2e_v2 import source_replay as c2e_base
from ovc.opt_b.c2e_v2 import source_replay_runtime as c2e_runtime
from ovc.opt_b.c2p_v0_2 import rs0_source_materialisation as materialisation


def _persisted_c2_value(value: Any) -> Any:
    """Reproduce the canonical persisted-C2 JSON numeric boundary in memory.

    C2E source replay deliberately rejects runtime floats and normally consumes
    C2 materialisation through JSON loaders configured with ``parse_float=str``.
    RS0 builds the same C2 materialisation in memory to stay within the frozen
    capacity budget, so this adapter must reproduce that persistence boundary
    before C2E sees the rows. The JSON token emitted for every finite float is
    preserved exactly and reloaded as a string; non-finite values fail closed.
    """
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return json.loads(encoded, parse_float=str)


def _bind_current_c2_persistence_boundary() -> None:
    current = materialisation._event_maps
    if getattr(current, "_c2p2_persisted_boundary", False):
        return

    def persisted_event_maps(event: Mapping[str, Any], prepared: Mapping[str, Any]) -> dict[str, Any]:
        maps = dict(current(event, prepared))
        # parent_observations is a side-wide immutable index repeatedly reused by
        # every frame. C2E reads only identity/FVT/hash fields from those rows, so
        # avoid an O(population^2) normalization. Event-local C2 surfaces contain
        # every numeric field consumed by the stable comparison projection.
        for key in (
            "observations",
            "profiles",
            "memberships",
            "contexts",
            "levels",
            "containers",
            "relation_sets",
        ):
            maps[key] = _persisted_c2_value(maps[key])
        return maps

    setattr(persisted_event_maps, "_c2p2_persisted_boundary", True)
    materialisation._event_maps = persisted_event_maps


def main() -> None:
    if c2e_base._dependencies is not c2e_runtime._dependencies:
        raise RuntimeError("C2E2_WP6_RUNTIME_DEPENDENCY_BINDING_NOT_ACTIVE")
    _bind_current_c2_persistence_boundary()
    materialisation.main()


if __name__ == "__main__":
    main()
