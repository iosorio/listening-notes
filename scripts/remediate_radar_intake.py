#!/usr/bin/env python3
"""Plan, apply, and verify deterministic validation repairs for active RADAR intake."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import subprocess
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from . import validate_events
    from .merge_inbox import merge, normalize, semantic_duplicate, validate_batch
    from .plan_radar_intake import plan as intake_plan
    from .radar_verification import (
        PUBLISHED,
        TEMPORARY_MATERIALIZATION,
        VERIFICATION_MODES,
        require_base_ancestor,
        verify_published_at_head,
        verify_temporary_materialization,
    )
except ImportError:  # Direct script execution.
    import validate_events
    from merge_inbox import merge, normalize, semantic_duplicate, validate_batch
    from plan_radar_intake import plan as intake_plan
    from radar_verification import (
        PUBLISHED,
        TEMPORARY_MATERIALIZATION,
        VERIFICATION_MODES,
        require_base_ancestor,
        verify_published_at_head,
        verify_temporary_materialization,
    )


SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = SOURCE_ROOT
ACTIVE = ROOT / "radar/inbox/curated"
CANONICAL = ROOT / "radar/events.json"
REGISTRY = ROOT / "radar/venue_identities.json"
REVIEW = ROOT / "radar/inbox/review/validation-decisions"
ENRICHMENT_FIELDS = ("official_event", "official_tickets", "apple_music")
PROTECTED_REVIEW_IDS = {"eddie-palmieri-2019-user-confirmed"}
IMPLEMENTATION_FILES = (
    Path(__file__).resolve(),
    Path(__file__).resolve().with_name("merge_inbox.py"),
    Path(__file__).resolve().with_name("plan_radar_intake.py"),
    Path(__file__).resolve().with_name("validate_events.py"),
)
HISTORICAL_SELF_SHA256 = "36cfdcaa4ef7916019baddaca08f05b56c32c98bbb0deb630a1a4c71871cd872"


class CandidateValidationError(ValueError):
    """Capture the production validator's exact message without exiting."""


class MemoryPath:
    def __init__(self, data: dict, label: str):
        self.data = data
        self.label = label

    def read_text(self) -> str:
        return json.dumps(self.data, ensure_ascii=False)

    def __str__(self) -> str:
        return self.label


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_sha256(data: object) -> str:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def fail_validation(message: str) -> None:
    raise CandidateValidationError(message)


def validate_candidate(event: dict, batch: dict, path: Path) -> list[str]:
    """Validate one candidate exactly as intake would after normalization."""
    individual = dict(batch, events=[event])
    try:
        validate_batch(individual, path, ACTIVE)
        normalized, _changes = normalize(deepcopy(event))
        original_fail = validate_events.fail
        validate_events.fail = fail_validation
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                validate_events.main(MemoryPath({"schema_version": 3, "events": [normalized]}, str(path)))
        finally:
            validate_events.fail = original_fail
    except (CandidateValidationError, ValueError, SystemExit) as error:
        return [str(error)]
    return []


def present_components(event: dict) -> dict[str, bool]:
    links = event.get("links") if isinstance(event.get("links"), dict) else {}
    recommendations = event.get("recommended_listening")
    if not isinstance(recommendations, list):
        recommendations = []
    return {
        "official_event": bool(links.get("official_event")),
        "official_tickets": bool(links.get("official_tickets")),
        "apple_music": any(
            isinstance(item, dict) and bool(item.get("apple_music_url"))
            for item in recommendations
        ),
    }


def exact_missing(event: dict) -> list[str]:
    present = present_components(event)
    return [field for field in ENRICHMENT_FIELDS if not present[field]]


def append_note(previous: object, sentence: str) -> str:
    prefix = previous.strip() if isinstance(previous, str) else ""
    return f"{prefix} {sentence}".strip()


