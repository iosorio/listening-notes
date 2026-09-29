#!/usr/bin/env python3
"""Verify the exact, evidence-bound historical discovery provenance backfill."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "radar/inbox/review/discovery-provenance-backfill-2026-09-29.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify(expected_source_sha256: str | None = None, manifest_path: Path = MANIFEST) -> dict:
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema_version") == 1 and manifest.get("kind") == "radar_discovery_provenance_backfill", "unsupported discovery backfill manifest")
    source_path = manifest.get("source_path")
    source_ref = manifest.get("source_ref")
    require(source_path == "radar/events.json" and isinstance(source_ref, str), "unexpected discovery backfill source")
    source_raw = subprocess.check_output(["git", "show", f"{source_ref}:{source_path}"], cwd=ROOT)
    source_hash = digest(source_raw)
    require(source_hash == manifest.get("source_sha256"), "discovery backfill source hash changed")
    if expected_source_sha256 is not None:
        require(source_hash == expected_source_sha256, "discovery backfill does not continue the protected canonical state")
    source = json.loads(source_raw)
    reconstructed = deepcopy(source)
    by_id = {event["id"]: event for event in reconstructed["events"]}
    seen: set[str] = set()
    changes = manifest.get("changes")
    require(isinstance(changes, list) and len(changes) == 2, "unexpected discovery backfill coverage")
    for change in changes:
        event_id = change.get("event_id")
        require(event_id in by_id and event_id not in seen, "unknown or repeated discovery backfill event")
        seen.add(event_id)
        require(change.get("field") == "discovered_at" and change.get("before") is None, "discovery backfill may only add an unknown discovered_at")
        require("discovered_at" not in by_id[event_id], f"{event_id} already had discovery provenance")
        commit = change.get("evidence_commit")
        timestamp = change.get("evidence_commit_timestamp")
        actual_timestamp = subprocess.check_output(["git", "show", "-s", "--format=%aI", commit], cwd=ROOT, text=True).strip()
        require(actual_timestamp == timestamp == change.get("after"), f"{event_id} evidence timestamp changed")
        commit_tree = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True)
        require(commit_tree.returncode == 0, f"{event_id} evidence commit is unavailable")
        by_id[event_id]["discovered_at"] = change["after"]
    current_raw = (ROOT / source_path).read_bytes()
    require(digest(current_raw) == manifest.get("target_sha256"), "discovery backfill target hash changed")
    require(json.loads(current_raw) == reconstructed, "discovery backfill contains unrecorded canonical changes")
    classification = manifest.get("classification", {})
    require(sum(classification.values()) == len(source["events"]), "discovery backfill classification does not cover canonical events")
    require(classification == {"exact_timestamp_recoverable": 2, "date_recoverable": 0, "unknown": 224}, "discovery backfill classification changed")
    return {"manifest": str(manifest_path.relative_to(ROOT)), "events": sorted(seen), "target_sha256": digest(current_raw)}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
