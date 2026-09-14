#!/usr/bin/env python3
"""Safely materialize approved RADAR duplicate decisions from a plan manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from .merge_inbox import normalize, validate_batch, validate_canonical
    from .plan_radar_intake import decide
    from .venue_identity import load_registry, canonicalize_venue
except ImportError:  # Direct script execution.
    from merge_inbox import normalize, validate_batch, validate_canonical
    from plan_radar_intake import decide
    from venue_identity import load_registry, canonicalize_venue


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
ACTIVE = ROOT / "radar/inbox/curated"
ARCHIVE = ROOT / "radar/inbox/review/decisions"
REGISTRY = ROOT / "radar/venue_identities.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def selected(manifest: dict) -> dict[Path, dict[int, dict]]:
    if manifest.get("canonical", {}).get("sha256") != digest(CANONICAL):
        raise ValueError("manifest was planned against a different canonical events.json")
    if manifest.get("venue_registry", {}).get("sha256") != digest(REGISTRY):
        raise ValueError("manifest was planned against a different venue registry")
    canonical = json.loads(CANONICAL.read_text())["events"]
    canonical_by_id = {event["id"]: event for event in canonical}
    registry = load_registry(REGISTRY)
    groups: dict[Path, dict[int, dict]] = {}
    for decision in manifest.get("decisions", []):
        if decision.get("action") != "archive_duplicate" or decision.get("approval") not in {"approved", "permitted"}:
            continue
        if decision.get("materialization", {}).get("status") == "blocked_residual_validation":
            continue
        label = decision.get("path")
        if not isinstance(label, str) or Path(label).is_absolute() or ".." in Path(label).parts or label.startswith("wip:"):
            raise ValueError("archive decision requires a relative active batch path")
        path = (ROOT / label).resolve()
        if path.parent != ACTIVE.resolve() or not path.is_file() or decision.get("sha256") != digest(path):
            raise ValueError(f"candidate evidence changed since planning: {label}")
        index = decision.get("event_index")
        batch = json.loads(path.read_text())
        if type(index) is not int or not 0 <= index < len(batch["events"]):
            raise ValueError(f"archive decision has no usable event index: {label}")
        candidate = batch["events"][index]
        if candidate.get("id") != decision.get("candidate_event_id"):
            raise ValueError(f"candidate ID does not match event index: {label}")
        if index in groups.get(path, {}):
            raise ValueError(f"repeated archive decision: {label}:{index}")
        existing = canonical_by_id.get(decision.get("canonical_event_id"))
        if existing is None:
            raise ValueError(f"unknown canonical event: {label}")
        current = decide(deepcopy(candidate), canonical, registry)
        if decision["approval"] == "permitted":
            if any(decision.get(key) != value for key, value in current.items()):
                raise ValueError(f"duplicate evidence no longer matches planner: {label}")
        else:
            research = decision.get("research", {})
            if (current.get("action") != "review"
                    or current.get("canonical_event_id") != existing["id"]
                    or decision.get("planned_decision") != current
                    or research.get("outcome") != "same_engagement"
                    or not research.get("reason")
                    or not research.get("sources")):
                raise ValueError(f"approved duplicate requires bound official research: {label}")
            date.fromisoformat(research.get("checked_on", ""))
            for source in research["sources"]:
                if not source.get("url", "").startswith("https://") or not source.get("finding"):
                    raise ValueError(f"official research source is incomplete: {label}")
            if (decision.get("candidate_event_sha256") != data_digest(candidate)
                    or decision.get("canonical_event_sha256") != data_digest(existing)):
                raise ValueError(f"researched event hashes do not match: {label}")
            if (candidate.get("dates") != existing.get("dates")
                    or canonicalize_venue(candidate["venue"], registry)[0]["id"]
                    != canonicalize_venue(existing["venue"], registry)[0]["id"]
                    or (candidate.get("showtimes") and existing.get("showtimes")
                        and set(candidate["showtimes"]).isdisjoint(existing["showtimes"]))):
                raise ValueError(f"research conflicts with recorded functions: {label}")
        groups.setdefault(path, {})[index] = decision
    return groups


def materialize(manifest: dict, apply: bool) -> dict:
    groups = selected(manifest)
    report = {"dry_run": not apply, "archived": [], "residual": [], "removed_active": []}
    validate_canonical(json.loads(CANONICAL.read_text()))
    # Preflight complete residual batches in a temporary tree. No production
    # file moves until every selected split is structurally valid.
    with TemporaryDirectory() as directory:
        temporary_curated = Path(directory) / "curated"
        temporary_curated.mkdir()
        for path, decisions in groups.items():
            archive = ARCHIVE / f"{digest(path)}-{path.name}"
            if archive.exists():
                raise ValueError(f"refusing to overwrite archived evidence: {archive}")
            indexes = set(decisions)
            batch = json.loads(path.read_text())
            duplicate_events = [event for index, event in enumerate(batch["events"]) if index in indexes]
            residual_events = [event for index, event in enumerate(batch["events"]) if index not in indexes]
            if residual_events:
                residual = dict(batch, events=residual_events)
                check = temporary_curated / path.name
                check.write_text(json.dumps(residual, ensure_ascii=False, indent=2) + "\n")
                validate_batch(residual, check, temporary_curated)
                for index, event in enumerate(residual_events):
                    individual = dict(batch, events=[event])
                    validate_batch(individual, temporary_curated / f"{index}-{path.name}", temporary_curated)
                    normalized, _changes = normalize(deepcopy(event))
                    validate_canonical({"schema_version": 3, "events": [normalized]})
            report["archived"].append({"source": str(path.relative_to(ROOT)), "events": [event.get("id") for event in duplicate_events], "sha256": digest(path)})
            if residual_events:
                report["residual"].append({"path": str(path.relative_to(ROOT)), "events": [{"id": event.get("id"), "sha256": data_digest(event)} for event in residual_events]})
            else:
                report["removed_active"].append(str(path.relative_to(ROOT)))
    if not apply:
        return report
    for path, decisions in groups.items():
        indexes = set(decisions)
        batch = json.loads(path.read_text())
        duplicate_events = [event for index, event in enumerate(batch["events"]) if index in indexes]
        residual_events = [event for index, event in enumerate(batch["events"]) if index not in indexes]
        archive = ARCHIVE / f"{digest(path)}-{path.name}"
        if archive.exists():
            raise ValueError(f"refusing to overwrite archived evidence: {archive}")
        archive.parent.mkdir(parents=True, exist_ok=True)
        archived = {
            "kind": "radar_intake_duplicate_archive",
            "source": {
                "path": str(path.relative_to(ROOT)),
                "sha256": digest(path),
                "original_text": path.read_bytes().decode("utf-8"),
                "original_batch": batch,
            },
            "duplicates": [
                {
                    "original_event": event,
                    "original_event_sha256": data_digest(event),
                    "canonical_event_id": decisions[index]["canonical_event_id"],
                    "decision": deepcopy(decisions[index]),
                }
                for index, event in enumerate(batch["events"])
                if index in indexes
            ],
        }
        archive.write_text(json.dumps(archived, ensure_ascii=False, indent=2) + "\n")
        if residual_events:
            path.write_text(json.dumps(dict(batch, events=residual_events), ensure_ascii=False, indent=2) + "\n")
        else:
            path.unlink()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(materialize(json.loads(args.manifest.read_text()), args.apply), ensure_ascii=False, indent=2))
    except ValueError as error:
        parser.exit(2, f"materialize RADAR intake: {error}\n")


if __name__ == "__main__":
    main()
