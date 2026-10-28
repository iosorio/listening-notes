#!/usr/bin/env python3
"""Report missing listening links without inventing research or blocking honest unknowns."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

try:
    from .enrichment_common import valid_apple_music_url
except ImportError:
    from enrichment_common import valid_apple_music_url


def audit(events: list[dict], today: str) -> dict:
    rows = []
    for event in events:
        if event.get("status") in {"attended", "passed"} or (event["dates"].get("end") or event["dates"]["start"]) < today:
            continue
        if any(valid_apple_music_url(item.get("apple_music_url")) for item in event.get("recommended_listening", [])):
            continue
        declaration = event.get("enrichment", {})
        rows.append({
            "id": event["id"], "artist": event["artist"], "concert_date": event["dates"]["start"],
            "canonicalized_at": event.get("canonicalized_at"), "status": declaration.get("status", "unreviewed"),
            "missing": declaration.get("missing", []), "note": declaration.get("note"),
            "official_event": event.get("links", {}).get("official_event"),
        })
    rows.sort(key=lambda row: (row["concert_date"], row["id"]))
    return {"checked_on": today, "missing_apple_music": len(rows), "events": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--events", type=Path, default=Path(__file__).resolve().parents[1] / "radar/events.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    date.fromisoformat(args.today)
    report = json.dumps(audit(json.loads(args.events.read_text())["events"], args.today), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(report)
    print(report, end="")
