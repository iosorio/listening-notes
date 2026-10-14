#!/usr/bin/env python3
"""Verify the exact, evidence-bound historical discovery provenance backfill."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from .merge_inbox import merge
except ImportError:
    from merge_inbox import merge


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "radar/inbox/review/discovery-provenance-backfill-2026-09-29.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_historical_target(label: str, expected_hash: str) -> bytes:
    """Keep the exact recorded bytes anchored to committed history."""
    revisions = subprocess.check_output(
        ["git", "rev-list", "HEAD", "--", label], cwd=ROOT, text=True,
    ).splitlines()
    for revision in revisions:
        raw = subprocess.check_output(["git", "show", f"{revision}:{label}"], cwd=ROOT)
        if digest(raw) == expected_hash:
            return raw
    raise ValueError("discovery backfill target hash is absent from committed history")


def require_published_intake(name: str, raw: bytes) -> None:
    """A processed batch must preserve an actual curated input in HEAD's history."""
    label = f"radar/inbox/curated/{name}"
    revisions = subprocess.check_output(
        ["git", "rev-list", "HEAD", "--", label], cwd=ROOT, text=True,
    ).splitlines()
    for revision in revisions:
        source = subprocess.run(
            ["git", "show", f"{revision}:{label}"], cwd=ROOT, capture_output=True,
        )
        if source.returncode == 0 and source.stdout == raw:
            return
    raise ValueError(f"processed intake does not preserve a published curated source: {name}")


def replay_processed_intake(baseline: dict, current: dict, batches: list[Path]) -> dict:
    """Extend the protected snapshot only by deterministic, reviewed v2 intake."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        canonical = root / "events.json"
        curated = root / "curated"
        curated.mkdir()
        canonical.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n")
        inputs = []
        for batch in batches:
            path = curated / batch.name
            path.write_bytes(batch.read_bytes())
            inputs.append(path)
        report = merge(inputs, False, canonical, curated, root / "processed")
        require(not any(report[key] for key in ("conflicts", "semantic_conflicts", "blocked")),
                "processed discovery intake cannot be replayed without conflicts or blocked candidates")
        require(json.loads(canonical.read_text()) == current,
                "canonical data does not match the protected backfill plus reviewed processed intake")
        return {"batches": len(batches), "events_added": len(report["added"])}


def verify(expected_source_sha256: str | None = None, manifest_path: Path = MANIFEST) -> dict:
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema_version") == 1 and manifest.get("kind") == "radar_discovery_provenance_backfill", "unsupported discovery backfill manifest")
    source_path = manifest.get("source_path")
    source_ref = manifest.get("source_ref")
    require(source_path == "radar/events.json" and isinstance(source_ref, str), "unexpected discovery backfill source")
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", source_ref, "HEAD"], cwd=ROOT)
    require(ancestry.returncode == 0, "discovery backfill source is not an ancestor of HEAD")
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
    baseline_raw = read_historical_target(source_path, manifest.get("target_sha256"))
    require(json.loads(baseline_raw) == reconstructed, "discovery backfill contains unrecorded canonical changes")
    batches = []
    for path in sorted((ROOT / "radar/inbox/processed").glob("*.json")):
        raw = path.read_bytes()
        if json.loads(raw).get("batch_version") == 2:
            require_published_intake(path.name, raw)
            batches.append(path)
    evolution = replay_processed_intake(reconstructed, json.loads(current_raw), batches)
    classification = manifest.get("classification", {})
    require(sum(classification.values()) == len(source["events"]), "discovery backfill classification does not cover canonical events")
    require(classification == {"exact_timestamp_recoverable": 2, "date_recoverable": 0, "unknown": 224}, "discovery backfill classification changed")
    return {"manifest": str(manifest_path.relative_to(ROOT)), "events": sorted(seen),
            "target_sha256": digest(baseline_raw), "current_sha256": digest(current_raw),
            "processed_intake": evolution}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
