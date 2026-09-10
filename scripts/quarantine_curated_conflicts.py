#!/usr/bin/env python3
"""Put historical curated-batch conflicts in a review queue without deleting them."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

try:
    from .merge_inbox import CURATED, ROOT, batch_paths, merge
except ImportError:  # Direct script execution.
    from merge_inbox import CURATED, ROOT, batch_paths, merge


REVIEW = ROOT / "radar/inbox/review/curated"
MANIFEST = REVIEW / "conflicts.json"


def collect_conflicts(paths: list[Path], canonical_path: Path, curated_dir: Path) -> dict:
    """Return a deterministic, source-preserving review manifest for conflicts."""
    report = merge(paths, True, canonical_path=canonical_path, curated_dir=curated_dir)
    by_batch: dict[str, list[dict]] = {}
    for kind in ("conflicts", "semantic_conflicts"):
        for conflict in report[kind]:
            by_batch.setdefault(conflict["batch"], []).append({"kind": kind, **conflict})
    entries = []
    for path in paths:
        batch = json.loads(path.read_text())
        conflicts = by_batch.get(batch["batch_id"], [])
        if not conflicts:
            continue
        entries.append({
            "batch_id": batch["batch_id"],
            "source_path": path.relative_to(ROOT).as_posix(),
            "review_path": (REVIEW / path.name).relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "conflicts": conflicts,
        })
    return {
        "schema_version": 1,
        "generated_on": date.today().isoformat(),
        "policy": "Historical conflicts are retained unchanged for explicit human review and are excluded from automated ingestion.",
        "review_batches": entries,
        "active_summary": {
            "added": len(report["added"]),
            "blocked": len(report["blocked"]),
            "conflicts": len(report["conflicts"]),
            "semantic_conflicts": len(report["semantic_conflicts"]),
        },
    }


def quarantine(manifest: dict, review_dir: Path = REVIEW, manifest_path: Path = MANIFEST) -> None:
    """Move only manifest-listed files, refusing to overwrite prior evidence."""
    destinations = []
    for entry in manifest["review_batches"]:
        source = ROOT / entry["source_path"]
        destination = ROOT / entry["review_path"]
        if not source.exists():
            raise ValueError(f"source batch disappeared: {source}")
        if destination.exists():
            raise ValueError(f"review destination already exists: {destination}")
        destinations.append((source, destination))
    if manifest_path.exists():
        raise ValueError(f"review manifest already exists: {manifest_path}")
    review_dir.mkdir(parents=True, exist_ok=True)
    for source, destination in destinations:
        shutil.move(source, destination)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="scan every active curated creation batch")
    parser.add_argument("--apply", action="store_true", help="move detected historical conflicts into the review queue")
    args = parser.parse_args()
    if not args.all:
        parser.error("choose --all")
    try:
        manifest = collect_conflicts(batch_paths(argparse.Namespace(batch=None)), ROOT / "radar/events.json", CURATED)
        if args.apply:
            quarantine(manifest)
    except ValueError as error:
        parser.exit(2, f"quarantine curated conflicts: {error}\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
