#!/usr/bin/env python3
"""Manually promote a verified RADAR event to The Signal."""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

if __package__:
    from .validate_signals import (
        REENTRY_DAYS,
        SignalValidationError,
        calculate_minimum_until,
        event_final_date,
        iso_date,
        read_json,
        validate_signals,
    )
else:
    from validate_signals import (  # type: ignore
        REENTRY_DAYS,
        SignalValidationError,
        calculate_minimum_until,
        event_final_date,
        iso_date,
        read_json,
        validate_signals,
    )


class SignalTransitionError(ValueError):
    """A proposed editorial transition violates the Signal policy."""


def bilingual_reason(recorded_on: str, english: str, spanish: str) -> dict:
    return {
        "recorded_on": recorded_on,
        "editorial": {
            "en": {"reason": english.strip()},
            "es": {"reason": spanish.strip()},
        },
    }


def require_pair(english: str | None, spanish: str | None, label: str) -> tuple[str, str] | None:
    values = (english.strip() if isinstance(english, str) else "", spanish.strip() if isinstance(spanish, str) else "")
    if bool(values[0]) != bool(values[1]):
        raise SignalTransitionError(f"{label} requires both English and Spanish copy")
    return values if all(values) else None


def transition_signal(
    signals: dict,
    events: dict,
    event_id: str,
    activated_on: str,
    why_now_en: str,
    why_now_es: str,
    action_deadline: str | None = None,
    urgent_override_en: str | None = None,
    urgent_override_es: str | None = None,
    material_change_en: str | None = None,
    material_change_es: str | None = None,
) -> tuple[dict, dict]:
    """Return a validated transition and a human-readable report without writing."""
    validate_signals(signals, events)
    if not why_now_en.strip() or not why_now_es.strip():
        raise SignalTransitionError("native English and Spanish why-now copy is required")

    activation = iso_date(activated_on, "activated_on")
    event_index = {event.get("id"): event for event in events["events"] if isinstance(event, dict)}
    event = event_index.get(event_id)
    if event is None:
        raise SignalTransitionError(f"unknown canonical event: {event_id}")

    proposed = deepcopy(signals)
    records = proposed["signals"]
    current = next(record for record in records if record["replaced_on"] is None)
    if current["event_id"] == event_id:
        raise SignalTransitionError(f"{event_id} is already the current Signal")
    if activation < iso_date(current["activated_on"], "current.activated_on"):
        raise SignalTransitionError("activated_on cannot precede the current Signal activation")
    if activation > event_final_date(event, f"event {event_id}"):
        raise SignalTransitionError("the proposed event has already finished on activated_on")

    urgent_pair = require_pair(urgent_override_en, urgent_override_es, "urgent override")
    current_minimum = iso_date(current["minimum_until"], "current.minimum_until")
    early_replacement = activation < current_minimum
    if early_replacement and urgent_pair is None:
        raise SignalTransitionError(
            f"the current Signal is protected through {current['minimum_until']}; "
            "bilingual urgent-override copy is required"
        )
    if not early_replacement and urgent_pair is not None:
        raise SignalTransitionError("urgent-override copy is allowed only before minimum_until")

    material_pair = require_pair(material_change_en, material_change_es, "material change")
    prior_records = [record for record in records if record["event_id"] == event_id]
    reentry_days = None
    if prior_records:
        prior = prior_records[-1]
        if prior["replaced_on"] is None:
            raise SignalTransitionError("the proposed event is already current")
        reentry_days = (activation - iso_date(prior["replaced_on"], "prior.replaced_on")).days
        if reentry_days < REENTRY_DAYS and material_pair is None:
            raise SignalTransitionError(
                f"{event_id} left The Signal {reentry_days} days ago; "
                "bilingual material-change copy is required for re-entry within 30 days"
            )
    elif material_pair is not None:
        raise SignalTransitionError("material-change copy is only valid when an event re-enters The Signal")

    deadline = iso_date(action_deadline, "action_deadline") if action_deadline else None
    minimum_until = calculate_minimum_until(activation, event, deadline)
    signal_id = f"signal-{activated_on}-{event_id}"
    if any(record["signal_id"] == signal_id for record in records):
        raise SignalTransitionError(f"Signal record already exists: {signal_id}")

    current["replaced_on"] = activated_on
    current["replaced_by"] = signal_id
    current["early_replacement_override"] = (
        bilingual_reason(activated_on, *urgent_pair) if urgent_pair is not None else None
    )
    new_record = {
        "signal_id": signal_id,
        "event_id": event_id,
        "activated_on": activated_on,
        "minimum_until": minimum_until.isoformat(),
        "action_deadline": action_deadline,
        "replaced_on": None,
        "replaced_by": None,
        "editorial": {
            "en": {"why_now": why_now_en.strip()},
            "es": {"why_now": why_now_es.strip()},
        },
        "early_replacement_override": None,
        "reentry_material_change": (
            bilingual_reason(activated_on, *material_pair) if material_pair is not None else None
        ),
    }
    records.append(new_record)
    validate_signals(proposed, events)

    report = {
        "from": {"signal_id": signals["signals"][-1]["signal_id"], "event_id": signals["signals"][-1]["event_id"]},
        "to": {"signal_id": signal_id, "event_id": event_id},
        "activated_on": activated_on,
        "minimum_until": new_record["minimum_until"],
        "action_deadline": action_deadline,
        "early_replacement": early_replacement,
        "reentry_days": reentry_days,
        "material_change_documented": material_pair is not None,
    }
    return proposed, report


def atomic_write_json(path: Path, payload: dict) -> None:
    """Atomically replace a JSON file, leaving the original intact on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Manually replace the current Listening Notes Signal.")
    command.add_argument("event_id", help="Canonical RADAR event ID to promote")
    command.add_argument("--why-now-en", required=True, help="Native English why-now rationale")
    command.add_argument("--why-now-es", required=True, help="Native Spanish why-now rationale")
    command.add_argument("--activated-on", default=date.today().isoformat(), help="Activation date (default: today)")
    command.add_argument("--action-deadline", help="Verified earlier decision/sale deadline, YYYY-MM-DD")
    command.add_argument("--urgent-override-en", help="English urgent reason for replacing before minimum_until")
    command.add_argument("--urgent-override-es", help="Spanish urgent reason for replacing before minimum_until")
    command.add_argument("--material-change-en", help="English material-change reason for re-entry within 30 days")
    command.add_argument("--material-change-es", help="Spanish material-change reason for re-entry within 30 days")
    command.add_argument("--signals", type=Path, default=Path("radar/signals.json"))
    command.add_argument("--events", type=Path, default=Path("radar/events.json"))
    command.add_argument("--dry-run", action="store_true", help="Report the transition without writing")
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        signals = read_json(arguments.signals)
        events = read_json(arguments.events)
        proposed, report = transition_signal(
            signals,
            events,
            arguments.event_id,
            arguments.activated_on,
            arguments.why_now_en,
            arguments.why_now_es,
            arguments.action_deadline,
            arguments.urgent_override_en,
            arguments.urgent_override_es,
            arguments.material_change_en,
            arguments.material_change_es,
        )
        print(json.dumps({"dry_run": arguments.dry_run, **report}, ensure_ascii=False, indent=2))
        if not arguments.dry_run:
            atomic_write_json(arguments.signals, proposed)
            print(f"Updated {arguments.signals} atomically.")
    except (OSError, SignalValidationError, SignalTransitionError) as error:
        print(f"Signal transition rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
