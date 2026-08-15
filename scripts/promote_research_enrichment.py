#!/usr/bin/env python3
"""Explicitly promote a reviewed RADAR research batch to the curated queue."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

try:
    from .enrichment_common import (
        CANONICAL, CURATED_ENRICHMENT, CURATED_KIND, RESEARCH, ROOT,
        EnrichmentError, read_json, sha256_file, validate_iso_date, validate_research_batch,
    )
except ImportError:  # Direct script execution.
    from enrichment_common import (
        CANONICAL,
        CURATED_ENRICHMENT,
        CURATED_KIND,
        RESEARCH,
        ROOT,
        EnrichmentError,
        read_json,
        sha256_file,
        validate_iso_date,
        validate_research_batch,
    )


def promote(path: Path, approved_by: str, approved_on: str, dry_run: bool = False) -> tuple[Path, dict]:
    path = path.resolve()
    if path.parent != RESEARCH.resolve():
        raise EnrichmentError("batch must be directly inside radar/inbox/research")
    research = read_json(path)
    validate_research_batch(research, read_json(CANONICAL), path)
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise EnrichmentError("approved_by is required")
    validate_iso_date(approved_on, "approved_on")
    destination = CURATED_ENRICHMENT / path.name
    if destination.exists():
        raise EnrichmentError(f"curated destination already exists: {destination}")
    curated = {
        "batch_version": 1,
        "kind": CURATED_KIND,
        "batch_id": research["batch_id"],
        "review": {
            "research_path": str(path.relative_to(ROOT)),
            "research_batch_id": research["batch_id"],
            "research_sha256": sha256_file(path),
            "approved_by": approved_by,
            "approved_on": approved_on,
        },
        "patches": research["events"],
    }
    if not dry_run:
        CURATED_ENRICHMENT.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(curated, ensure_ascii=False, indent=2) + "\n")
    return destination, curated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", help="reviewed JSON file directly inside radar/inbox/research")
    parser.add_argument("--approved-by", required=True, help="human or interactive reviewer name")
    parser.add_argument("--approved-on", default=date.today().isoformat(), help="review date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        destination, curated = promote(Path(args.batch), args.approved_by, args.approved_on, args.dry_run)
    except EnrichmentError as error:
        parser.exit(2, f"promote research enrichment: {error}\n")
    print(json.dumps({"dry_run": args.dry_run, "destination": str(destination), "batch": curated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
