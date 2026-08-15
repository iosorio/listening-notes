#!/usr/bin/env python3
"""Shared deterministic contracts for RADAR enrichment research and patches."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
RESEARCH = ROOT / "radar/inbox/research"
CURATED_ENRICHMENT = ROOT / "radar/inbox/curated/enrichment"
PROCESSED_ENRICHMENT = ROOT / "radar/inbox/processed/enrichment"

RESEARCH_KIND = "research_event_enrichment_patches"
CURATED_KIND = "curated_event_enrichment_patches"
PATCH_FIELDS = {
    "id",
    "links",
    "recommended_listening",
    "enrichment",
    "sources",
    "provenance",
    "replacement_reason",
}
LINK_FIELDS = {"official_event", "official_tickets"}
ENRICHMENT_FIELDS = {"official_event", "official_tickets", "apple_music"}
ENRICHMENT_STATUSES = {"complete", "pending", "unavailable"}
RECOMMENDATION_KINDS = {"album", "track", "playlist"}
PRIVATE_TEXT = re.compile(r"(?:https?://mail\.google\.com|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)", re.I)
SOCIAL_HOSTS = {
    "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com",
}


class EnrichmentError(ValueError):
    """A deterministic enrichment-contract failure."""


def fail(message: str) -> None:
    raise EnrichmentError(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path}: {error}")
    if not isinstance(value, dict):
        fail(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_iso_date(value: object, field: str) -> None:
    if not isinstance(value, str):
        fail(f"{field} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError:
        fail(f"{field} must be an ISO date")


def reject_private_text(value: object, field: str = "batch") -> None:
    if isinstance(value, str) and PRIVATE_TEXT.search(value):
        fail(f"{field} contains a private email address or Gmail URL")
    if isinstance(value, dict):
        for key, child in value.items():
            reject_private_text(child, f"{field}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_private_text(child, f"{field}[{index}]")


def normalized_url(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", parsed.query, ""))


def valid_source_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    host = parsed.netloc.lower().split(":", 1)[0]
    path = parsed.path.lower()
    if parsed.scheme != "https" or not host or path in {"", "/"}:
        return False
    if host in {"google.com", "www.google.com"} or "/search" in path:
        return False
    return True


def valid_official_url(value: object) -> bool:
    if not valid_source_url(value):
        return False
    host = urlparse(value).netloc.lower().split(":", 1)[0]
    return not any(host == blocked or host.endswith(f".{blocked}") for blocked in SOCIAL_HOSTS)


def valid_apple_music_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "music.apple.com"
        and "/search" not in parsed.path.lower()
        and re.search(r"/(album|song|playlist)/", parsed.path) is not None
    )


def validate_source(source: object, field: str) -> None:
    if not isinstance(source, dict):
        fail(f"{field} must be an object")
    unknown = set(source) - {"url", "publisher", "checked_on", "note"}
    if unknown:
        fail(f"{field} contains unsupported fields: {', '.join(sorted(unknown))}")
    if not valid_source_url(source.get("url")):
        fail(f"{field}.url must be an exact public HTTPS source URL")
    if not isinstance(source.get("publisher"), str) or not source["publisher"].strip():
        fail(f"{field}.publisher is required")
    validate_iso_date(source.get("checked_on"), f"{field}.checked_on")
    if source.get("note") is not None and not isinstance(source["note"], str):
        fail(f"{field}.note must be a string when present")


def validate_recommendation(recommendation: object, field: str) -> None:
    if not isinstance(recommendation, dict):
        fail(f"{field} must be an object")
    unknown = set(recommendation) - {"artist", "title", "kind", "apple_music_url"}
    if unknown:
        fail(f"{field} contains unsupported fields: {', '.join(sorted(unknown))}")
    for key in ("artist", "title"):
        if not isinstance(recommendation.get(key), str) or not recommendation[key].strip():
            fail(f"{field}.{key} is required")
    if recommendation.get("kind") not in RECOMMENDATION_KINDS:
        fail(f"{field}.kind must be album, track, or playlist")
    apple_url = recommendation.get("apple_music_url")
    if apple_url is not None and not valid_apple_music_url(apple_url):
        fail(f"{field}.apple_music_url must be an exact Apple Music album, song, or playlist URL")


def validate_provenance(provenance: object, field: str) -> None:
    if not isinstance(provenance, dict):
        fail(f"{field} must be an object")
    unknown = set(provenance) - {"status", "note", "recorded_on"}
    if unknown:
        fail(f"{field} contains unsupported fields: {', '.join(sorted(unknown))}")
    for key in ("status", "note"):
        if not isinstance(provenance.get(key), str) or not provenance[key].strip():
            fail(f"{field}.{key} is required")
    validate_iso_date(provenance.get("recorded_on"), f"{field}.recorded_on")


def validate_patch_shape(patch: object, field: str) -> None:
    if not isinstance(patch, dict):
        fail(f"{field} must be an object")
    unknown = set(patch) - PATCH_FIELDS
    if unknown:
        fail(f"{field} attempts forbidden updates: {', '.join(sorted(unknown))}")
    if not isinstance(patch.get("id"), str) or not patch["id"].strip():
        fail(f"{field}.id is required")
    if not (set(patch) - {"id", "replacement_reason"}):
        fail(f"{field} contains no enrichment changes")
    if "enrichment" not in patch:
        fail(f"{field}.enrichment is required")
    links = patch.get("links")
    if links is not None:
        if not isinstance(links, dict) or set(links) - LINK_FIELDS:
            fail(f"{field}.links may contain only official_event and official_tickets")
        for key, value in links.items():
            if not valid_official_url(value):
                fail(f"{field}.links.{key} must be an exact public HTTPS event URL")
    recommendations = patch.get("recommended_listening")
    if recommendations is not None:
        if not isinstance(recommendations, list):
            fail(f"{field}.recommended_listening must be an array")
        for index, recommendation in enumerate(recommendations):
            validate_recommendation(recommendation, f"{field}.recommended_listening[{index}]")
    sources = patch.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            fail(f"{field}.sources must be an array")
        for index, source in enumerate(sources):
            validate_source(source, f"{field}.sources[{index}]")
    if "provenance" in patch:
        validate_provenance(patch["provenance"], f"{field}.provenance")
    reason = patch.get("replacement_reason")
    if reason is not None:
        if not isinstance(reason, str) or not reason.strip():
            fail(f"{field}.replacement_reason must be a non-empty string")
        if not sources:
            fail(f"{field}.replacement_reason requires corresponding source evidence")
    enrichment = patch.get("enrichment")
    if not isinstance(enrichment, dict):
        fail(f"{field}.enrichment must be an object")
    unknown = set(enrichment) - {"status", "missing", "note"}
    if unknown or enrichment.get("status") not in ENRICHMENT_STATUSES:
        fail(f"{field}.enrichment has an unsupported shape or status")
    missing = enrichment.get("missing")
    if not isinstance(missing, list) or set(missing) - ENRICHMENT_FIELDS or len(missing) != len(set(missing)):
        fail(f"{field}.enrichment.missing must be a unique list of known fields")
    if enrichment["status"] == "complete":
        if missing or enrichment.get("note") not in {None, ""}:
            fail(f"{field}.enrichment complete requires missing=[] and no note")
    elif not missing or not isinstance(enrichment.get("note"), str) or not enrichment["note"].strip():
        fail(f"{field}.enrichment pending/unavailable requires missing fields and a note")
    reject_private_text(patch, field)


def validate_enrichment_result(event: dict, field: str) -> None:
    enrichment = event.get("enrichment")
    if not isinstance(enrichment, dict):
        fail(f"{field}.enrichment is required after applying the patch")
    links = event.get("links", {})
    available = {
        "official_event": bool(links.get("official_event")),
        "official_tickets": bool(links.get("official_tickets")),
        "apple_music": any(
            isinstance(item, dict) and valid_apple_music_url(item.get("apple_music_url"))
            for item in event.get("recommended_listening", [])
        ),
    }
    expected_missing = {name for name, present in available.items() if not present}
    declared_missing = set(enrichment.get("missing", []))
    if enrichment.get("status") == "complete":
        if expected_missing or declared_missing:
            fail(f"{field} claims complete enrichment but required fields are missing")
    elif declared_missing != expected_missing:
        fail(f"{field}.enrichment.missing must exactly describe unresolved enrichment: {sorted(expected_missing)}")


def recommendation_key(item: dict) -> tuple[str, str, str]:
    return (
        str(item.get("artist", "")).strip().casefold(),
        str(item.get("title", "")).strip().casefold(),
        str(item.get("kind", "")).strip().casefold(),
    )


def record_key(item: dict) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_key(item: dict) -> str:
    normalized = deepcopy(item)
    if isinstance(normalized.get("url"), str):
        normalized["url"] = normalized_url(normalized["url"])
    return record_key(normalized)


def apply_patch(event: dict, patch: dict) -> list[str]:
    """Apply one validated patch to a copy of an event and return changed paths."""
    changed: list[str] = []
    reason = patch.get("replacement_reason")
    evidence = patch.get("sources", [])
    evidence_urls = {
        normalized_url(source["url"])
        for source in evidence
        if isinstance(source, dict) and isinstance(source.get("url"), str)
    }

    def replacement_is_supported(new_url: str) -> bool:
        return bool(reason and normalized_url(new_url) in evidence_urls)

    if "links" in patch:
        links = event.setdefault("links", {})
        for key, new_value in patch["links"].items():
            old_value = links.get(key)
            if old_value == new_value:
                continue
            if old_value is not None and not replacement_is_supported(new_value):
                fail(f"{patch['id']}.links.{key} already has a different verified URL; replacement_reason and a source for the new URL are required")
            links[key] = new_value
            changed.append(f"links.{key}")

    if "recommended_listening" in patch:
        recommendations = event.setdefault("recommended_listening", [])
        by_apple = {
            normalized_url(item["apple_music_url"]): index
            for index, item in enumerate(recommendations)
            if isinstance(item, dict) and valid_apple_music_url(item.get("apple_music_url"))
        }
        by_editorial = {
            recommendation_key(item): index
            for index, item in enumerate(recommendations)
            if isinstance(item, dict)
        }
        for new_item in patch["recommended_listening"]:
            new_url = new_item.get("apple_music_url")
            if new_url and normalized_url(new_url) in by_apple:
                continue
            key = recommendation_key(new_item)
            if key in by_editorial:
                index = by_editorial[key]
                old_item = recommendations[index]
                old_url = old_item.get("apple_music_url")
                if old_url == new_url or new_url is None:
                    continue
                if old_url is not None and not replacement_is_supported(new_url):
                    fail(f"{patch['id']}.recommended_listening has a different verified Apple Music URL; replacement_reason and a source for the new URL are required")
                recommendations[index] = deepcopy(new_item)
                changed.append(f"recommended_listening[{index}]")
                by_apple[normalized_url(new_url)] = index
            else:
                recommendations.append(deepcopy(new_item))
                index = len(recommendations) - 1
                by_editorial[key] = index
                if new_url:
                    by_apple[normalized_url(new_url)] = index
                changed.append(f"recommended_listening[{index}]")

    if "sources" in patch:
        sources = event.setdefault("sources", [])
        existing = {source_key(item) for item in sources if isinstance(item, dict)}
        for source in patch["sources"]:
            key = source_key(source)
            if key not in existing:
                sources.append(deepcopy(source))
                existing.add(key)
                changed.append(f"sources[{len(sources) - 1}]")

    if "provenance" in patch:
        provenance = event.setdefault("provenance", {})
        if not isinstance(provenance, dict):
            fail(f"{patch['id']}.provenance is not compatible with enrichment history")
        history = provenance.setdefault("enrichment_history", [])
        if not isinstance(history, list):
            fail(f"{patch['id']}.provenance.enrichment_history must be an array")
        key = record_key(patch["provenance"])
        if key not in {record_key(item) for item in history if isinstance(item, dict)}:
            history.append(deepcopy(patch["provenance"]))
            changed.append(f"provenance.enrichment_history[{len(history) - 1}]")

    if event.get("enrichment") != patch["enrichment"]:
        event["enrichment"] = deepcopy(patch["enrichment"])
        changed.append("enrichment")
    validate_enrichment_result(event, patch["id"])
    return changed


def validate_research_batch(batch: dict, canonical: dict, path: Path) -> dict:
    allowed = {"batch_version", "kind", "batch_id", "created_on", "notes", "events"}
    if set(batch) - allowed or batch.get("batch_version") != 1 or batch.get("kind") != RESEARCH_KIND:
        fail(f"{path}: unsupported research batch envelope")
    if not isinstance(batch.get("batch_id"), str) or not batch["batch_id"].strip():
        fail(f"{path}: batch_id is required")
    if "created_on" in batch:
        validate_iso_date(batch["created_on"], f"{path}.created_on")
    if not isinstance(batch.get("events"), list) or not batch["events"]:
        fail(f"{path}: events must be a non-empty array")
    reject_private_text(batch, str(path))
    if canonical.get("schema_version") != 3 or not isinstance(canonical.get("events"), list):
        fail("canonical events.json must use schema_version 3")
    index = {event["id"]: deepcopy(event) for event in canonical["events"]}
    seen: set[str] = set()
    report = {"batch_id": batch["batch_id"], "path": str(path), "events": []}
    for number, patch in enumerate(batch["events"]):
        validate_patch_shape(patch, f"{path}.events[{number}]")
        event_id = patch["id"]
        if event_id in seen:
            fail(f"{path}: duplicate event id {event_id}")
        seen.add(event_id)
        if event_id not in index:
            fail(f"{path}: unknown canonical event id {event_id}")
        changes = apply_patch(index[event_id], patch)
        report["events"].append({"id": event_id, "changes": changes, "result": index[event_id]["enrichment"]})
    return report


def research_path_from_review(review: dict, root: Path = ROOT, research_dir: Path = RESEARCH) -> Path:
    raw = review.get("research_path")
    if not isinstance(raw, str):
        fail("review.research_path is required")
    path = (root / raw).resolve()
    if path.parent != research_dir.resolve():
        fail("review.research_path must be a file directly inside radar/inbox/research")
    return path


def validate_curated_batch(
    batch: dict,
    canonical: dict,
    path: Path,
    root: Path = ROOT,
    research_dir: Path = RESEARCH,
) -> dict:
    allowed = {"batch_version", "kind", "batch_id", "patches", "review"}
    if set(batch) - allowed or batch.get("batch_version") != 1 or batch.get("kind") != CURATED_KIND:
        fail(f"{path}: unsupported curated enrichment batch envelope")
    if not isinstance(batch.get("batch_id"), str) or not isinstance(batch.get("patches"), list) or not batch["patches"]:
        fail(f"{path}: batch_id and non-empty patches are required")
    reject_private_text(batch, str(path))
    review = batch.get("review")
    if not isinstance(review, dict) or set(review) != {"research_path", "research_batch_id", "research_sha256", "approved_by", "approved_on"}:
        fail(f"{path}: exact review metadata is required")
    if not isinstance(review["approved_by"], str) or not review["approved_by"].strip():
        fail(f"{path}: review.approved_by is required")
    validate_iso_date(review["approved_on"], f"{path}.review.approved_on")
    research_path = research_path_from_review(review, root, research_dir)
    research = read_json(research_path)
    if review["research_sha256"] != sha256_file(research_path):
        fail(f"{path}: research SHA-256 does not match the preserved source batch")
    if review["research_batch_id"] != research.get("batch_id") or batch["batch_id"] != research.get("batch_id"):
        fail(f"{path}: research and curated batch IDs must match")
    if batch["patches"] != research.get("events"):
        fail(f"{path}: curated patches must exactly match the reviewed research batch")
    report = validate_research_batch(research, canonical, research_path)
    report["path"] = str(path)
    return report
