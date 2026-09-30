#!/usr/bin/env python3
"""Append an actual completed executor heartbeat; never run discovery or schedule it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

try:
    from .validate_radar_discovery import DiscoveryValidationError, RUNS, read_json, validate_runs
except ImportError:
    from validate_radar_discovery import DiscoveryValidationError, RUNS, read_json, validate_runs


def append_run(payload: dict, record: dict) -> dict:
    runs = validate_runs(payload)
    validate_runs({"schema_version": 1, "runs": [record]})
    existing = next((run for run in runs if run["run_id"] == record["run_id"]), None)
    if existing is not None:
        if existing != record:
            raise DiscoveryValidationError("run_id already exists with different content; heartbeats are immutable")
        return payload  # A publication retry is not another scan.
    result = {"schema_version": 1, "runs": runs + [record]}
    validate_runs(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True, help="JSON object with the actual completed run")
    parser.add_argument("--runs", type=Path, default=RUNS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    temporary = None
    try:
        payload = read_json(args.runs)
        updated = append_run(payload, read_json(args.record))
        if updated == payload:
            print("Heartbeat already recorded unchanged.")
        elif args.dry_run:
            print("Valid heartbeat; dry run made no changes.")
        else:
            # Use a dedicated checkout and serialize runs. Git's non-force push
            # protects the shared ledger against another publisher's commits.
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.runs.parent, delete=False) as output:
                temporary = output.name
                json.dump(updated, output, ensure_ascii=False, indent=2)
                output.write("\n")
            os.replace(temporary, args.runs)
            temporary = None
            print("Heartbeat appended locally; commit and publish it with the reviewed intake.")
    except (DiscoveryValidationError, OSError) as error:
        parser.exit(1, f"Cannot record RADAR run: {error}\n")
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
