#!/usr/bin/env python3
"""Generate the profile header as an animated terminal card.

The word YOUNES is set in the pyfiglet ``ansi_shadow`` font and turned into
SVG paths with JetBrains Mono, so the box-drawing stays aligned without
depending on the viewer's fonts. A clip reveal, a thin cursor, and a typed
tagline are SMIL animations. Without animation the card still shows the
finished banner.

Requires: pip install pyfiglet fonttools
And JetBrains Mono on the machine (or BANNER_FONT pointing at the .ttf).
"""

from __future__ import annotations

import os
from pathlib import Path

import pyfiglet
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets"

WORD = "YOUNES"
FIGLET_FONT = "ansi_shadow"
TAGLINE = "terminal tools & efficient local AI"
DURATION = 9.0

# Fractions of DURATION.
REVEAL_END = 0.40
PROMPT_START = 0.26
PROMPT_END = 0.62
HOLD_END = 0.84
FADE_END = 0.93

FONT_SIZE = 23.0
CANVAS_W = 900
CANVAS_H = 292

FONT_CANDIDATES = [
    os.environ.get("BANNER_FONT"),
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf",
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
    "/usr/share/fonts/truetype/macos/JetBrainsMono-Regular.ttf",
]

THEMES = {
    "dark": {
        "file": "banner-dark.svg",
        "bg": "#0d1117",
        "glow": "#222b3d",
        "stroke": "#30363d",
        "chrome": "#8b949e",
        "muted": "#6e7681",
        "text": "#e6edf3",
        "prompt": "#3fb950",
        "stops": ("#5ce1ff", "#8a7dff", "#ff6fb5", "#ffb86b"),
        "blur": 0.65,
        "blur_opacity": 0.7,
    },
    "light": {
        "file": "banner-light.svg",
        "bg": "#f6f8fa",
        "glow": "#ffffff",
        "stroke": "#d0d7de",
        "chrome": "#656d76",
        "muted": "#8c959f",
        "text": "#1f2328",
        "prompt": "#1a7f37",
        "stops": ("#087990", "#6e40c9", "#c42d78", "#9a6700"),
        "blur": 0.4,
        "blur_opacity": 0.35,
    },
}


def find_font() -> str:
    for candidate in FONT_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit(
        "JetBrains Mono was not found. Install it or set BANNER_FONT to a .ttf "
        "with uniform box-drawing advances."
    )


def render_art() -> list[str]:
    raw = pyfiglet.Figlet(font=FIGLET_FONT).renderText(WORD).splitlines()
    while raw and not raw[0].strip():
        raw.pop(0)
    while raw and not raw[-1].strip():
        raw.pop()
    width = max(len(line) for line in raw)
    return [line.ljust(width) for line in raw]


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def keys(*pairs: float) -> str:
    """Format keyTimes, keeping them strictly increasing inside (0, 1)."""
    values = [min(1.0, max(0.0, float(v))) for v in pairs]
    values[0] = 0.0
    values[-1] = 1.0
    fixed = [values[0]]
    for value in values[1:-1]:
        fixed.append(max(value, fixed[-1] + 0.002))
    fixed.append(1.0 if fixed[-1] < 1 else fixed[-1])
    if fixed[-1] > 1:
        fixed[-1] = 1.0
    return ";".join(f"{v:.4f}" for v in fixed)


def glyph_paths(art: list[str], font_path: str) -> tuple[list[str], float, float, float]:
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    upem = font["head"].unitsPerEm
    scale = FONT_SIZE / upem
    advance = 600 * scale  # JetBrains Mono em-square advance for these glyphs
    columns = len(art[0])
    rows = len(art)

    art_w = columns * advance
    art_h = (rows - 1) * FONT_SIZE + (1020 + 300) * scale
    origin_x = (CANVAS_W - art_w) / 2
    # Title bar sits in the top 46px; the rest of the card holds the word.
    top = 58
    baseline0 = top + 1020 * scale

    paths: list[str] = []
    index = 0
    for row, line in enumerate(art):
        baseline = baseline0 + row * FONT_SIZE
        for col, ch in enumerate(line):
            if ch == " ":
                continue
            name = cmap.get(ord(ch))
            if name is None:
                raise SystemExit(f"Font is missing U+{ord(ch):04X} ({ch!r})")
            pen = SVGPathPen(glyph_set)
            transform = Transform(scale, 0, 0, -scale, origin_x + col * advance, baseline)
            glyph_set[name].draw(TransformPen(pen, transform))
            commands = pen.getCommands()
            if not commands:
                continue
            paths.append(f'<path id="g{index}" d="{commands}"/>')
            index += 1

    if not paths:
        raise SystemExit("ASCII art produced no glyphs")
    return paths, art_w, origin_x, art_h


