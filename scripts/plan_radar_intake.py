#!/usr/bin/env python3
"""Produce a deterministic, read-only decision manifest for RADAR intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .merge_inbox import dates_overlap, normalized_artist_identity, semantic_duplicate
    from .venue_identity import VenueIdentityError, canonicalize_venue, load_registry
except ImportError:  # Direct script execution.
    from merge_inbox import dates_overlap, normalized_artist_identity, semantic_duplicate
    from venue_identity import VenueIdentityError, canonicalize_venue, load_registry


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
ACTIVE = ROOT / "radar/inbox/curated"
WIP_PATH_PREFIX = "radar/inbox/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def link_url(event: dict, field: str) -> str | None:
    """Return a literal candidate URL; planning never canonicalizes URLs."""
    value = event.get("links", {}).get(field)
    return value if isinstance(value, str) and value else None


def exact_official_event_page(url: str | None) -> bool:
    """Reject known venue/provider placeholders and generic listing endpoints.

    Literal equality is meaningful only for a page that purports to identify a
    performance.  A vendor's ``coming-soon`` or calendar page may legitimately
    be shared by many functions and is never duplicate evidence.
    """
    if not url:
        return False
    parts = [part.casefold() for part in urlsplit(url).path.split("/") if part]
    generic = {"calendar", "schedule", "upcoming", "coming-soon", "events", "artists", "listing"}
    # A year suffix does not turn a festival lineup into a performance page.
    generic_listing = bool(parts) and re.fullmatch(r"(?:lineup|schedule|calendar)(?:[-_]\d{4})?", parts[-1])
    return bool(parts) and parts[-1] not in generic and not generic_listing


def exact_ticket_page(url: str | None) -> bool:
    """A generic ticket-provider listing is not an event-level identity."""
    if not url:
        return False
    parsed = urlsplit(url)
    parts = [part.casefold() for part in parsed.path.split("/") if part]
    generic = {"calendar", "schedule", "upcoming", "coming-soon", "events", "artists", "listing", "provider", "tickets"}
    # Some authorized providers use a root destination only with an exact item
    # query.  A bare provider home/listing is never sufficient.
    return (bool(parts) and parts[-1] not in generic) or (not parts and bool(parsed.query))


def exact_ticket_identity(candidate: dict, existing: dict) -> bool:
    """The narrow ticket-page identity permitted for automatic archival."""
    try:
        if candidate["venue"]["id"] != existing["venue"]["id"] or not dates_overlap(candidate, existing):
            return False
    except (KeyError, TypeError):
        return False
    candidate_identity = normalized_artist_identity(candidate)
    existing_identity = normalized_artist_identity(existing)
    if not candidate_identity or candidate_identity != existing_identity:
        return False
    candidate_times = candidate.get("showtimes")
    existing_times = existing.get("showtimes")
    return not (
        isinstance(candidate_times, list)
        and isinstance(existing_times, list)
        and candidate_times
        and existing_times
        and set(candidate_times).isdisjoint(existing_times)
    )


def safe_semantic_duplicate(candidate: dict, existing: dict) -> bool:
    try:
        return semantic_duplicate(candidate, existing)
    except (KeyError, TypeError):
        return False


def read_batch(data: bytes, label: str) -> dict:
    try:
        batch = json.loads(data)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label}: invalid JSON: {error}") from error
    if batch.get("kind") != "curated_event_candidates" or not isinstance(batch.get("events"), list):
        raise ValueError(f"{label}: not a curated event-candidate batch")
    return batch


def wip_files(ref: str) -> list[tuple[str, bytes]]:
    """Read the stash/tree as evidence, without checking it out or changing it."""
    evidence = []
    seen: set[tuple[str, str]] = set()
    # A `git stash --include-untracked` stores untracked evidence in its third
    # parent. Inspect both trees instead of resurrecting either one.
    tracked = subprocess.run(["git", "diff", "--name-only", f"{ref}^1", ref], cwd=ROOT, text=True, capture_output=True, check=True)
    trees = [(ref, tracked.stdout.splitlines())]
    untracked = subprocess.run(["git", "ls-tree", "-r", "--name-only", f"{ref}^3"], cwd=ROOT, text=True, capture_output=True)
    if untracked.returncode == 0:
        trees.append((f"{ref}^3", untracked.stdout.splitlines()))
    for tree, tree_paths in trees:
        result = subprocess.run(["git", "ls-tree", "-r", "--name-only", tree], cwd=ROOT, text=True, capture_output=True)
        if result.returncode:
            continue
        present = set(result.stdout.splitlines())
        paths = [path for path in tree_paths if path in present and path.startswith(WIP_PATH_PREFIX) and path.endswith(".json")]
        for path in paths:
            content = subprocess.run(["git", "show", f"{tree}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
            digest = sha256(content)
            if (path, digest) in seen:
                continue
            seen.add((path, digest))
            try:
                batch = json.loads(content)
            except json.JSONDecodeError:
                continue
            if batch.get("kind") == "curated_event_candidates":
                evidence.append((f"wip:{tree}:{path}", content))
    return evidence


def event_diff(candidate: dict, existing: dict | None) -> list[dict]:
    if existing is None:
        return [{"field": "event", "before": None, "after": candidate.get("id")}]
    fields = ("artist", "subtitle", "dates", "showtimes", "venue", "links", "lineup")
    return [
        {"field": field, "before": existing.get(field), "after": candidate.get(field)}
        for field in fields if existing.get(field) != candidate.get(field)
    ]


def decide(candidate: dict, canonical: list[dict], registry: dict) -> dict:
    raw = deepcopy(candidate)
    try:
        candidate["venue"], venue_changes = canonicalize_venue(candidate.get("venue", {}), registry)
    except VenueIdentityError as error:
        return {"action": "review", "approval": "requires_review", "evidence": [{"kind": "invalid_venue_identity", "detail": str(error)}], "diff": []}
    same_id = next((event for event in canonical if event.get("id") == candidate.get("id")), None)
    if same_id:
        return {
            "action": "archive_duplicate", "approval": "permitted", "canonical_event_id": same_id["id"],
            "evidence": [{"kind": "same_id", "value": candidate["id"]}], "diff": event_diff(candidate, same_id), "normalization": venue_changes,
        }
    for existing in canonical:
        shared_event = link_url(candidate, "official_event")
        if shared_event and exact_official_event_page(shared_event) and shared_event == link_url(existing, "official_event"):
            if candidate.get("dates") != existing.get("dates") or (
                candidate.get("showtimes") and existing.get("showtimes")
                and set(candidate["showtimes"]).isdisjoint(existing["showtimes"])
            ):
                return {
                    "action": "review", "approval": "requires_review", "canonical_event_id": existing["id"],
                    "evidence": [{"kind": "shared_event_page_distinct_functions", "url": shared_event}],
                    "diff": event_diff(candidate, existing), "normalization": venue_changes,
                }
            return {
                "action": "archive_duplicate", "approval": "permitted", "canonical_event_id": existing["id"],
                "evidence": [{"kind": "same_official_event_url", "url": shared_event}], "diff": event_diff(candidate, existing), "normalization": venue_changes,
            }
        shared_ticket = link_url(candidate, "official_tickets")
        if shared_ticket and exact_ticket_page(shared_ticket) and shared_ticket == link_url(existing, "official_tickets") and exact_ticket_identity(candidate, existing):
            return {
                "action": "archive_duplicate", "approval": "permitted", "canonical_event_id": existing["id"],
                "evidence": [{"kind": "same_official_ticket_url_and_identity", "url": shared_ticket}], "diff": event_diff(candidate, existing), "normalization": venue_changes,
            }
    for existing in canonical:
        if safe_semantic_duplicate(candidate, existing):
            distinct = bool(candidate.get("showtimes") and existing.get("showtimes") and set(candidate["showtimes"]).isdisjoint(existing["showtimes"]))
            return {
                "action": "review", "approval": "requires_review", "canonical_event_id": existing["id"],
                "evidence": [{"kind": "same_artist_venue_date", "artist_tokens": sorted(normalized_artist_identity(candidate)), "dates_overlap": dates_overlap(candidate, existing)}, {"kind": "distinct_showtimes", "value": distinct}],
                "diff": event_diff(candidate, existing), "normalization": venue_changes,
            }
    return {"action": "create", "approval": "requires_review", "evidence": [{"kind": "no_canonical_match"}], "diff": event_diff(candidate, None), "normalization": venue_changes}


def plan(active_dir: Path, wip_ref: str | None) -> dict:
    registry = load_registry()
    canonical_data = json.loads(CANONICAL.read_text())
    canonical = canonical_data["events"]
    inputs: list[tuple[str, bytes]] = [(str(path.relative_to(ROOT)), path.read_bytes()) for path in sorted(active_dir.glob("*.json"))]
    if wip_ref:
        inputs.extend(wip_files(wip_ref))
    decisions = []
    for label, data in inputs:
        try:
            batch = read_batch(data, label)
        except ValueError as error:
            decisions.append({"path": label, "sha256": sha256(data), "action": "review", "approval": "requires_review", "evidence": [{"kind": "invalid_batch", "detail": str(error)}], "diff": []})
            continue
        for index, event in enumerate(batch["events"]):
            if not isinstance(event, dict):
                decisions.append({"path": label, "sha256": sha256(data), "event_index": index, "action": "review", "approval": "requires_review", "evidence": [{"kind": "invalid_event"}], "diff": []})
                continue
            detail = decide(deepcopy(event), canonical, registry)
            decisions.append({"path": label, "sha256": sha256(data), "batch_id": batch.get("batch_id"), "event_index": index, "candidate_event_id": event.get("id"), **detail})
    counts = {action: sum(item["action"] == action for item in decisions) for action in ("create", "merge", "replace", "archive_duplicate", "review")}
    return {
        "schema_version": 1,
        "policy": "Read-only pre-ingest plan. permitted actions are deterministic strong duplicate matches; all other actions require documented official evidence before materialization.",
        "canonical": {"path": "radar/events.json", "sha256": sha256(CANONICAL.read_bytes())},
        "venue_registry": {"path": "radar/venue_identities.json", "sha256": sha256((ROOT / "radar/venue_identities.json").read_bytes())},
        "wip_ref": wip_ref,
        "decisions": decisions,
        "summary": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-dir", type=Path, default=ACTIVE)
    parser.add_argument("--wip-ref", default=None, help="Git tree/stash to inspect only; never checked out")
    args = parser.parse_args()
    print(json.dumps(plan(args.active_dir.resolve(), args.wip_ref), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
