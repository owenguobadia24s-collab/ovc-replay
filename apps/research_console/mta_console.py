from __future__ import annotations

from typing import Any, Mapping

from apps.research_console import shell as base_shell
from apps.research_console.mta_audit_surface import load_mta_reference, projection_identity, render_mta_audit_surface
from apps.research_console.rc_g5_console import run_console as run_rc_g5_console

def run_console(
    identity: Mapping[str, Any] | None = None,
    *,
    c1_projection: Mapping[str, Any] | None = None,
    c2_sequence_projection: Mapping[str, Any] | None = None,
) -> None:
    """Run the accepted RC-G5 console with the MTA-WP7 read-only audit surface."""

    reference = load_mta_reference()
    represented = dict(identity or {})
    represented.update({f"mta_{key}": value for key, value in projection_identity(reference).items()})
    original_research = base_shell.render_research

    def render_research_with_mta(bundle: Mapping[str, Any]) -> None:
        original_research(bundle)
        render_mta_audit_surface(reference)

    base_shell.render_research = render_research_with_mta
    try:
        run_rc_g5_console(
            represented,
            c1_projection=c1_projection,
            c2_sequence_projection=c2_sequence_projection,
        )
    finally:
        base_shell.render_research = original_research
