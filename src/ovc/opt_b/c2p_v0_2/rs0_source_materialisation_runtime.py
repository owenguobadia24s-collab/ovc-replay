from __future__ import annotations

"""C2P2-RS0 execution adapter binding current-source materialisation to canonical C2E2-WP6 runtime.

The current C2E source replay module retains historical projection helpers.  Its
canonical WP6 execution surface is source_replay_runtime, which binds only
lawful upstream dependency rows before the reverse-dependency firewall.  This
adapter imports that runtime first, verifies the binding, and then delegates to
the bounded RS0 source materialiser without changing C2E rules or pack
semantics.
"""

from ovc.opt_b.c2e_v2 import source_replay as c2e_base
from ovc.opt_b.c2e_v2 import source_replay_runtime as c2e_runtime
from ovc.opt_b.c2p_v0_2 import rs0_source_materialisation as materialisation


def main() -> None:
    if c2e_base._dependencies is not c2e_runtime._dependencies:
        raise RuntimeError("C2E2_WP6_RUNTIME_DEPENDENCY_BINDING_NOT_ACTIVE")
    materialisation.main()


if __name__ == "__main__":
    main()
