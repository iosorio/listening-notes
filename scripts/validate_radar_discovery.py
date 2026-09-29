#!/usr/bin/env python3
"""Validate RADAR desired state/run telemetry and report derived health."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "radar/discovery/status.json"
RUNS = ROOT / "radar/discovery/runs.json"
RUN_STATUSES = {"success", "partial", "error"}
TRIGGERS = {"scheduled", "manual", "external"}
COUNTERS = (
    "sources_checked",
    "candidates_reviewed",
    "events_admitted",
    "events_published",
    "material_updates",
)


class DiscoveryValidationError(ValueError):
    """A deterministic discovery operational-data validation error."""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise DiscoveryValidationError(f"{path}: {error}") from error
    if not isinstance(value, dict):
        raise DiscoveryValidationError(f"{path}: root must be an object")
    return value


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise DiscoveryValidationError(f"{field} must be an ISO-8601 timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DiscoveryValidationError(f"{field} must be an ISO-8601 timestamp with timezone") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DiscoveryValidationError(f"{field} must include a timezone")
    return parsed


def validate_status(payload: dict) -> dict:
    required = {
        "schema_version", "enabled", "cadence", "expected_max_silence_hours",
        "changed_at", "changed_by", "reason", "state_history",
    }
    if set(payload) != required or payload.get("schema_version") != 1:
        raise DiscoveryValidationError("status.json has an unsupported shape or schema_version")
    if not isinstance(payload["enabled"], bool):
        raise DiscoveryValidationError("status.enabled must be boolean")
    if not isinstance(payload["cadence"], str) or not payload["cadence"].strip():
        raise DiscoveryValidationError("status.cadence must be a non-empty string")
    silence = payload["expected_max_silence_hours"]
    if not isinstance(silence, (int, float)) or isinstance(silence, bool) or silence <= 0:
        raise DiscoveryValidationError("status.expected_max_silence_hours must be positive")
    parse_timestamp(payload["changed_at"], "status.changed_at")
    for field in ("changed_by", "reason"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise DiscoveryValidationError(f"status.{field} must be non-empty")
    history = payload["state_history"]
    if not isinstance(history, list) or not history:
        raise DiscoveryValidationError("status.state_history must be a non-empty array")
    previous = None
    for index, record in enumerate(history):
        field = f"status.state_history[{index}]"
        if not isinstance(record, dict) or set(record) != {"enabled", "changed_at", "changed_by", "reason"}:
            raise DiscoveryValidationError(f"{field} has an unsupported shape")
        if not isinstance(record["enabled"], bool):
            raise DiscoveryValidationError(f"{field}.enabled must be boolean")
        changed = parse_timestamp(record["changed_at"], f"{field}.changed_at")
        if previous and changed <= previous:
            raise DiscoveryValidationError("status.state_history must be strictly chronological")
        previous = changed
        for name in ("changed_by", "reason"):
            if not isinstance(record[name], str) or not record[name].strip():
                raise DiscoveryValidationError(f"{field}.{name} must be non-empty")
    latest = history[-1]
    for field in ("enabled", "changed_at", "changed_by", "reason"):
        if payload[field] != latest[field]:
            raise DiscoveryValidationError(f"status.{field} must match the latest state_history record")
    return payload


def validate_runs(payload: dict) -> list[dict]:
    if set(payload) != {"schema_version", "runs"} or payload.get("schema_version") != 1:
        raise DiscoveryValidationError("runs.json has an unsupported shape or schema_version")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise DiscoveryValidationError("runs must be an array")
    required = {
        "run_id", "started_at", "completed_at", "trigger", "status", "executor",
        "threads_checked", *COUNTERS, "error_summary",
    }
    seen: set[str] = set()
    previous = None
    for index, run in enumerate(runs):
        field = f"runs[{index}]"
        if not isinstance(run, dict) or set(run) != required:
            raise DiscoveryValidationError(f"{field} has an unsupported shape")
        run_id = run["run_id"]
        if not isinstance(run_id, str) or not run_id.strip() or run_id in seen:
            raise DiscoveryValidationError(f"{field}.run_id must be non-empty and unique")
        seen.add(run_id)
        started = parse_timestamp(run["started_at"], f"{field}.started_at")
        completed = parse_timestamp(run["completed_at"], f"{field}.completed_at")
        if completed < started:
            raise DiscoveryValidationError(f"{field}.completed_at precedes started_at")
        if previous and started <= previous:
            raise DiscoveryValidationError("runs must be append-only in strictly increasing started_at order")
        previous = started
        if run["trigger"] not in TRIGGERS or run["status"] not in RUN_STATUSES:
            raise DiscoveryValidationError(f"{field} has an unsupported trigger or status")
        if not isinstance(run["executor"], str) or not run["executor"].strip():
            raise DiscoveryValidationError(f"{field}.executor must be non-empty")
        threads = run["threads_checked"]
        if not isinstance(threads, list) or any(not isinstance(item, str) or not item.strip() for item in threads):
            raise DiscoveryValidationError(f"{field}.threads_checked must be an array of non-empty strings")
        for counter in COUNTERS:
            value = run[counter]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise DiscoveryValidationError(f"{field}.{counter} must be a non-negative integer")
        error = run["error_summary"]
        if run["status"] == "success" and error is not None:
            raise DiscoveryValidationError(f"{field}.error_summary must be null for success")
        if run["status"] in {"partial", "error"} and (not isinstance(error, str) or not error.strip()):
            raise DiscoveryValidationError(f"{field}.error_summary is required for partial/error")
    return runs


def cadence_delta(value: str) -> timedelta | None:
    if value == "hourly":
        return timedelta(hours=1)
    if value.startswith("every_") and value.endswith("_hours"):
        try:
            hours = int(value[6:-6])
        except ValueError:
            return None
        return timedelta(hours=hours) if hours > 0 else None
    return None


def derive_health(status: dict, runs: list[dict], now: datetime) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise DiscoveryValidationError("now must include a timezone")
    latest = runs[-1] if runs else None
    successes = [run for run in runs if run["status"] == "success"]
    last_success = successes[-1] if successes else None
    result = {
        "state": "off" if not status["enabled"] else "unknown",
        "latest_run": latest,
        "last_successful_run": last_success,
        "next_expected_at": None,
    }
    if not status["enabled"]:
        return result
    if latest and latest["status"] == "error":
        result["state"] = "error"
    elif last_success:
        completed = parse_timestamp(last_success["completed_at"], "last_success.completed_at")
        threshold = timedelta(hours=status["expected_max_silence_hours"])
        result["state"] = "healthy" if now <= completed + threshold else "stale"
    cadence = cadence_delta(status["cadence"])
    if last_success and cadence:
        completed = parse_timestamp(last_success["completed_at"], "last_success.completed_at")
        result["next_expected_at"] = (completed + cadence).isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=STATUS)
    parser.add_argument("--runs", type=Path, default=RUNS)
    parser.add_argument("--now", help="ISO-8601 timestamp used for deterministic health checks")
    args = parser.parse_args()
    try:
        status = validate_status(read_json(args.status))
        runs = validate_runs(read_json(args.runs))
        now = parse_timestamp(args.now, "--now") if args.now else datetime.now(timezone.utc)
        report = derive_health(status, runs, now)
    except DiscoveryValidationError as error:
        parser.exit(1, f"Invalid RADAR discovery data: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["state"] in {"stale", "error", "unknown"}:
        print(f"RADAR operational warning: {report['state'].upper()}", file=sys.stderr)


if __name__ == "__main__":
    main()
