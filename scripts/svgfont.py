"""Embed the bundled UI font into generated SVGs.

GitHub READMEs cannot set the page's font, but text drawn inside an SVG image
renders with whatever font the SVG embeds. The variable Geist subset in
`assets/fonts/` is inlined as a base64 WOFF2 `@font-face`, so every visitor sees
the same typeface instead of falling back to Segoe UI / SF / Roboto.

To change the typeface, drop a licensed font into `assets/fonts/`, update
`FONT_PATH`, `FAMILY` and the `FONT` constant in the build scripts, and keep the
licence file next to the font.
"""

from __future__ import annotations

import base64
import functools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "assets" / "fonts" / "geist-subset.woff2"
FAMILY = "Geist"


@functools.lru_cache(maxsize=1)
def font_face() -> str:
    """A `@font-face` rule with the subset inlined as a data URI."""
    encoded = base64.b64encode(FONT_PATH.read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'{FAMILY}';"
        f"src:url(data:font/woff2;base64,{encoded}) format('woff2');"
        "font-weight:100 900;font-style:normal;font-display:block;}"
    )