def json_diff(before: object, after: object, prefix: str = "") -> list[dict]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes = []
        for key in sorted(set(before) | set(after)):
            field = f"{prefix}.{key}" if prefix else key
            changes.extend(json_diff(before.get(key), after.get(key), field))
        return changes
    return [{"field": prefix, "before": before, "after": after}]


def normalize_enrichment(event: dict, recorded_on: str) -> tuple[dict, list[str]]:
    """Return the only structural enrichment repair permitted by current evidence."""
    repaired = deepcopy(event)
    enrichment = repaired.get("enrichment")
    if not isinstance(enrichment, dict):
        return repaired, []
    status = enrichment.get("status")
    old_missing = enrichment.get("missing")
    old_note = enrichment.get("note")
    if old_note is not None and not isinstance(old_note, str):
        return repaired, []
    missing = exact_missing(repaired)
    nonstandard = []
    if isinstance(old_missing, list):
        nonstandard = [str(value) for value in old_missing if value not in ENRICHMENT_FIELDS]
    reasons = []

    if status not in {"complete", "pending", "unavailable"}:
        if missing:
            enrichment["status"] = "pending"
            reasons.append(f"status {status!r} normalized to pending")
        elif old_note in {None, ""} and not nonstandard:
            enrichment["status"] = "complete"
            reasons.append(f"status {status!r} normalized to complete")
        else:
            return deepcopy(event), []
    elif status == "complete" and missing:
        enrichment["status"] = "pending"
        reasons.append("complete normalized to pending because required components are absent")

    if missing:
        if old_missing != missing:
            enrichment["missing"] = missing
            reasons.append("missing recalculated from the links and Apple Music URLs already present")
    elif enrichment.get("status") == "complete":
        if old_note not in {None, ""} or nonstandard:
            return deepcopy(event), []
        if old_missing != []:
            enrichment["missing"] = []
            reasons.append("missing recalculated as empty because every required component is present")
    else:
        return deepcopy(event), []

    if nonstandard:
        reasons.append("non-standard missing labels preserved here: " + ", ".join(nonstandard))
    if not reasons:
        return deepcopy(event), []

    # A complete declaration is valid only without a note. Its normalization
    # remains fully documented by the manifest instead of inventing uncertainty.
    if enrichment.get("status") != "complete":
        explanation = (
            f"Structural normalization on {recorded_on}: " + "; ".join(reasons) + ". "
            "No URL, price, time, lineup, listening recommendation, editorial copy, "
            "priority, attendance, geography, or ID was added, removed, or inferred."
        )
        enrichment["note"] = append_note(old_note, explanation)
    return repaired, reasons


def candidate_evidence(event: dict, errors: list[str]) -> list[dict]:
    enrichment = event.get("enrichment")
    return [
        *({"kind": "validator_error", "message": error} for error in errors),
        {"kind": "present_components", **present_components(event)},
        {
            "kind": "enrichment_input",
            "status": enrichment.get("status") if isinstance(enrichment, dict) else None,
            "missing": enrichment.get("missing") if isinstance(enrichment, dict) else None,
            "note": enrichment.get("note") if isinstance(enrichment, dict) else None,
        },
    ]


def archive_path(path: Path, batch_hash: str) -> Path:
    return REVIEW / f"{batch_hash}-{path.name}"


def implementation_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(SOURCE_ROOT)): sha256_bytes(path.read_bytes())
        for path in IMPLEMENTATION_FILES
    }


