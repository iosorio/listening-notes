#!/usr/bin/env python3
"""Dependency-free validation for the Listening Notes event record."""

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

PRIORITIES = {"S+", "S", "A+", "A"}
STATUSES = {"considering", "going", "attended", "passed"}
DOMAINS = {"tokyo_kanto", "us_corridor", "north_america", "rest_of_world"}
ATTENDANCE_EVIDENCE = {"user_confirmed", "personal_photo", "ticket_purchase", "logistics_email", "calendar_or_planning", "third_party_ticket", "archival_reference", "post_event_reference", "unknown"}
# A stable event ID ends in its year or, when a historical/show record needs
# disambiguation, its full ISO date. Existing year-only IDs remain valid.
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-\d{4}(?:-\d{2}-\d{2})?$")
ENRICHMENT_STATUSES = {"complete", "pending", "unavailable"}
ENRICHMENT_FIELDS = {"official_event", "official_tickets", "apple_music"}


def valid_public_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.path not in {"", "/"} and "/search" not in parsed.path


def validate_enrichment(event: dict, event_id: str) -> None:
    enrichment = event.get("enrichment")
    if enrichment is None:
        return
    if not isinstance(enrichment, dict) or enrichment.get("status") not in ENRICHMENT_STATUSES:
        fail(f"{event_id}.enrichment requires status complete, pending, or unavailable")
    links = event.get("links", {})
    if not isinstance(links, dict):
        fail(f"{event_id}.links must be an object")
    for field in ("official_event", "official_tickets"):
        value = links.get(field)
        if value is not None and not valid_public_url(value):
            fail(f"{event_id}.links.{field} must be an exact HTTPS event URL, not a search or homepage")
    apple_urls = [item.get("apple_music_url") for item in event.get("recommended_listening", []) if isinstance(item, dict) and item.get("apple_music_url")]
    missing = enrichment.get("missing", [])
    if not isinstance(missing, list) or any(field not in ENRICHMENT_FIELDS for field in missing) or len(set(missing)) != len(missing):
        fail(f"{event_id}.enrichment.missing must be a unique list of known enrichment fields")
    if enrichment["status"] == "complete":
        if missing or not links.get("official_event") or not links.get("official_tickets") or not apple_urls:
            fail(f"{event_id} claims complete enrichment but required links or Apple Music are missing")
    else:
        if not missing or not isinstance(enrichment.get("note"), str) or not enrichment["note"].strip():
            fail(f"{event_id} pending/unavailable enrichment requires missing fields and an explanatory note")


def fail(message: str) -> None:
    print(f"Invalid event data: {message}", file=sys.stderr)
    raise SystemExit(1)


def valid_date(value: object, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        fail(f"{field} must be an ISO date or null")
    try:
        date.fromisoformat(value)
    except ValueError:
        fail(f"{field} is not an ISO date: {value!r}")


def main(path: Path) -> None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(str(error))
    if not isinstance(data, dict) or data.get("schema_version") != 3:
        fail("root must be an object with schema_version 3")
    events = data.get("events")
    if not isinstance(events, list):
        fail("events must be an array")

    ids = set()
    for index, event in enumerate(events):
        prefix = f"events[{index}]"
        if not isinstance(event, dict):
            fail(f"{prefix} must be an object")
        event_id = event.get("id")
        if not isinstance(event_id, str) or not ID.fullmatch(event_id) or event_id in ids:
            fail(f"{prefix}.id must be unique and stable")
        ids.add(event_id)
        priority = event.get("priority")
        if (priority not in PRIORITIES and not (priority is None and event.get("status") == "attended")) or event.get("status") not in STATUSES:
            fail(f"{event_id} has an unsupported priority or status")
        dates = event.get("dates")
        venue = event.get("venue")
        if not isinstance(dates, dict) or not isinstance(venue, dict):
            fail(f"{event_id} requires dates and venue objects")
        valid_date(dates.get("start"), f"{event_id}.dates.start")
        valid_date(dates.get("end"), f"{event_id}.dates.end")
        if not dates.get("start") or not all(isinstance(venue.get(k), str) for k in ("id", "name", "city", "state", "country")):
            fail(f"{event_id} requires a start date and named venue location")
        if event.get("geographic_domain") not in DOMAINS or not isinstance(event.get("musical_axes"), list):
            fail(f"{event_id} requires a known geographic domain and musical_axes array")
        editorial = event.get("editorial")
        if not isinstance(editorial, dict) or not all(isinstance(editorial.get(lang), dict) for lang in ("en", "es")):
            fail(f"{event_id} requires English and Spanish editorial objects")
        tickets = event.get("tickets", {})
        if tickets.get("currency") != "USD":
            fail(f"{event_id} requires an explicit ticket currency")
        for market in ("official", "resale"):
            prices = tickets.get(market)
            if not isinstance(prices, dict):
                fail(f"{event_id}.tickets.{market} must be an object")
            for key in ("minimum", "maximum"):
                if prices.get(key) is not None and not isinstance(prices[key], (int, float)):
                    fail(f"{event_id}.tickets.{market}.{key} must be a number or null")
        if not isinstance(event.get("sources"), list):
            fail(f"{event_id}.sources must be an array")
        recommendations = event.get("recommended_listening")
        if not isinstance(recommendations, list):
            fail(f"{event_id}.recommended_listening must be an array")
        for recommendation in recommendations:
            if not isinstance(recommendation, dict) or not isinstance(recommendation.get("title"), str):
                fail(f"{event_id}.recommended_listening entries require a title")
            apple_music_url = recommendation.get("apple_music_url")
            if apple_music_url is not None:
                if not isinstance(apple_music_url, str):
                    fail(f"{event_id}.recommended_listening.apple_music_url must be a URL or null")
                parsed = urlparse(apple_music_url)
                if parsed.scheme != "https" or parsed.netloc != "music.apple.com" or not re.search(r"/(album|song|playlist)/", parsed.path):
                    fail(f"{event_id}.recommended_listening.apple_music_url must be an exact Apple Music album, song, or playlist URL")
        validate_enrichment(event, event_id)
        attendance = event.get("attendance")
        if not isinstance(attendance, dict) or attendance.get("status") not in {None, "attended", "unknown_attendance"}:
            fail(f"{event_id}.attendance requires a supported status")
        evidence = attendance.get("evidence")
        if not isinstance(evidence, list) or any(not isinstance(item, dict) or item.get("type") not in ATTENDANCE_EVIDENCE for item in evidence):
            fail(f"{event_id}.attendance.evidence has an unsupported type")
    print(f"Validated {len(events)} events in {path}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "radar/events.json"))
