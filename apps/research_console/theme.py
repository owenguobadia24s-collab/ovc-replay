from __future__ import annotations

from pathlib import Path

DESIGN_TOKENS: dict[str, str] = {
    "background": "#0B1220",
    "panel": "#111B2E",
    "panel_alt": "#0F192A",
    "panel_border": "#25324A",
    "primary_text": "#F4F7FB",
    "muted_text": "#94A3B8",
    "blue": "#4F7CFF",
    "green": "#25C281",
    "amber": "#F3B94E",
    "red": "#EF5A67",
    "purple": "#8B5CF6",
    "cyan": "#35C7D8",
}

CSS_PATH = Path(__file__).resolve().parent / "assets" / "console.css"


def load_css_text() -> str:
    if not CSS_PATH.is_file():
        raise FileNotFoundError(f"Research Console stylesheet unavailable: {CSS_PATH}")
    return CSS_PATH.read_text(encoding="utf-8")