def head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE_ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def build_plan(recorded_on: str) -> dict:
    date.fromisoformat(recorded_on)
    canonical_hash = sha256_bytes(CANONICAL.read_bytes())
    registry_hash = sha256_bytes(REGISTRY.read_bytes())
    decisions = []
    active_files = {}
    proposed_events: dict[tuple[str, int], dict] = {}

    for path in sorted(ACTIVE.glob("*.json")):
        raw = path.read_bytes()
        label = str(path.relative_to(ROOT))
        batch_hash = sha256_bytes(raw)
        active_files[label] = batch_hash
        batch = read_json(path)
        if batch.get("kind") != "curated_event_candidates" or not isinstance(batch.get("events"), list):
            raise ValueError(f"{label}: not a curated event-candidate batch")
        for index, event in enumerate(batch["events"]):
            if not isinstance(event, dict):
                raise ValueError(f"{label}: events[{index}] must be an object")
            event_id = event.get("id")
            errors = validate_candidate(event, batch, path)
            action = "valid"
            proposed = deepcopy(event)
            reasons: list[str] = []
            after_errors: list[str] = []
            preserve = event_id in PROTECTED_REVIEW_IDS
            if errors:
                proposed, reasons = normalize_enrichment(event, recorded_on)
                after_errors = validate_candidate(proposed, batch, path) if reasons else list(errors)
                if reasons and not after_errors:
                    action = "normalize_enrichment"
                else:
                    action = "review_validation"
                    proposed = deepcopy(event)
            decision = {
                "path": label,
                "batch_sha256": batch_hash,
                "batch_id": batch.get("batch_id"),
                "event_index": index,
                "candidate_event_id": event_id,
                "candidate_sha256": data_sha256(event),
                "errors": errors,
                "action": action,
                "proposed_diff": json_diff(event, proposed),
                "evidence": candidate_evidence(event, errors),
                "reason": (
                    "Candidate already passes individual intake validation."
                    if action == "valid" else
                    "All proposed changes are deterministic enrichment metadata derived from fields already present."
                    if action == "normalize_enrichment" else
                    "The remaining validation error requires factual or editorial judgment and cannot be repaired structurally."
                ),
                "can_remain_active": action in {"valid", "normalize_enrichment"} or preserve,
                "materialization": "preserve_active_review" if preserve else "apply",
            }
            if reasons:
                decision["normalization_reasons"] = reasons
                decision["errors_after_proposed_repair"] = after_errors
                decision["proposed_candidate_sha256"] = data_sha256(proposed)
            decisions.append(decision)
            proposed_events[(label, index)] = proposed

    # Catch collisions among candidates that are individually valid. Neither
    # side is preferred automatically; every participant goes to review.
    eligible = [d for d in decisions if d["action"] in {"valid", "normalize_enrichment"}]
    conflicts: dict[tuple[str, int], list[dict]] = {}
    normalized = {}
    for decision in eligible:
        key = (decision["path"], decision["event_index"])
        normalized[key], _changes = normalize(deepcopy(proposed_events[key]))
    for left_index, left in enumerate(eligible):
        left_key = (left["path"], left["event_index"])
        for right in eligible[left_index + 1:]:
            right_key = (right["path"], right["event_index"])
            same_id = left["candidate_event_id"] == right["candidate_event_id"]
            semantic = not same_id and semantic_duplicate(normalized[left_key], normalized[right_key])
            if not same_id and not semantic:
                continue
            kind = "duplicate_active_id" if same_id else "semantic_active_conflict"
            conflicts.setdefault(left_key, []).append({"kind": kind, "other": right["candidate_event_id"], "other_path": right["path"]})
            conflicts.setdefault(right_key, []).append({"kind": kind, "other": left["candidate_event_id"], "other_path": left["path"]})
    for decision in decisions:
        key = (decision["path"], decision["event_index"])
        if key not in conflicts:
            continue
        decision["errors"].extend(
            f"{item['kind']}: {item['other']} in {item['other_path']}" for item in conflicts[key]
        )
        decision["evidence"].extend(conflicts[key])
        decision["action"] = "review_validation"
        decision["reason"] = "Active candidates conflict with one another and require an explicit identity decision."
        decision["can_remain_active"] = False
        decision["materialization"] = "apply"
        decision["proposed_diff"] = []

    actions = ("valid", "normalize_enrichment", "correct_from_official", "review_validation")
    summary = {action: sum(item["action"] == action for item in decisions) for action in actions}
    return {
        "schema_version": 1,
        "kind": "radar_intake_validation_remediation",
        "recorded_on": recorded_on,
        "base_commit": head_commit(),
        "policy": (
            "Read-only per-candidate plan. Only exact enrichment metadata derived from existing fields may be normalized; "
            "all factual, identity, geographic, URL, listening, and editorial decisions go to review."
        ),
        "canonical": {"path": "radar/events.json", "sha256": canonical_hash},
        "venue_registry": {"path": "radar/venue_identities.json", "sha256": registry_hash},
        "implementation_files": implementation_hashes(),
        "active_files_before": active_files,
        "protected_review_ids": sorted(PROTECTED_REVIEW_IDS),
        "summary": summary,
        "decisions": decisions,
    }


