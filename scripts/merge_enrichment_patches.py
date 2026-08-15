#!/usr/bin/env python3
"""Atomically merge reviewed RADAR enrichment patches into canonical events."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

try:
    from .enrichment_common import (
        CANONICAL, CURATED_ENRICHMENT, PROCESSED_ENRICHMENT, ROOT,
        EnrichmentError, apply_patch, read_json, validate_curated_batch,
    )
except ImportError:  # Direct script execution.
    from enrichment_common import (
        CANONICAL,
        CURATED_ENRICHMENT,
        PROCESSED_ENRICHMENT,
        ROOT,
        EnrichmentError,
        apply_patch,
        read_json,
        validate_curated_batch,
    )


VALIDATOR = ROOT / "scripts/validate_events.py"


def validate_canonical(data: dict) -> None:
    with TemporaryDirectory() as directory:
        target = Path(directory) / "events.json"
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        result = subprocess.run([sys.executable, str(VALIDATOR), str(target)], text=True, capture_output=True)
        if result.returncode:
            raise EnrichmentError(result.stderr.strip() or result.stdout.strip())


def batch_paths(batch: str | None, all_batches: bool) -> list[Path]:
    if bool(batch) == bool(all_batches):
        raise EnrichmentError("choose exactly one of --batch or --all")
    if batch:
        path = Path(batch).resolve()
        if path.parent != CURATED_ENRICHMENT.resolve():
            raise EnrichmentError("batch must be directly inside radar/inbox/curated/enrichment")
        return [path]
    return sorted(CURATED_ENRICHMENT.glob("*.json"))


def merge(
    paths: list[Path],
    dry_run: bool,
    canonical_path: Path = CANONICAL,
    processed_dir: Path = PROCESSED_ENRICHMENT,
    root: Path = ROOT,
    research_dir: Path | None = None,
) -> dict:
    canonical = read_json(canonical_path)
    if canonical.get("schema_version") != 3 or not isinstance(canonical.get("events"), list):
        raise EnrichmentError("canonical events.json must use schema_version 3")
    validate_canonical(canonical)
    report = {"dry_run": dry_run, "batches": [], "events": [], "already_processed": []}
    if not paths:
        return report

    seen_events: set[str] = set()
    actionable: list[tuple[Path, dict, Path]] = []

    # Preflight every batch and archive destination before mutating anything.
    for path in paths:
        batch = read_json(path)
        destination = processed_dir / path.name
        if destination.exists():
            if destination.read_bytes() == path.read_bytes():
                report["already_processed"].append(batch.get("batch_id", path.name))
                continue
            raise EnrichmentError(f"processed destination already exists with different content: {destination}")
        validate_curated_batch(batch, canonical, path, root, research_dir or root / "radar/inbox/research")
        for patch in batch["patches"]:
            if patch["id"] in seen_events:
                raise EnrichmentError(f"event {patch['id']} appears in more than one selected batch")
            seen_events.add(patch["id"])
        actionable.append((path, batch, destination))

    merged = deepcopy(canonical)
    merged_index = {event["id"]: event for event in merged["events"]}
    for path, batch, _ in actionable:
        try:
            display_path = str(path.relative_to(root))
        except ValueError:
            display_path = str(path)
        batch_report = {"batch_id": batch["batch_id"], "path": display_path}
        report["batches"].append(batch_report)
        for patch in batch["patches"]:
            changes = apply_patch(merged_index[patch["id"]], patch)
            report["events"].append({"id": patch["id"], "changes": changes})

    validate_canonical(merged)
    if dry_run or not actionable:
        return report

    processed_dir.mkdir(parents=True, exist_ok=True)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=canonical_path.parent, delete=False) as handle:
        handle.write(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        temporary = Path(handle.name)
    original_bytes = canonical_path.read_bytes()
    archived: list[tuple[Path, Path]] = []
    try:
        os.replace(temporary, canonical_path)
        for path, _, destination in actionable:
            os.replace(path, destination)
            archived.append((path, destination))
    except OSError as error:
        for source, destination in reversed(archived):
            if destination.exists() and not source.exists():
                os.replace(destination, source)
        with NamedTemporaryFile("wb", dir=canonical_path.parent, delete=False) as handle:
            handle.write(original_bytes)
            rollback = Path(handle.name)
        os.replace(rollback, canonical_path)
        raise EnrichmentError(f"filesystem failure while committing enrichment batch; changes rolled back: {error}") from error
    finally:
        if temporary.exists():
            temporary.unlink()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        paths = batch_paths(args.batch, args.all)
        report = merge(paths, args.dry_run)
    except EnrichmentError as error:
        parser.exit(2, f"merge enrichment patches: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
