#!/usr/bin/env python3
"""Safely materialize approved RADAR duplicate decisions from a plan manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from .merge_inbox import validate_batch, validate_canonical
except ImportError:  # Direct script execution.
    from merge_inbox import validate_batch, validate_canonical


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "radar/events.json"
ACTIVE = ROOT / "radar/inbox/curated"
ARCHIVE = ROOT / "radar/inbox/review/decisions"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def selected(manifest: dict) -> dict[Path, dict[int, dict]]:
    if manifest.get("canonical", {}).get("sha256") != digest(CANONICAL):
        raise ValueError("manifest was planned against a different canonical events.json")
    groups: dict[Path, dict[int, dict]] = {}
    for decision in manifest.get("decisions", []):
        if decision.get("action") != "archive_duplicate" or decision.get("approval") not in {"approved", "permitted"}:
            continue
        label = decision.get("path")
        if not isinstance(label, str) or label.startswith("wip:"):
            continue
        path = ROOT / label
        if path.parent != ACTIVE or not path.is_file() or decision.get("sha256") != digest(path):
            raise ValueError(f"candidate evidence changed since planning: {label}")
        index = decision.get("event_index")
        if not isinstance(index, int):
            raise ValueError(f"archive decision has no usable event index: {label}")
        groups.setdefault(path, {})[index] = decision
    return groups


def materialize(manifest: dict, apply: bool) -> dict:
    groups = selected(manifest)
    report = {"archived": [], "residual": [], "untouched": []}
    validate_canonical(json.loads(CANONICAL.read_text()))
    # Preflight complete residual batches in a temporary tree. No production
    # file moves until every selected split is structurally valid.
    with TemporaryDirectory() as directory:
        temporary_curated = Path(directory) / "curated"
        temporary_curated.mkdir()
        for path, decisions in groups.items():
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
            report["archived"].append({"source": str(path.relative_to(ROOT)), "events": [event.get("id") for event in duplicate_events], "sha256": digest(path)})
            if residual_events:
                report["residual"].append({"path": str(path.relative_to(ROOT)), "events": [{"id": event.get("id"), "sha256": data_digest(event)} for event in residual_events]})
            else:
                report["untouched"].append(str(path.relative_to(ROOT)))
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
                "original_batch": batch,
            },
            "duplicates": [
                {
                    "original_event": event,
                    "original_event_sha256": data_digest(event),
                    "canonical_event_id": decisions[index]["canonical_event_id"],
                    "decision": {
                        key: decisions[index].get(key)
                        for key in ("action", "approval", "evidence", "diff", "normalization")
                    },
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