def decisions_by_path(manifest: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for decision in manifest.get("decisions", []):
        grouped.setdefault(decision["path"], []).append(decision)
    return grouped


def desired_batch(batch: dict, decisions: list[dict], recorded_on: str) -> tuple[dict, list[dict], list[dict]]:
    by_index = {decision["event_index"]: decision for decision in decisions}
    if set(by_index) != set(range(len(batch["events"]))):
        raise ValueError("manifest decisions do not cover the batch exactly")
    active_events = []
    automatic = []
    reviewed = []
    for index, event in enumerate(batch["events"]):
        decision = by_index[index]
        if decision["candidate_event_id"] != event.get("id") or decision["candidate_sha256"] != data_sha256(event):
            raise ValueError(f"candidate evidence changed: {event.get('id')}")
        action = decision["action"]
        if action == "valid" or decision.get("materialization") == "preserve_active_review":
            active_events.append(deepcopy(event))
        elif action == "normalize_enrichment":
            repaired, reasons = normalize_enrichment(event, recorded_on)
            if reasons != decision.get("normalization_reasons"):
                raise ValueError(f"normalization changed since planning: {event.get('id')}")
            if data_sha256(repaired) != decision.get("proposed_candidate_sha256"):
                raise ValueError(f"proposed candidate hash changed: {event.get('id')}")
            active_events.append(repaired)
            automatic.append({"before": deepcopy(event), "after": repaired, "decision": deepcopy(decision)})
        elif action in {"review_validation", "correct_from_official"}:
            reviewed.append({"original_event": deepcopy(event), "decision": deepcopy(decision)})
        else:
            raise ValueError(f"unsupported remediation action: {action}")
    return dict(batch, events=active_events), automatic, reviewed


def preflight(manifest: dict) -> tuple[dict[str, dict], dict[str, dict], dict]:
    if manifest.get("base_commit") != head_commit():
        raise ValueError("repository base commit changed since planning")
    if manifest.get("canonical", {}).get("sha256") != sha256_bytes(CANONICAL.read_bytes()):
        raise ValueError("canonical events.json changed since planning")
    if manifest.get("venue_registry", {}).get("sha256") != sha256_bytes(REGISTRY.read_bytes()):
        raise ValueError("venue registry changed since planning")
    if manifest.get("implementation_files") != implementation_hashes():
        raise ValueError("remediation implementation changed since planning")
    current = build_plan(manifest["recorded_on"])
    if current != manifest:
        raise ValueError("active intake or deterministic plan changed since planning")
    grouped = decisions_by_path(manifest)
    desired: dict[str, dict] = {}
    archives: dict[str, dict] = {}
    for label, expected_hash in manifest["active_files_before"].items():
        path = ROOT / label
        raw = path.read_bytes()
        if sha256_bytes(raw) != expected_hash:
            raise ValueError(f"active batch changed since planning: {label}")
        batch = json.loads(raw)
        result, automatic, reviewed = desired_batch(batch, grouped[label], manifest["recorded_on"])
        desired[label] = result
        if automatic or reviewed:
            target = archive_path(path, expected_hash)
            if target.exists():
                raise ValueError(f"refusing to overwrite validation evidence: {target}")
            archives[label] = {
                "schema_version": 1,
                "kind": "radar_intake_validation_archive",
                "recorded_on": manifest["recorded_on"],
                "source": {
                    "path": label,
                    "sha256": expected_hash,
                    "original_text": raw.decode("utf-8"),
                    "original_batch": batch,
                },
                "decisions": deepcopy(grouped[label]),
                "automatic_repairs": automatic,
                "review_candidates": reviewed,
                "result": {
                    "active_path": label if result["events"] else None,
                    "active_events": [
                        {"id": event.get("id"), "sha256": data_sha256(event)} for event in result["events"]
                    ],
                },
            }

    with TemporaryDirectory() as directory:
        temporary = Path(directory) / "curated"
        temporary.mkdir()
        paths = []
        for label, batch in desired.items():
            if not batch["events"]:
                continue
            path = temporary / Path(label).name
            path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n")
            paths.append(path)
        report = merge(
            paths,
            True,
            canonical_path=CANONICAL,
            curated_dir=temporary,
            processed_dir=Path(directory) / "processed",
        )
        if report["conflicts"] or report["semantic_conflicts"]:
            raise ValueError("preflight found unresolved active candidate conflicts")
        blocked_ids = {item["id"] for item in report["blocked"]}
        if blocked_ids != PROTECTED_REVIEW_IDS:
            raise ValueError(f"unexpected blocked candidates after remediation: {sorted(blocked_ids)}")
    return desired, archives, report


def materialize(manifest: dict, apply: bool) -> dict:
    desired, archives, merge_report = preflight(manifest)
    report = {
        "dry_run": not apply,
        "automatic_repairs": sum(len(item["automatic_repairs"]) for item in archives.values()),
        "review_candidates": sum(len(item["review_candidates"]) for item in archives.values()),
        "changed_batches": len(archives),
        "active_batches_after": sum(bool(batch["events"]) for batch in desired.values()),
        "active_candidates_after": sum(len(batch["events"]) for batch in desired.values()),
        "ingestible_candidates": len(merge_report["added"]),
        "protected_reviews": sorted(PROTECTED_REVIEW_IDS),
        "archives": [str(archive_path(ROOT / label, manifest["active_files_before"][label]).relative_to(ROOT)) for label in archives],
    }
    if not apply:
        return report
    REVIEW.mkdir(parents=True, exist_ok=True)
    for label, record in archives.items():
        target = archive_path(ROOT / label, manifest["active_files_before"][label])
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    for label, batch in desired.items():
        path = ROOT / label
        original = json.loads(path.read_text())
        if batch == original:
            continue
        if batch["events"]:
            path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n")
        else:
            path.unlink()
    return report


def verify(manifest: dict, verification_mode: str = PUBLISHED) -> dict:
    if verification_mode == TEMPORARY_MATERIALIZATION:
        return {
            "verification_mode": verification_mode,
            "published": verify_published_at_head(
                ROOT,
                "scripts/remediate_radar_intake.py",
                ["--verify", "radar/inbox/review/intake-validation-remediation-2026-09-11.json"],
            ),
            "temporary_materialization": verify_temporary_materialization(ROOT),
        }
    if verification_mode != PUBLISHED:
        raise ValueError(f"unsupported verification mode: {verification_mode}")
    ancestry = require_base_ancestor(ROOT, manifest.get("base_commit"))
    if manifest.get("canonical", {}).get("sha256") != sha256_bytes(CANONICAL.read_bytes()):
        raise ValueError("canonical events.json changed")
    expected_implementation = manifest.get("implementation_files", {})
    actual_implementation = implementation_hashes()
    for label, expected in expected_implementation.items():
        if label == "scripts/remediate_radar_intake.py":
            if expected != HISTORICAL_SELF_SHA256:
                raise ValueError(f"unexpected historical remediation identity: {label}")
        elif actual_implementation.get(label) != expected:
            raise ValueError(f"remediation implementation changed: {label}")
    grouped = decisions_by_path(manifest)
    expected_paths = set()
    automatic_count = 0
    review_count = 0
    for label, original_hash in manifest["active_files_before"].items():
        decisions = grouped[label]
        changed = any(
            decision["action"] == "normalize_enrichment"
            or (decision["action"] in {"review_validation", "correct_from_official"}
                and decision.get("materialization") != "preserve_active_review")
            for decision in decisions
        )
        path = ROOT / label
        if changed:
            archive = archive_path(path, original_hash)
            record = read_json(archive)
            raw = record["source"]["original_text"].encode()
            if sha256_bytes(raw) != original_hash or json.loads(raw) != record["source"]["original_batch"]:
                raise ValueError(f"original batch is not recoverable: {label}")
            if record["decisions"] != decisions:
                raise ValueError(f"archived decisions changed: {label}")
            expected, automatic, reviewed = desired_batch(json.loads(raw), decisions, manifest["recorded_on"])
            automatic_count += len(automatic)
            review_count += len(reviewed)
        else:
            if sha256_bytes(path.read_bytes()) != original_hash:
                raise ValueError(f"unchanged active batch changed: {label}")
            expected = json.loads(path.read_text())
        if expected["events"]:
            expected_paths.add(label)
            if not path.exists() or json.loads(path.read_text()) != expected:
                raise ValueError(f"active residual does not match the plan: {label}")
        elif path.exists():
            raise ValueError(f"fully reviewed batch remains active: {label}")
    actual_paths = {str(path.relative_to(ROOT)) for path in ACTIVE.glob("*.json")}
    if actual_paths != expected_paths:
        raise ValueError("unexpected active batch set after remediation")
    report = merge(sorted(ACTIVE.glob("*.json")), True)
    if report["conflicts"] or report["semantic_conflicts"]:
        raise ValueError("post-remediation intake still has conflicts")
    blocked_ids = {item["id"] for item in report["blocked"]}
    if blocked_ids != PROTECTED_REVIEW_IDS:
        raise ValueError(f"unexpected blocked candidates after remediation: {sorted(blocked_ids)}")
    after_plan = intake_plan(ACTIVE, None)
    reviews = [item["candidate_event_id"] for item in after_plan["decisions"] if item["action"] == "review"]
    if reviews != sorted(PROTECTED_REVIEW_IDS):
        raise ValueError(f"unexpected identity reviews after remediation: {reviews}")
    return {
        "verification_mode": verification_mode,
        "ancestry": ancestry,
        "active_batches": len(actual_paths),
        "active_candidates": len(report["added"]) + len(report["blocked"]),
        "ingestible_candidates": len(report["added"]),
        "protected_reviews": reviews,
        "automatic_repairs": automatic_count,
        "review_candidates": review_count,
        "intake_plan": after_plan["summary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--dry-run", type=Path, metavar="MANIFEST")
    mode.add_argument("--apply", type=Path, metavar="MANIFEST")
    mode.add_argument("--verify", type=Path, metavar="MANIFEST")
    parser.add_argument("--recorded-on", default=date.today().isoformat())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verification-mode", choices=VERIFICATION_MODES, default=PUBLISHED)
    args = parser.parse_args()
    try:
        if args.plan:
            result = build_plan(args.recorded_on)
        elif args.dry_run:
            result = materialize(read_json(args.dry_run), False)
        elif args.apply:
            result = materialize(read_json(args.apply), True)
        else:
            result = verify(read_json(args.verify), args.verification_mode)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            if args.output.exists():
                raise ValueError(f"refusing to overwrite output: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output)
        else:
            print(output, end="")
    except ValueError as error:
        parser.exit(2, f"RADAR intake remediation: {error}\n")


if __name__ == "__main__":
    main()
