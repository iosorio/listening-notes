#!/usr/bin/env python3
"""Safely merge curated radar handoff batches into the canonical event dataset."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
CURATED = ROOT / "radar/inbox/curated"
PROCESSED = ROOT / "radar/inbox/processed"
VALIDATOR = ROOT / "scripts/validate_events.py"
EVIDENCE_TYPES = {"user_confirmed", "personal_photo", "ticket_purchase", "logistics_email", "calendar_or_planning", "third_party_ticket", "archival_reference", "post_event_reference", "unknown"}


def fail(message: str) -> None:
    raise ValueError(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path}: {error}")
    if not isinstance(value, dict):
        fail(f"{path}: root must be an object")
    return value


def validate_batch(batch: dict, path: Path) -> list[dict]:
    if batch.get("batch_version") != 1 or batch.get("kind") != "curated_event_candidates":
        fail(f"{path}: unsupported batch envelope")
    if not isinstance(batch.get("batch_id"), str) or not isinstance(batch.get("events"), list):
        fail(f"{path}: batch_id and events are required")
    ids: set[str] = set()
    for index, event in enumerate(batch["events"]):
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            fail(f"{path}: events[{index}] requires an id")
        if event["id"] in ids:
            fail(f"{path}: duplicate candidate id {event['id']}")
        ids.add(event["id"])
        if not isinstance(event.get("artist"), str) or not isinstance(event.get("dates"), dict):
            fail(f"{path}: {event['id']} requires artist and dates")
        attendance = event.get("attendance", {})
        evidence = attendance.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, dict) or item.get("type") not in EVIDENCE_TYPES for item in evidence):
            fail(f"{path}: {event['id']} has unsupported attendance evidence")
    return batch["events"]


def complete_metadata(candidate: dict) -> tuple[bool, str | None]:
    venue = candidate.get("venue", {})
    if not candidate.get("dates", {}).get("start"):
        return False, "missing dates.start"
    if not all(isinstance(venue.get(key), str) and venue[key] for key in ("id", "name", "city", "state", "country")):
        return False, "missing complete venue identity"
    return True, None


def normalize(candidate: dict) -> tuple[dict, list[str]]:
    event = deepcopy(candidate)
    changes: list[str] = []
    defaults = {
        "subtitle": None, "showtimes": [], "priority": None,
        "category": "Historical archive", "genres": [], "musical_axes": [],
        "lineup": [], "factual_description": None, "recommended_listening": [],
    }
    for field, value in defaults.items():
        if field not in event:
            event[field] = value
            changes.append(f"{field}={value!r}")
    event.setdefault("editorial", {"en": {}, "es": {}})
    for language in ("en", "es"):
        event["editorial"].setdefault(language, {})
        for field in ("why_it_matters", "trip_verdict", "listen_before"):
            if field not in event["editorial"][language]:
                event["editorial"][language][field] = None
                changes.append(f"editorial.{language}.{field}=null")
    event.setdefault("links", {"official_event": None, "official_tickets": None})
    event["links"].setdefault("official_event", None)
    event["links"].setdefault("official_tickets", None)
    event.setdefault("tickets", {})
    event["tickets"].setdefault("currency", "USD")
    for market, url_field in (("official", "source_url"), ("resale", "url")):
        event["tickets"].setdefault(market, {})
        for field in ("minimum", "maximum", url_field, "checked_on"):
            event["tickets"][market].setdefault(field, None)
    event.setdefault("sources", [])
    event.setdefault("provenance", {"status": "curated-inbox", "note": "Merged from a reviewed curated inbox batch."})
    attendance = event.setdefault("attendance", {})
    attendance.setdefault("status", "attended" if event.get("status") == "attended" else None)
    attendance.setdefault("evidence", [])
    attendance.setdefault("notes", None)
    attendance.setdefault("setlist", None)
    attendance.setdefault("photo_paths", [])
    return event, changes


def validate_canonical(data: dict) -> None:
    with TemporaryDirectory() as directory:
        target = Path(directory) / "events.json"
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        result = subprocess.run([sys.executable, str(VALIDATOR), str(target)], text=True, capture_output=True)
        if result.returncode:
            fail(result.stderr.strip() or result.stdout.strip())


def batch_paths(args: argparse.Namespace) -> list[Path]:
    if args.batch:
        path = Path(args.batch).resolve()
        if path.parent != CURATED.resolve():
            fail("batch must be an unprocessed file directly inside radar/inbox/curated")
        return [path]
    paths = sorted(CURATED.glob("*.json"))
    if not paths:
        fail("no unprocessed curated batches found")
    return paths


def merge(paths: list[Path], dry_run: bool) -> dict:
    canonical = read_json(CANONICAL)
    if canonical.get("schema_version") != 3:
        fail("canonical events.json must use schema_version 3")
    validate_canonical(canonical)
    existing = {event["id"] for event in canonical["events"]}
    report = {"dry_run": dry_run, "added": [], "conflicts": [], "blocked": [], "normalization": [], "processed": []}
    additions: list[dict] = []
    payloads: dict[Path, dict] = {}
    added_by_path: dict[Path, list[str]] = {}
    blocked_by_path: dict[Path, list[dict]] = {}
    seen = set(existing)
    for path in paths:
        batch = read_json(path)
        payloads[path] = batch
        added_by_path[path] = []
        blocked_by_path[path] = []
        for candidate in validate_batch(batch, path):
            event_id = candidate["id"]
            if event_id in seen:
                report["conflicts"].append({"id": event_id, "batch": batch["batch_id"], "reason": "canonical or earlier batch already has this id"})
                continue
            complete, reason = complete_metadata(candidate)
            if not complete:
                report["blocked"].append({"id": event_id, "batch": batch["batch_id"], "reason": reason})
                blocked_by_path[path].append(candidate)
                continue
            normalized, changes = normalize(candidate)
            additions.append(normalized)
            seen.add(event_id)
            report["added"].append(event_id)
            added_by_path[path].append(event_id)
            if changes:
                report["normalization"].append({"id": event_id, "changes": changes})
        if added_by_path[path]:
            report["processed"].append({"batch": batch["batch_id"], "path": str(path.relative_to(ROOT))})
    if report["conflicts"]:
        return report
    merged = {"schema_version": 3, "events": sorted(canonical["events"] + additions, key=lambda event: (event["dates"]["start"], event["id"]))}
    validate_canonical(merged)
    if not dry_run:
        CANONICAL.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        PROCESSED.mkdir(parents=True, exist_ok=True)
        for path in paths:
            if not added_by_path[path]:
                continue
            destination = PROCESSED / path.name
            if destination.exists():
                fail(f"processed destination already exists: {destination}")
            if blocked_by_path[path]:
                residual = deepcopy(payloads[path])
                residual["batch_id"] = f"{residual['batch_id']}-deferred"
                residual["events"] = blocked_by_path[path]
                residual["notes"] = f"{residual.get('notes', '')} Deferred records remain unprocessed until canonical metadata is complete.".strip()
                deferred = CURATED / f"{path.stem}-deferred.json"
                if deferred.exists():
                    fail(f"deferred destination already exists: {deferred}")
                deferred.write_text(json.dumps(residual, ensure_ascii=False, indent=2) + "\n")
            shutil.move(path, destination)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", help="one file in radar/inbox/curated")
    parser.add_argument("--all", action="store_true", help="merge every unprocessed curated batch")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = parser.parse_args()
    if bool(args.batch) == bool(args.all):
        parser.error("choose exactly one of --batch or --all")
    try:
        report = merge(batch_paths(args), args.dry_run)
    except ValueError as error:
        parser.exit(2, f"merge inbox: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["conflicts"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
