#!/usr/bin/env python3
"""Check the static social preview contract without third-party packages."""

import struct
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://iosorio.github.io/listening-notes"
REQUIRED = {
    "og:title", "og:description", "og:type", "og:url", "og:image",
    "og:image:width", "og:image:height", "og:site_name", "og:locale",
    "twitter:card", "twitter:title", "twitter:description", "twitter:image",
}
PAGES = {
    "index.html": ("es_MX", "assets/social/listening-notes-og.png"),
    "en/index.html": ("en_US", "assets/social/listening-notes-og.png"),
    "radar/index.html": ("en_US", "assets/social/radar-og-en.png"),
    "radar/es/index.html": ("es_MX", "assets/social/radar-og-es.png"),
}


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and values.get("property"):
            self.meta[values["property"]] = values.get("content") or ""
        if tag == "meta" and values.get("name", "").startswith("twitter:"):
            self.meta[values["name"]] = values.get("content") or ""
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        header = image.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", header[16:24])


def main() -> None:
    errors: list[str] = []
    for relative_page, (locale, relative_image) in PAGES.items():
        parser = HeadParser()
        parser.feed((ROOT / relative_page).read_text(encoding="utf-8"))
        missing = REQUIRED - parser.meta.keys()
        if missing:
            errors.append(f"{relative_page}: missing {', '.join(sorted(missing))}")
        if not parser.canonical.startswith(ORIGIN):
            errors.append(f"{relative_page}: canonical must be an absolute Listening Notes URL")
        if parser.meta.get("og:locale") != locale:
            errors.append(f"{relative_page}: expected locale {locale}")
        for field in ("og:image", "twitter:image"):
            value = parser.meta.get(field, "")
            if not value.startswith(f"{ORIGIN}/"):
                errors.append(f"{relative_page}: {field} must be absolute")
            if urlparse(value).path != f"/listening-notes/{relative_image}":
                errors.append(f"{relative_page}: {field} points to the wrong card")
        if parser.meta.get("og:image:width") != "1200" or parser.meta.get("og:image:height") != "630":
            errors.append(f"{relative_page}: image dimensions must be declared as 1200×630")

    for relative_image in sorted({image for _, image in PAGES.values()}):
        image = ROOT / relative_image
        if not image.exists():
            errors.append(f"missing image: {relative_image}")
        elif png_size(image) != (1200, 630):
            errors.append(f"{relative_image}: image must be 1200×630")

    if errors:
        raise SystemExit("Social-card validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated Open Graph metadata and {len(set(image for _, image in PAGES.values()))} social cards")


if __name__ == "__main__":
    main()