def prompt_lines(theme: dict, origin_x: float) -> str:
    family = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'JetBrains Mono', monospace"
    x = f"{origin_x:.1f}"
    y = CANVAS_H - 36
    common = (
        f'x="{x}" y="{y}" font-family="{family}" font-size="16" '
        f'letter-spacing="0.2"'
    )
    chunks: list[str] = []
    count = len(TAGLINE)
    span = (PROMPT_END - PROMPT_START) / count
    for i in range(count):
        start = PROMPT_START + i * span
        end = start + span
        typed = esc(TAGLINE[:i])
        chunks.append(
            f'<text {common} opacity="0">'
            f'<tspan fill="{theme["prompt"]}">❯ </tspan>'
            f'<tspan fill="{theme["text"]}">{typed}|</tspan>'
            f'<animate attributeName="opacity" dur="{DURATION}s" '
            f'repeatCount="indefinite" values="0;0;1;0;0" '
            f'keyTimes="{keys(0, start, start + 0.004, end, 1)}"/>'
            f"</text>"
        )

    chunks.append(
        f'<text {common} opacity="1">'
        f'<tspan fill="{theme["prompt"]}">❯ </tspan>'
        f'<tspan fill="{theme["text"]}">{esc(TAGLINE)}</tspan>'
        f'<tspan fill="{theme["text"]}">'
        f'<animate attributeName="opacity" dur="1.1s" repeatCount="indefinite" '
        f'values="1;1;0;0" keyTimes="0;0.45;0.5;1"/>|</tspan>'
        f'<animate attributeName="opacity" dur="{DURATION}s" '
        f'repeatCount="indefinite" values="0;0;1;1" '
        f'keyTimes="{keys(0, PROMPT_END, PROMPT_END + 0.02, 1)}"/>'
        f"</text>"
    )
    return "\n    ".join(chunks)


def build_svg(theme: dict, defs: str, art_w: float, origin_x: float, art_h: float) -> str:
    reveal_y = 52
    reveal_h = art_h + 8
    stops = theme["stops"]
    title = "YOUNES — terminal tools and efficient local AI"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}" role="img" aria-label="{title}">
  <title>{title}</title>
  <defs>
    <radialGradient id="bg" cx="0.22" cy="0" r="1.05">
      <stop offset="0" stop-color="{theme["glow"]}"/>
      <stop offset="1" stop-color="{theme["bg"]}"/>
    </radialGradient>
    <linearGradient id="ink" x1="{origin_x:.1f}" y1="0" x2="{origin_x + art_w:.1f}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{stops[0]}"/>
      <stop offset="0.38" stop-color="{stops[1]}"/>
      <stop offset="0.68" stop-color="{stops[2]}"/>
      <stop offset="1" stop-color="{stops[3]}"/>
      <animateTransform attributeName="gradientTransform" type="translate" values="-{art_w * 0.35:.0f} 0; {art_w * 0.45:.0f} 0; -{art_w * 0.35:.0f} 0" dur="{DURATION}s" repeatCount="indefinite"/>
    </linearGradient>
    <clipPath id="reveal">
      <rect x="{origin_x:.1f}" y="{reveal_y}" width="{art_w:.1f}" height="{reveal_h}">
        <animate attributeName="width" dur="{DURATION}s" repeatCount="indefinite" values="0;{art_w:.1f};{art_w:.1f};{art_w:.1f}" keyTimes="{keys(0, REVEAL_END, FADE_END, 1)}"/>
      </rect>
    </clipPath>
    <filter id="glow" x="-12%" y="-40%" width="124%" height="180%">
      <feGaussianBlur stdDeviation="{theme["blur"]}"/>
    </filter>
    {defs}
  </defs>

  <rect width="{CANVAS_W}" height="{CANVAS_H}" rx="18" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="{CANVAS_W - 1}" height="{CANVAS_H - 1}" rx="18" fill="none" stroke="{theme["stroke"]}"/>

  <circle cx="26" cy="24" r="6" fill="#ff5f57"/>
  <circle cx="46" cy="24" r="6" fill="#febc2e"/>
  <circle cx="66" cy="24" r="6" fill="#28c840"/>
  <text x="86" y="29" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14" fill="{theme["chrome"]}">YnsLaf</text>
  <text x="{CANVAS_W - 24}" y="29" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" fill="{theme["muted"]}">zsh</text>

  <g>
    <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite" values="1;1;0;0" keyTimes="{keys(0, HOLD_END, FADE_END, 1)}"/>
    <g clip-path="url(#reveal)">
      <g filter="url(#glow)" fill="url(#ink)" opacity="{theme["blur_opacity"]}">
        {"".join(f'<use href="#g{i}"/>' for i in range(defs.count("<path ")))}
      </g>
      <g fill="url(#ink)">
        {"".join(f'<use href="#g{i}"/>' for i in range(defs.count("<path ")))}
      </g>
    </g>
    <rect y="{reveal_y:.1f}" width="2.5" height="{reveal_h:.1f}" rx="1" fill="{stops[0]}">
      <animate attributeName="x" dur="{DURATION}s" repeatCount="indefinite" values="{origin_x:.1f};{origin_x + art_w:.1f};{origin_x + art_w:.1f};{origin_x:.1f}" keyTimes="{keys(0, REVEAL_END, FADE_END, 1)}"/>
      <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite" values="0.95;0.95;0;0" keyTimes="{keys(0, REVEAL_END, REVEAL_END + 0.045, 1)}"/>
    </rect>
    {prompt_lines(theme, origin_x)}
  </g>
</svg>
'''


def main() -> None:
    art = render_art()
    defs_list, art_w, origin_x, art_h = glyph_paths(art, find_font())
    defs = "\n    ".join(defs_list)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme in THEMES.values():
        svg = build_svg(theme, defs, art_w, origin_x, art_h)
        path = OUT_DIR / theme["file"]
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes, {len(defs_list)} glyphs)")


if __name__ == "__main__":
    main()
