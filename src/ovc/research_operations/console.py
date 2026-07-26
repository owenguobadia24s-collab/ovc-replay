from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .read_model import ResearchReadModel


class ConsoleWriteDenied(PermissionError):
    pass


class ResearchConsole:
    """Read-only projection over a typed read model.

    The console deliberately exposes no repository, selector, threshold, market,
    probability, exposure, execution or agent mutation method.
    """

    capabilities = {
        "read_model": "READ_ONLY",
        "lineage": "READ_ONLY",
        "health": "READ_ONLY",
        "research_records": "LINK_TO_GOVERNED_CLI_ONLY",
        "repository_mutation": "NONE",
        "selector_mutation": "NONE",
        "threshold_mutation": "NONE",
        "market_classification": "NONE",
        "execution": "NONE",
    }

    def __init__(self, model: ResearchReadModel):
        self.model = model

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for node in self.model.nodes:
            counts[node.object_type] = counts.get(node.object_type, 0) + 1
        return {
            "source_commit": self.model.source_commit,
            "logical_sha256": self.model.logical_sha256,
            "object_counts": dict(sorted(counts.items())),
            "health_count": len(self.model.health),
            "capabilities": dict(self.capabilities),
        }

    def render_html(self, output: Path) -> Path:
        rows = "".join(
            f"<tr><td>{html.escape(node.object_type)}</td><td>{html.escape(node.object_id)}</td>"
            f"<td>{html.escape(node.status)}</td><td>{html.escape(node.authority)}</td>"
            f"<td>{html.escape(', '.join(node.source_refs) or 'NONE')}</td></tr>"
            for node in self.model.nodes
        )
        health = "".join(
            f"<li><strong>{html.escape(str(item['status']))}</strong> {html.escape(str(item['code']))}: "
            f"{html.escape(str(item['detail']))}</li>" for item in self.model.health
        ) or "<li>NONE</li>"
        document = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>OVC Research Console</title>
<style>body{{font-family:system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.5rem;text-align:left}}code{{background:#eee;padding:.15rem}}</style></head>
<body><h1>OVC Research Console</h1>
<p><strong>READ-ONLY</strong> · source commit <code>{html.escape(self.model.source_commit)}</code> · read-model hash <code>{html.escape(self.model.logical_sha256)}</code></p>
<h2>Authority</h2><pre>{html.escape(str(self.capabilities))}</pre>
<h2>Health</h2><ul>{health}</ul>
<h2>Objects</h2><table><thead><tr><th>Type</th><th>ID</th><th>Status</th><th>Authority</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>
</body></html>"""
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document, encoding="utf-8")
        return output

    def mutate(self, *_: Any, **__: Any) -> None:
        raise ConsoleWriteDenied("RO-WP3 console is read-only; use the governed Research Operations CLI for approved writes")
