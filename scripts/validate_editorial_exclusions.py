#!/usr/bin/env python3
"""Validate the append-only ledger of withdrawn RADAR editorial admissions."""
import json
import sys
from datetime import date
from pathlib import Path

FIELDS = {"event_id", "excluded_on", "decision", "reviewed_by", "rationale"}

def validate(ledger, canonical):
    if not isinstance(ledger, dict) or set(ledger) != {"schema_version", "exclusions"}:
        raise ValueError("expected schema_version and exclusions")
    if ledger["schema_version"] != 1 or not isinstance(ledger["exclusions"], list):
        raise ValueError("unsupported exclusions schema")
    if canonical.get("schema_version") != 3 or not isinstance(canonical.get("events"), list):
        raise ValueError("invalid canonical catalog")
    ids = {e["id"] for e in canonical["events"]}
    seen = set()
    for i, item in enumerate(ledger["exclusions"]):
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise ValueError(f"exclusions[{i}]: invalid fields")
        event_id = item["event_id"]
        if not isinstance(event_id, str) or event_id not in ids:
            raise ValueError(f"exclusions[{i}]: unknown canonical event")
        if event_id in seen:
            raise ValueError(f"exclusions[{i}]: duplicate event")
        seen.add(event_id)
        if item["decision"] != "editorial_retraction":
            raise ValueError(f"exclusions[{i}]: invalid decision")
        try:
            if not isinstance(item["excluded_on"], str) or date.fromisoformat(item["excluded_on"]).isoformat() != item["excluded_on"]:
                raise ValueError("invalid date")
        except ValueError as error:
            raise ValueError(f"exclusions[{i}]: invalid ISO date") from error
        for key, minimum in (("reviewed_by", 3), ("rationale", 40)):
            if not isinstance(item[key], str) or len(item[key].strip()) < minimum:
                raise ValueError(f"exclusions[{i}]: missing {key}")
    return len(seen)

if __name__ == "__main__":
    try:
        records = json.loads(Path(sys.argv[1] if len(sys.argv)>1 else "radar/editorial_exclusions.json").read_text())
        canonical = json.loads(Path(sys.argv[2] if len(sys.argv)>2 else "radar/events.json").read_text())
        print(f"Validated {validate(records, canonical)} editorial exclusions")
    except (ValueError, OSError) as error:
        sys.exit(f"Invalid editorial exclusions: {error}")
