#!/usr/bin/env python3
"""Generate the static Open Graph cards used by Listening Notes.

The cards intentionally use typography rather than artist imagery so their
visual identity remains stable as the Radar changes. On macOS, `sips` renders
the committed SVG masters into the PNG files used by social platforms.
"""

from pathlib import Path
from subprocess import run
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "social"
WIDTH, HEIGHT = 1200, 630

CARDS = {
    "listening-notes-og": {
        "masthead": "LISTENING NOTES",
        "title": ["LISTENING", "NOTES"],
        "tagline": "Essays, listening paths and live-music notes.",
        "territory": "Tokyo · Washington · Baltimore · Philadelphia · Newark · New York",
    },
    "radar-og-en": {
        "masthead": "LISTENING NOTES",
        "title": ["RADAR"],
        "tagline": "Live music worth making room for.",
        "territory": "Tokyo · Washington · Baltimore · Philadelphia · Newark · New York",
    },
    "radar-og-es": {
        "masthead": "LISTENING NOTES",
        "title": ["RADAR"],
        "tagline": "Música por la que vale la pena viajar.",
        "territory": "Tokio · Washington · Baltimore · Filadelfia · Newark · Nueva York",
    },
}


def text(value: str) -> str:
    return escape(value)


def card_svg(card: dict[str, object]) -> str:
    title = card["title"]
    assert isinstance(title, list)
    title_lines = []
    if len(title) == 1:
        title_lines.append(f'<text class="title" x="82" y="338">{text(title[0])}</text>')
    else:
        title_lines.extend(
            f'<text class="title title--stacked" x="82" y="{267 + index * 142}">{text(line)}</text>'
            for index, line in enumerate(title)
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="#0b0c10"/>
  <line x1="82" y1="94" x2="1118" y2="94" stroke="#2a2d34" stroke-width="2"/>
  <rect x="82" y="93" width="92" height="2" fill="#ff4d6d"/>
  <style>
    .masthead {{ fill:#f3efe6; font-family:Arial, Helvetica, sans-serif; font-size:25px; font-weight:800; letter-spacing:6px; }}
    .title {{ fill:#f3efe6; font-family:Georgia, 'Times New Roman', serif; font-size:176px; font-weight:700; }}
    .title--stacked {{ font-size:142px; }}
    .tagline {{ fill:#d0cbc0; font-family:Georgia, 'Times New Roman', serif; font-size:36px; font-style:italic; }}
    .territory {{ fill:#aaa7a0; font-family:Arial, Helvetica, sans-serif; font-size:18px; font-weight:700; letter-spacing:1.4px; }}
  </style>
  <text class="masthead" x="82" y="67">{text(card['masthead'])}</text>
  {''.join(title_lines)}
  <text class="tagline" x="86" y="471">{text(card['tagline'])}</text>
  <line x1="82" y1="525" x2="1118" y2="525" stroke="#2a2d34" stroke-width="2"/>
  <text class="territory" x="84" y="569">{text(card['territory'])}</text>
</svg>'''


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, card in CARDS.items():
        svg_path = OUTPUT / f"{name}.svg"
        png_path = OUTPUT / f"{name}.png"
        svg_path.write_text(card_svg(card), encoding="utf-8")
        run(["sips", "-s", "format", "png", str(svg_path), "--out", str(png_path)], check=True, capture_output=True)
        print(f"Wrote {svg_path.relative_to(ROOT)} and {png_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
