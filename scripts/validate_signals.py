#!/usr/bin/env python3
"""Dependency-free validation for the canonical Listening Notes Signal history."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse


SCHEMA_VERSION = 1
DEFAULT_CYCLE_DAYS = 7
REENTRY_DAYS = 30
ELIGIBLE_PRIORITIES = {"S+", "S", "A+"}
RECORD_FIELDS = {
    "signal_id",
    "event_id",
    "activated_on",
    "minimum_until",
    "action_deadline",
    "replaced_on",
    "replaced_by",
    "editorial",
    "early_replacement_override",
    "reentry_material_change",
}
SIGNAL_ID = re.compile(r"^signal-\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")


class SignalValidationError(ValueError):
    """A deterministic Signal contract failure."""


def fail(message: str) -> None:
    raise SignalValidationError(message)


def read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path}: {error}")
    if not isinstance(payload, dict):
        fail(f"{path}: root must be an object")
    return payload


def iso_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        fail(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail(f"{field} must be an ISO date")


def normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def normalized_url(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            parsed.query,
            "",
        )
    )


def valid_public_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    path = parsed.path.lower()
    if parsed.scheme != "https" or not parsed.netloc or "/search" in path:
        return False
    return parsed.path not in {"", "/"} or bool(parsed.query)


def event_final_date(event: dict, field: str = "event") -> date:
    dates = event.get("dates")
    if not isinstance(dates, dict):
        fail(f"{field}.dates must be an object")
    start = iso_date(dates.get("start"), f"{field}.dates.start")
    end_value = dates.get("end")
    end = iso_date(end_value, f"{field}.dates.end") if end_value is not None else start
    if end < start:
        fail(f"{field}.dates.end must not precede dates.start")
    return end


def calculate_minimum_until(activated_on: date, event: dict, action_deadline: date | None) -> date:
    """Return the deterministic minimum cycle end for a new Signal."""
    candidates = [activated_on + timedelta(days=DEFAULT_CYCLE_DAYS), event_final_date(event)]
    if action_deadline is not None:
        candidates.append(action_deadline)
    return min(candidates)


def validate_localized_text(container: object, field: str, prefix: str) -> None:
    if not isinstance(container, dict) or set(container) != {"en", "es"}:
        fail(f"{prefix} must contain exactly English and Spanish objects")
    for language in ("en", "es"):
        localized = container.get(language)
        if not isinstance(localized, dict) or set(localized) != {field}:
            fail(f"{prefix}.{language} must contain exactly {field}")
        value = localized.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(f"{prefix}.{language}.{field} must be nonempty native-language copy")


def validate_reason(value: object, prefix: str, expected_date: date) -> None:
    if not isinstance(value, dict) or set(value) != {"recorded_on", "editorial"}:
        fail(f"{prefix} must contain recorded_on and editorial")
    recorded_on = iso_date(value.get("recorded_on"), f"{prefix}.recorded_on")
    if recorded_on != expected_date:
        fail(f"{prefix}.recorded_on must match the transition date")
    validate_localized_text(value.get("editorial"), "reason", f"{prefix}.editorial")


def validate_event_eligibility(event: object, event_id: str) -> dict:
    prefix = f"event {event_id}"
    if not isinstance(event, dict):
        fail(f"{prefix} must be an object")
    if not isinstance(event.get("artist"), str) or not event["artist"].strip():
        fail(f"{prefix} requires a verified artist identity")
    if event.get("priority") not in ELIGIBLE_PRIORITIES:
        fail(f"{prefix} priority must be S+, S, or A+")
    event_final_date(event, prefix)
    venue = event.get("venue")
    if not isinstance(venue, dict) or any(
        not isinstance(venue.get(field), str) or not venue[field].strip()
        for field in ("id", "name", "city", "state", "country")
    ):
        fail(f"{prefix} requires a stable, named venue and location")
    links = event.get("links")
    official_event = links.get("official_event") if isinstance(links, dict) else None
    if not valid_public_url(official_event):
        fail(f"{prefix} requires an exact official event page")
    sources = event.get("sources")
    if not isinstance(sources, list) or not sources:
        fail(f"{prefix} requires factual source evidence")
    official_normalized = normalized_url(official_event)
    if not any(
        isinstance(source, dict)
        and isinstance(source.get("url"), str)
        and normalized_url(source["url"]) == official_normalized
        for source in sources
    ):
        fail(f"{prefix} official event page must also be preserved in sources")
    editorial = event.get("editorial")
    if not isinstance(editorial, dict) or any(not isinstance(editorial.get(language), dict) for language in ("en", "es")):
        fail(f"{prefix} requires bilingual event editorial")
    return event


def validate_signals(signals: object, events: object) -> None:
    if not isinstance(signals, dict) or set(signals) != {"schema_version", "signals"}:
        fail("Signal root must contain exactly schema_version and signals")
    if signals.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema_version must be {SCHEMA_VERSION}")
    records = signals.get("signals")
    if not isinstance(records, list) or not records:
        fail("signals must be a nonempty chronological array")

    if not isinstance(events, dict) or not isinstance(events.get("events"), list):
        fail("event data must contain an events array")
    event_index = {
        event.get("id"): event
        for event in events["events"]
        if isinstance(event, dict) and isinstance(event.get("id"), str)
    }

    seen_signal_ids: set[str] = set()
    current_indexes: list[int] = []
    previous_activation: date | None = None
    previous_for_event: dict[str, tuple[dict, date]] = {}

    for index, record in enumerate(records):
        prefix = f"signals[{index}]"
        if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
            fail(f"{prefix} must contain exactly the documented Signal fields")
        signal_id = record.get("signal_id")
        if not isinstance(signal_id, str) or not SIGNAL_ID.fullmatch(signal_id) or signal_id in seen_signal_ids:
            fail(f"{prefix}.signal_id must be unique and stable")
        seen_signal_ids.add(signal_id)
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or event_id not in event_index:
            fail(f"{prefix}.event_id must reference a canonical event")
        event = validate_event_eligibility(event_index[event_id], event_id)

        activated = iso_date(record.get("activated_on"), f"{prefix}.activated_on")
        if signal_id != f"signal-{activated.isoformat()}-{event_id}":
            fail(f"{prefix}.signal_id must be derived from activated_on and event_id")
        if previous_activation is not None and activated < previous_activation:
            fail("Signal records must be chronological by activated_on")
        previous_activation = activated
        final = event_final_date(event, f"event {event_id}")
        if activated > final:
            fail(f"{prefix} cannot activate after the event's final date")

        action_value = record.get("action_deadline")
        action_deadline = iso_date(action_value, f"{prefix}.action_deadline") if action_value is not None else None
        if action_deadline is not None and not (activated <= action_deadline <= final):
            fail(f"{prefix}.action_deadline must fall between activation and the event's final date")
        minimum_until = iso_date(record.get("minimum_until"), f"{prefix}.minimum_until")
        expected_minimum = calculate_minimum_until(activated, event, action_deadline)
        if minimum_until != expected_minimum:
            fail(
                f"{prefix}.minimum_until must be the earlier of the seven-day cycle, "
                "event final date, or documented action deadline"
            )

        validate_localized_text(record.get("editorial"), "why_now", f"{prefix}.editorial")
        for language in ("en", "es"):
            why_now = record["editorial"][language]["why_now"]
            why_it_matters = event.get("editorial", {}).get(language, {}).get("why_it_matters")
            if isinstance(why_it_matters, str) and normalized_text(why_now) == normalized_text(why_it_matters):
                fail(f"{prefix}.editorial.{language}.why_now must be distinct from why_it_matters")

        replaced_on_value = record.get("replaced_on")
        replaced_by = record.get("replaced_by")
        if (replaced_on_value is None) != (replaced_by is None):
            fail(f"{prefix}.replaced_on and replaced_by must both be null or both be set")
        if replaced_on_value is None:
            current_indexes.append(index)
            replaced_on = None
        else:
            replaced_on = iso_date(replaced_on_value, f"{prefix}.replaced_on")
            if not isinstance(replaced_by, str) or not replaced_by.strip():
                fail(f"{prefix}.replaced_by must identify the next Signal record")
            if replaced_on < activated:
                fail(f"{prefix}.replaced_on must not precede activated_on")

        override = record.get("early_replacement_override")
        if replaced_on is not None and replaced_on < minimum_until:
            validate_reason(override, f"{prefix}.early_replacement_override", replaced_on)
        elif override is not None:
            fail(f"{prefix}.early_replacement_override is allowed only for an early replacement")

        reentry = record.get("reentry_material_change")
        prior = previous_for_event.get(event_id)
        if prior is None:
            if reentry is not None:
                fail(f"{prefix}.reentry_material_change requires a previous Signal for the same event")
        else:
            prior_record, prior_replaced_on = prior
            days_since_replacement = (activated - prior_replaced_on).days
            if days_since_replacement < 0:
                fail(f"{prefix} re-enters before its previous Signal record was replaced")
            if days_since_replacement < REENTRY_DAYS:
                validate_reason(reentry, f"{prefix}.reentry_material_change", activated)
            elif reentry is not None:
                validate_reason(reentry, f"{prefix}.reentry_material_change", activated)
        if replaced_on is not None:
            previous_for_event[event_id] = (record, replaced_on)

    if len(current_indexes) != 1:
        fail("exactly one Signal record must be current")
    if current_indexes[0] != len(records) - 1:
        fail("the current Signal must be the final chronological record")

    for index, record in enumerate(records[:-1]):
        following = records[index + 1]
        if record["replaced_on"] != following["activated_on"]:
            fail(f"signals[{index}].replaced_on must match the next activation date")
        if record["replaced_by"] != following["signal_id"]:
            fail(f"signals[{index}].replaced_by must identify the next Signal record")


def validate_files(signal_path: Path, event_path: Path) -> None:
    validate_signals(read_json(signal_path), read_json(event_path))


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    signal_path = Path(arguments[0]) if arguments else Path("radar/signals.json")
    event_path = Path(arguments[1]) if len(arguments) > 1 else Path("radar/events.json")
    if len(arguments) > 2:
        print("Usage: validate_signals.py [SIGNALS_JSON] [EVENTS_JSON]", file=sys.stderr)
        return 2
    try:
        validate_files(signal_path, event_path)
    except SignalValidationError as error:
        print(f"Invalid Signal data: {error}", file=sys.stderr)
        return 1
    print(f"Valid Signal data: {signal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
