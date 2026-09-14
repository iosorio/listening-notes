#!/usr/bin/env python3
"""Audit a completed duplicate resolution without changing any repository file."""

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

try:
    from .materialize_radar_intake import data_digest, digest
    from .merge_inbox import normalize, validate_batch, validate_canonical
    from .plan_radar_intake import plan
    from .radar_verification import (
        PUBLISHED,
        TEMPORARY_MATERIALIZATION,
        VERIFICATION_MODES,
        require_base_ancestor,
        verify_published_at_head,
        verify_temporary_materialization,
    )
    from .remediate_radar_intake import (
        data_sha256,
        desired_batch,
        verify as verify_validation_remediation,
    )
except ImportError:
    from materialize_radar_intake import data_digest, digest
    from merge_inbox import normalize, validate_batch, validate_canonical
    from plan_radar_intake import plan
    from radar_verification import (
        PUBLISHED,
        TEMPORARY_MATERIALIZATION,
        VERIFICATION_MODES,
        require_base_ancestor,
        verify_published_at_head,
        verify_temporary_materialization,
    )
    from remediate_radar_intake import (
        data_sha256,
        desired_batch,
        verify as verify_validation_remediation,
    )

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "radar/inbox/curated"
ARCHIVE = ROOT / "radar/inbox/review/decisions"
VALIDATION_ARCHIVE = ROOT / "radar/inbox/review/validation-decisions"
VALIDATION_MANIFESTS = ROOT / "radar/inbox/review"
HISTORICAL_PROTECTED_SHA256 = {
    "scripts/verify_radar_duplicate_resolution.py": "5da1e965a8d299c76b1be17d0d972c934f7c35f284057c27927bb5ebd9aac8c7",
    "tests/test_radar_signal_ui.py": "bf379cff2a06a1316174acf4aec31e6daab172f5f45b61ee1b561c8c55a93023",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_stage_or_later(label, expected_hash, expected_batch=None):
    """Accept an exact historical stage or its hash-bound validation successor."""
    path = ROOT / label
    if path.is_file() and digest(path) == expected_hash:
        if expected_batch is not None:
            require(json.loads(path.read_text()) == expected_batch, f"historical stage JSON changed: {label}")
        return []

    archive = VALIDATION_ARCHIVE / f"{expected_hash}-{path.name}"
    if archive.is_file():
        record = json.loads(archive.read_text())
        require(record.get("kind") == "radar_intake_validation_archive", f"wrong later archive kind: {label}")
        source = record.get("source", {})
        raw = source.get("original_text", "").encode("utf-8")
        require(source.get("path") == label, f"later archive source path changed: {label}")
        require(hashlib.sha256(raw).hexdigest() == expected_hash == source.get("sha256"), f"later archive source hash changed: {label}")
        original = json.loads(raw)
        require(original == source.get("original_batch"), f"later archive source JSON changed: {label}")
        if expected_batch is not None:
            require(original == expected_batch, f"later archive does not continue the expected residual: {label}")

        decisions = record.get("decisions", [])
        result, automatic, reviewed = desired_batch(original, decisions, record.get("recorded_on"))
        require(record.get("automatic_repairs") == automatic, f"later automatic repairs changed: {label}")
        require(record.get("review_candidates") == reviewed, f"later review evidence changed: {label}")
        expected_result = {
            "active_path": label if result["events"] else None,
            "active_events": [
                {"id": event.get("id"), "sha256": data_sha256(event)}
                for event in result["events"]
            ],
        }
        require(record.get("result") == expected_result, f"later archive result changed: {label}")
        if result["events"]:
            require(path.is_file() and json.loads(path.read_text()) == result, f"later active residual changed: {label}")
        else:
            require(not path.exists(), f"later archive says removed but batch is active: {label}")
        return [str(archive.relative_to(ROOT))]

    # Four residuals were explicitly repaired between the first and second
    # duplicate materializations. Follow that byte-for-byte transition.
    for repair_manifest in sorted(VALIDATION_MANIFESTS.glob("residual-repair-*.json")):
        repairs = json.loads(repair_manifest.read_text())
        for repair in repairs.get("batches", []):
            if repair.get("path") != label or repair.get("original_sha256") != expected_hash:
                continue
            original_raw = repair.get("original_text", "").encode("utf-8")
            corrected_raw = repair.get("corrected_text", "").encode("utf-8")
            require(hashlib.sha256(original_raw).hexdigest() == expected_hash, f"residual repair source hash changed: {label}")
            if expected_batch is not None:
                require(json.loads(original_raw) == expected_batch, f"residual repair source JSON changed: {label}")
            corrected_hash = repair.get("corrected_sha256")
            require(hashlib.sha256(corrected_raw).hexdigest() == corrected_hash, f"residual repair result hash changed: {label}")
            return [str(repair_manifest.relative_to(ROOT)), *verify_stage_or_later(label, corrected_hash, json.loads(corrected_raw))]

    # A later duplicate decision may consume a repaired historical stage before
    # the validation-remediation archive takes over.
    duplicate_archive = ARCHIVE / f"{expected_hash}-{path.name}"
    if duplicate_archive.is_file():
        record = json.loads(duplicate_archive.read_text())
        source = record.get("source", {})
        raw = source.get("original_text", "").encode("utf-8")
        require(source.get("path") == label, f"later duplicate source path changed: {label}")
        require(hashlib.sha256(raw).hexdigest() == expected_hash == source.get("sha256"), f"later duplicate source hash changed: {label}")
        original = json.loads(raw)
        require(original == source.get("original_batch"), f"later duplicate source JSON changed: {label}")
        if expected_batch is not None:
            require(original == expected_batch, f"later duplicate does not continue the expected stage: {label}")
        indexes = {item["decision"]["event_index"] for item in record.get("duplicates", [])}
        require(len(indexes) == len(record.get("duplicates", [])), f"later duplicate indexes changed: {label}")
        for item in record.get("duplicates", []):
            index = item["decision"]["event_index"]
            event = original["events"][index]
            require(item.get("original_event") == event, f"later duplicate event changed: {label}:{index}")
            require(item.get("original_event_sha256") == data_digest(event), f"later duplicate event hash changed: {label}:{index}")
        residual = dict(original, events=[event for index, event in enumerate(original["events"]) if index not in indexes])
        chain = [str(duplicate_archive.relative_to(ROOT))]
        if not residual["events"]:
            require(not path.exists(), f"fully archived later duplicate remains active: {label}")
            return chain
        residual_raw = (json.dumps(residual, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        return [*chain, *verify_stage_or_later(label, hashlib.sha256(residual_raw).hexdigest(), residual)]

    raise ValueError(f"historical stage is neither active nor archived: {label}")


def verify_later_remediation():
    manifests = sorted(VALIDATION_MANIFESTS.glob("intake-validation-remediation-*.json"))
    manifests = [path for path in manifests if not path.name.endswith("-validation.json")]
    require(len(manifests) == 1, "expected exactly one validation-remediation manifest")
    manifest = json.loads(manifests[0].read_text())
    return {
        "manifest": str(manifests[0].relative_to(ROOT)),
        "report": verify_validation_remediation(manifest),
    }


def verify(manifest, verification_mode=PUBLISHED):
    if verification_mode == TEMPORARY_MATERIALIZATION:
        return {
            "verification_mode": verification_mode,
            "published": verify_published_at_head(
                ROOT,
                "scripts/verify_radar_duplicate_resolution.py",
                ["radar/inbox/review/duplicate-resolution-2026-09-11.json"],
            ),
            "temporary_materialization": verify_temporary_materialization(ROOT),
        }
    if verification_mode != PUBLISHED:
        raise ValueError(f"unsupported verification mode: {verification_mode}")
    ancestry = require_base_ancestor(ROOT, manifest.get("base_commit"))
    for label, expected in manifest["protected_files"].items():
        if label in HISTORICAL_PROTECTED_SHA256:
            require(expected == HISTORICAL_PROTECTED_SHA256[label], f"unexpected historical protected identity: {label}")
        else:
            require(digest(ROOT / label) == expected, f"protected file changed: {label}")
    selected = {}
    for decision in manifest["decisions"]:
        if (decision["action"] == "archive_duplicate" and decision["approval"] in {"approved", "permitted"}
                and decision.get("materialization", {}).get("status") != "blocked_residual_validation"):
            selected.setdefault(decision["path"], []).append(decision)
    canonical = json.loads((ROOT / "radar/events.json").read_text())
    validate_canonical(canonical)
    originals = manifest["active_files_before"]
    later_archives = []
    for label, expected in originals.items():
        if label not in selected:
            later_archives.extend(verify_stage_or_later(label, expected))
    current_paths = {str(p.relative_to(ROOT)) for p in ACTIVE.glob("*.json")}
    require(not current_paths - set(originals), "unexpected active batches were introduced")
    report = {
        "verification_mode": verification_mode,
        "ancestry": ancestry,
        "protected_files": list(manifest["protected_files"]),
        "archived_candidates": [],
        "split_batches": [],
        "removed_active_batches": [],
        "residual_candidates_validated": 0,
    }
    for label, decisions in selected.items():
        path = ROOT / label
        archive = ARCHIVE / f"{decisions[0]['sha256']}-{path.name}"
        record = json.loads(archive.read_text())
        source = record["source"]
        raw = source["original_text"].encode("utf-8")
        require(hashlib.sha256(raw).hexdigest() == originals[label] == source["sha256"], f"original bytes not preserved: {label}")
        batch = json.loads(raw)
        require(batch == source["original_batch"], f"original JSON mismatch: {label}")
        require(source["path"] == label, f"original path mismatch: {label}")
        indexes = {d["event_index"] for d in decisions}
        expected_duplicates = [e for i, e in enumerate(batch["events"]) if i in indexes]
        require([d["original_event"] for d in record["duplicates"]] == expected_duplicates, f"archived candidate mismatch: {label}")
        require(len(record["duplicates"]) == len(decisions), f"archive count mismatch: {label}")
        by_id = {d["candidate_event_id"]: d for d in decisions}
        for duplicate in record["duplicates"]:
            event = duplicate["original_event"]
            decision = by_id[event["id"]]
            require(duplicate["decision"] == decision, f"decision changed: {event['id']}")
            require(duplicate["canonical_event_id"] == decision["canonical_event_id"], f"canonical mismatch: {event['id']}")
            require(data_digest(event) == duplicate["original_event_sha256"] == decision["candidate_event_sha256"], f"event hash mismatch: {event['id']}")
            report["archived_candidates"].append({"id": event["id"], "canonical": decision["canonical_event_id"], "archive": str(archive.relative_to(ROOT))})
        residual = [e for i, e in enumerate(batch["events"]) if i not in indexes]
        if residual:
            expected = dict(batch, events=residual)
            validate_batch(expected, path, ACTIVE)
            for event in residual:
                validate_batch(dict(batch, events=[event]), path, ACTIVE)
                normalized, _changes = normalize(deepcopy(event))
                validate_canonical({"schema_version": 3, "events": [normalized]})
                report["residual_candidates_validated"] += 1
            expected_raw = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            later_archives.extend(verify_stage_or_later(label, hashlib.sha256(expected_raw).hexdigest(), expected))
            report["split_batches"].append({"path": label, "residual": [{"id": e["id"], "sha256": data_digest(e)} for e in residual]})
        else:
            require(not path.exists(), f"fully archived batch remains active: {label}")
            report["removed_active_batches"].append(label)
    after = plan(ACTIVE, None)
    if later_archives:
        later_remediation = verify_later_remediation()
        require(after["summary"] == later_remediation["report"]["intake_plan"], "current plan disagrees with later remediation")
        report["later_remediation"] = later_remediation
    else:
        require(after["summary"] == manifest["expected_active_after"], "unexpected post-materialization plan")
    reviews = [d["candidate_event_id"] for d in after["decisions"] if d["action"] == "review"]
    require(reviews == ["eddie-palmieri-2019-user-confirmed"], "historical review changed")
    report["active_summary"] = after["summary"]
    report["reviews"] = reviews
    report["unchanged_unselected_batches"] = len(originals) - len(selected)
    report["later_validation_archives"] = sorted(set(later_archives))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--verification-mode", choices=VERIFICATION_MODES, default=PUBLISHED)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(json.loads(args.manifest.read_text()), args.verification_mode), ensure_ascii=False, indent=2))
    except ValueError as error:
        parser.exit(2, f"verify RADAR duplicates: {error}\n")


if __name__ == "__main__":
    main()
