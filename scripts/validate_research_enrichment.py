#!/usr/bin/env python3
"""Validate untrusted RADAR enrichment research without writing data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .enrichment_common import (
        CANONICAL,
        PROCESSED_ENRICHMENT,
        RESEARCH,
        ROOT,
        EnrichmentError,
        fail,
        read_json,
        sha256_file,
        validate_research_batch,
    )
except ImportError:  # Direct script execution.
    from enrichment_common import (
        CANONICAL,
        PROCESSED_ENRICHMENT,
        RESEARCH,
        ROOT,
        EnrichmentError,
        fail,
        read_json,
        sha256_file,
        validate_research_batch,
    )


def _research_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        fail(f"{path}: research batch must be inside {root}")


def processed_archive_for(path: Path, processed_dir: Path, root: Path) -> Path | None:
    """Return the exact processed archive for research, rejecting stale provenance."""
    research = read_json(path)
    research_path = _research_path(path, root)
    batch_id = research.get("batch_id")
    digest = sha256_file(path)
    exact_matches = []

    for archived_path in sorted(processed_dir.glob("*.json")):
        archived = read_json(archived_path)
        review = archived.get("review")
        if not isinstance(review, dict):
            continue
        linked = review.get("research_path") == research_path or (
            isinstance(batch_id, str)
            and bool(batch_id.strip())
            and review.get("research_batch_id") == batch_id
        )
        if not linked:
            continue
        checks = {
            "research_path": review.get("research_path") == research_path,
            "research_batch_id": review.get("research_batch_id") == batch_id,
            "processed_batch_id": archived.get("batch_id") == batch_id,
            "research_sha256": review.get("research_sha256") == digest,
            "patches": archived.get("patches") == research.get("events"),
        }
        mismatches = [name for name, matches in checks.items() if not matches]
        if mismatches:
            fail(
                f"{path}: processed provenance mismatch in {archived_path}: "
                f"{', '.join(mismatches)}"
            )
        exact_matches.append(archived_path)

    if len(exact_matches) > 1:
        fail(f"{path}: multiple processed archives claim this research batch")
    return exact_matches[0] if exact_matches else None


def validate_unprocessed_research(
    paths: list[Path],
    canonical_path: Path = CANONICAL,
    processed_dir: Path = PROCESSED_ENRICHMENT,
    root: Path = ROOT,
) -> dict:
    """Validate only research that has not been archived with exact provenance."""
    canonical = read_json(canonical_path)
    report = {"validated": [], "already_processed": []}
    for path in sorted(path.resolve() for path in paths):
        archived_path = processed_archive_for(path, processed_dir, root)
        if archived_path is not None:
            report["already_processed"].append(
                {
                    "batch_id": read_json(path).get("batch_id"),
                    "research": _research_path(path, root),
                    "processed": _research_path(archived_path, root),
                }
            )
            continue
        batch_report = validate_research_batch(read_json(path), canonical, path)
        report["validated"].append(batch_report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", nargs="?", help="one JSON file directly inside radar/inbox/research")
    parser.add_argument(
        "--all-unprocessed",
        action="store_true",
        help="validate every research batch not already preserved in processed/enrichment",
    )
    args = parser.parse_args()
    if bool(args.batch) == args.all_unprocessed:
        parser.error("provide one batch or --all-unprocessed")
    if args.all_unprocessed:
        try:
            report = validate_unprocessed_research(list(RESEARCH.glob("*.json")))
        except EnrichmentError as error:
            parser.exit(2, f"validate research enrichment: {error}\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    path = Path(args.batch).resolve()
    if path.parent != RESEARCH.resolve():
        parser.error("batch must be directly inside radar/inbox/research")
    try:
        report = validate_research_batch(read_json(path), read_json(CANONICAL), path)
    except EnrichmentError as error:
        parser.exit(2, f"validate research enrichment: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
