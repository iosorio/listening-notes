#!/usr/bin/env python3
"""Read-only audit of the four authorized residual repairs and archive chain."""

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

try:
    from .merge_inbox import normalize, validate_batch, validate_canonical
    from .verify_radar_duplicate_resolution import verify as verify_archives, verify_stage_or_later, require
except ImportError:
    from merge_inbox import normalize, validate_batch, validate_canonical
    from verify_radar_duplicate_resolution import verify as verify_archives, verify_stage_or_later, require

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "radar/inbox/curated"
ALLOWED = {
    "wycliffe-gordon-welcome-to-georgia-town-jalc-new-york-2026-10-09": {"enrichment", "sources"},
    "sora-ichikawa-concept-band-jazz-house-alfie-tokyo-2026-09-12": {"enrichment", "tickets", "sources"},
    "cortex-howard-theatre-washington-dc-2026-10-06": {"enrichment"},
    "interpretations-hemingway-andonovska-howard-roulette-brooklyn-2026-12-03": {"enrichment"},
}
HISTORICAL_VERIFIER_SHA256 = {
    # This was the verifier bound into the repair manifest. Its successor adds
    # read-only traversal of the later validation archive chain.
    "scripts/verify_radar_duplicate_resolution.py": "5da1e965a8d299c76b1be17d0d972c934f7c35f284057c27927bb5ebd9aac8c7",
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify(repairs, decisions, before_archive=False):
    report = {"stage": "before_archive" if before_archive else "after_archive", "residuals": [], "batches": []}
    changed = set()
    for record in repairs["batches"]:
        label = record["path"]
        require(sha(record["original_text"]) == record["original_sha256"] == repairs["active_files_before"][label], f"original bytes changed: {label}")
        require(sha(record["corrected_text"]) == record["corrected_sha256"], f"corrected bytes changed: {label}")
        original = json.loads(record["original_text"])
        corrected = json.loads(record["corrected_text"])
        reconstructed = deepcopy(original)
        for change in record["changes"]:
            event_id = change["event_id"]
            require(event_id in ALLOWED and event_id not in changed, "unexpected/repeated repaired candidate")
            changed.add(event_id)
            event = next(e for e in reconstructed["events"] if e["id"] == event_id)
            for field in change["fields"]:
                key = field["field"]
                require(key in ALLOWED[event_id] and event[key] == field["before"], f"unauthorized field: {event_id}.{key}")
                if key == "sources":
                    require(field["after"][:len(field["before"])] == field["before"], "existing sources altered")
                if key == "tickets":
                    require(field["after"]["currency"] == field["before"]["currency"] == "JPY", "currency inferred or converted")
                    require(field["after"]["resale"] == field["before"]["resale"], "resale altered")
                event[key] = deepcopy(field["after"])
            links = event["links"]
            missing = {k for k in ("official_event", "official_tickets") if not links.get(k)}
            if not any(e.get("apple_music_url") for e in event["recommended_listening"]):
                missing.add("apple_music")
            require(set(event["enrichment"]["missing"]) == missing, f"inexact missing fields: {event_id}")
            normalized, _ = normalize(deepcopy(event))
            validate_canonical({"schema_version": 3, "events": [normalized]})
            report["residuals"].append({"id": event_id, "missing": sorted(missing), "valid": True})
        require(reconstructed == corrected, f"unrecorded edits: {label}")
        validate_batch(corrected, ROOT / label, ACTIVE)
        selected = [d for d in decisions["decisions"] if d["path"] == label]
        require(len(selected) == 1, "exactly one previously confirmed duplicate expected per batch")
        decision = selected[0]
        require(decision["pre_repair_batch_sha256"] == record["original_sha256"], "broken pre-repair link")
        require(decision["sha256"] == record["corrected_sha256"], "broken repaired hash")
        index = decision["event_index"]
        require(original["events"][index] == corrected["events"][index], "duplicate modified by repair")
        residual = dict(corrected, events=[e for i, e in enumerate(corrected["events"]) if i != index])
        validate_batch(residual, ROOT / label, ACTIVE)
        for event in residual["events"]:
            validate_batch(dict(residual, events=[event]), ROOT / label, ACTIVE)
        if before_archive:
            require((ROOT / label).read_bytes() == record["corrected_text"].encode(), f"active repair mismatch: {label}")
        report["batches"].append({"path": label, "original_sha256": record["original_sha256"], "corrected_sha256": record["corrected_sha256"], "residual_ids": [e["id"] for e in residual["events"]]})
    require(changed == set(ALLOWED), "repair coverage must be exactly four candidates")
    for label, expected in repairs["protected_files"].items():
        if label in HISTORICAL_VERIFIER_SHA256:
            require(expected == HISTORICAL_VERIFIER_SHA256[label], f"unexpected historical verifier identity: {label}")
        else:
            require(hashlib.sha256((ROOT / label).read_bytes()).hexdigest() == expected, f"protected file changed: {label}")
    target_paths = {b["path"] for b in repairs["batches"]}
    for label, expected in repairs["active_files_before"].items():
        if label not in target_paths:
            verify_stage_or_later(label, expected)
    validate_canonical(json.loads((ROOT / "radar/events.json").read_text()))
    if not before_archive:
        report["archives"] = verify_archives(decisions)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repairs", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("--before-archive", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.repairs.read_text()), json.loads(args.decisions.read_text()), args.before_archive), indent=2))


if __name__ == "__main__":
    main()
