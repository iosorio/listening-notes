#!/usr/bin/env python3
"""Safely merge curated radar handoff batches into the canonical event dataset."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
CURATED = ROOT / "radar/inbox/curated"
PROCESSED = ROOT / "radar/inbox/processed"
VALIDATOR = ROOT / "scripts/validate_events.py"
EVIDENCE_TYPES = {"user_confirmed", "personal_photo", "ticket_purchase", "logistics_email", "calendar_or_planning", "third_party_ticket", "archival_reference", "post_event_reference", "unknown"}
TOP_PRIORITIES = {"S": "protect_the_night", "S+": "alter_plans"}


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


def validate_priority_review(event: dict, path: Path) -> None:
    """Require an explicit editorial decision for the two scarcity tiers."""
    priority = event.get("priority")
    if priority not in TOP_PRIORITIES:
        return
    review = event.get("priority_review")
    event_id = event["id"]
    if not isinstance(review, dict):
        fail(f"{path}: {event_id} at {priority} requires a priority_review")
    if review.get("decision") != TOP_PRIORITIES[priority]:
        fail(f"{path}: {event_id} at {priority} requires priority_review.decision={TOP_PRIORITIES[priority]}")
    if not all(isinstance(review.get(field), str) and review[field].strip() for field in ("reviewed_by", "reviewed_on", "rationale")):
        fail(f"{path}: {event_id} priority_review requires reviewed_by, reviewed_on, and rationale")
    try:
        date.fromisoformat(review["reviewed_on"])
    except ValueError:
        fail(f"{path}: {event_id} priority_review.reviewed_on must be an ISO date")


def validate_batch(batch: dict, path: Path, curated_dir: Path = CURATED) -> list[dict]:
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
        validate_priority_review(event, path)
        if path.parent.resolve() == curated_dir.resolve() and event.get("status") in {"considering", "going"} and "enrichment" not in event:
            fail(f"{path}: {event['id']} is upcoming and requires an enrichment declaration")
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


def normalized_artist_identity(event: dict) -> frozenset[str]:
    """Return a deliberately conservative artist/project token identity."""
    text = " ".join(str(event.get(field) or "") for field in ("artist", "subtitle"))
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return frozenset(token for token in re.findall(r"[a-z0-9]+", folded) if len(token) > 1)


def dates_overlap(left: dict, right: dict) -> bool:
    left_start = left["dates"]["start"]
    left_end = left["dates"].get("end") or left_start
    right_start = right["dates"]["start"]
    right_end = right["dates"].get("end") or right_start
    return left_start <= right_end and right_start <= left_end


def semantic_duplicate(candidate: dict, existing: dict) -> bool:
    if candidate["venue"]["id"] != existing["venue"]["id"] or not dates_overlap(candidate, existing):
        return False
    candidate_identity = normalized_artist_identity(candidate)
    existing_identity = normalized_artist_identity(existing)
    # Subset matching catches expanded billings such as "BEAT" and "BEAT:
    # Belew/Vai/Levin/Bozzio" without guessing. It is still conservative
    # because it also requires the same stable venue and overlapping dates.
    return bool(candidate_identity and existing_identity) and (
        candidate_identity <= existing_identity or existing_identity <= candidate_identity
    )


def normalize(candidate: dict) -> tuple[dict, list[str]]:
    event = deepcopy(candidate)
    changes: list[str] = []
    priority_review = event.pop("priority_review", None)
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
    if priority_review is not None:
        event["provenance"]["priority_review"] = priority_review
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
    return paths


def merge(
    paths: list[Path],
    dry_run: bool,
    canonical_path: Path = CANONICAL,
    curated_dir: Path = CURATED,
    processed_dir: Path = PROCESSED,
) -> dict:
    canonical = read_json(canonical_path)
    if canonical.get("schema_version") != 3:
        fail("canonical events.json must use schema_version 3")
    validate_canonical(canonical)
    existing = {event["id"] for event in canonical["events"]}
    def priority_counts(events: list[dict]) -> dict[str, int]:
        return {priority: sum(event.get("priority") == priority for event in events) for priority in ("A", "A+", "S", "S+")}

    report = {"dry_run": dry_run, "added": [], "conflicts": [], "semantic_conflicts": [], "blocked": [], "normalization": [], "processed": []}
    additions: list[dict] = []
    payloads: dict[Path, dict] = {}
    added_by_path: dict[Path, list[str]] = {}
    blocked_by_path: dict[Path, list[dict]] = {}
    seen = set(existing)
    candidates_to_compare = list(canonical["events"])
    for path in paths:
        batch = read_json(path)
        payloads[path] = batch
        added_by_path[path] = []
        blocked_by_path[path] = []
        for candidate in validate_batch(batch, path, curated_dir):
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
            duplicate = next((event for event in candidates_to_compare if semantic_duplicate(normalized, event)), None)
            if duplicate:
                report["semantic_conflicts"].append({
                    "id": event_id,
                    "conflict_with": duplicate["id"],
                    "batch": batch["batch_id"],
                    "reason": "same venue, overlapping dates, and normalized artist/project identity",
                })
                continue
            additions.append(normalized)
            candidates_to_compare.append(normalized)
            seen.add(event_id)
            report["added"].append(event_id)
            added_by_path[path].append(event_id)
            if changes:
                report["normalization"].append({"id": event_id, "changes": changes})
        if added_by_path[path]:
            try:
                display_path = str(path.relative_to(ROOT))
            except ValueError:
                display_path = str(path)
            report["processed"].append({"batch": batch["batch_id"], "path": display_path})
    if report["conflicts"] or report["semantic_conflicts"]:
        return report
    merged = {"schema_version": 3, "events": sorted(canonical["events"] + additions, key=lambda event: (event["dates"]["start"], event["id"]))}
    validate_canonical(merged)
    report["priority_distribution"] = {
        "before": priority_counts(canonical["events"]),
        "added": priority_counts(additions),
        "after": priority_counts(merged["events"]),
    }
    if not dry_run:
        canonical_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        processed_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            if not added_by_path[path]:
                continue
            destination = processed_dir / path.name
            if destination.exists():
                fail(f"processed destination already exists: {destination}")
            if blocked_by_path[path]:
                residual = deepcopy(payloads[path])
                residual["batch_id"] = f"{residual['batch_id']}-deferred"
                residual["events"] = blocked_by_path[path]
                residual["notes"] = f"{residual.get('notes', '')} Deferred records remain unprocessed until canonical metadata is complete.".strip()
                deferred = curated_dir / f"{path.stem}-deferred.json"
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
    # A dry run is deliberately reviewable: semantic conflicts are reported
    # without making the workflow fail, while an actual merge still refuses
    # to proceed. Exact ID conflicts retain their established hard failure.
    if report["conflicts"] or (report["semantic_conflicts"] and not args.dry_run):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
