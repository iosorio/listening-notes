#!/usr/bin/env python3
"""Shared integrity checks for published and temporarily materialized RADAR state."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from .merge_inbox import merge
except ImportError:  # Direct script execution.
    from merge_inbox import merge


PUBLISHED = "published"
TEMPORARY_MATERIALIZATION = "temporary_materialization"
VERIFICATION_MODES = (PUBLISHED, TEMPORARY_MATERIALIZATION)


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=check
    )


def require_base_ancestor(root: Path, base_commit: object, head: str = "HEAD") -> dict[str, str]:
    """Require a recorded base to exist and be an ancestor of the selected HEAD."""
    if not isinstance(base_commit, str) or not base_commit:
        raise ValueError("manifest does not record a base_commit")
    base = git(root, "rev-parse", "--verify", f"{base_commit}^{{commit}}", check=False)
    if base.returncode:
        raise ValueError(f"recorded base commit does not exist: {base_commit}")
    resolved_base = base.stdout.strip()
    resolved_head = git(root, "rev-parse", "--verify", f"{head}^{{commit}}").stdout.strip()
    ancestry = git(root, "merge-base", "--is-ancestor", resolved_base, resolved_head, check=False)
    if ancestry.returncode == 1:
        raise ValueError(
            f"recorded base commit {resolved_base} is not an ancestor of HEAD {resolved_head}"
        )
    if ancestry.returncode:
        detail = ancestry.stderr.strip() or "git could not verify ancestry"
        raise ValueError(f"could not verify recorded base commit ancestry: {detail}")
    return {"base_commit": resolved_base, "head_commit": resolved_head}


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True
    ).stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _changed_paths(root: Path) -> set[str]:
    tracked = git(root, "diff", "--name-only", "HEAD").stdout.splitlines()
    staged = git(root, "diff", "--cached", "--name-only", "HEAD").stdout.splitlines()
    untracked = git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return {path for path in (*tracked, *staged, *untracked) if path}


def verify_temporary_materialization(root: Path) -> dict:
    """Rebuild the working-tree ingest from committed inputs and compare it exactly."""
    root = root.resolve()
    canonical_label = "radar/events.json"
    active_prefix = "radar/inbox/curated/"
    processed_prefix = "radar/inbox/processed/"
    published_canonical = _git_bytes(root, "show", f"HEAD:{canonical_label}")
    current_canonical = (root / canonical_label).read_bytes()
    active_at_head = [
        path
        for path in git(root, "ls-tree", "-r", "--name-only", "HEAD", "radar/inbox/curated").stdout.splitlines()
        if path.startswith(active_prefix)
        and "/enrichment/" not in path
        and path.endswith(".json")
    ]
    selected = [path for path in active_at_head if not (root / path).exists()]

    with TemporaryDirectory() as directory:
        temporary = Path(directory)
        canonical = temporary / canonical_label
        curated = temporary / active_prefix
        processed = temporary / processed_prefix
        canonical.parent.mkdir(parents=True, exist_ok=True)
        curated.mkdir(parents=True, exist_ok=True)
        canonical.write_bytes(published_canonical)
        sources = []
        for label in selected:
            source = _git_bytes(root, "show", f"HEAD:{label}")
            path = curated / Path(label).name
            path.write_bytes(source)
            sources.append(path)
        report = merge(sources, False, canonical, curated, processed)
        if report["conflicts"] or report["semantic_conflicts"] or report["blocked"]:
            raise ValueError(
                "temporary materialization contains rejected candidates: "
                f"conflicts={len(report['conflicts'])}, "
                f"semantic_conflicts={len(report['semantic_conflicts'])}, "
                f"blocked={len(report['blocked'])}"
            )
        expected_canonical = canonical.read_bytes()
        if current_canonical != expected_canonical:
            raise ValueError("temporary canonical does not match deterministic materialization")

        expected_changes: set[str] = set()
        if expected_canonical != published_canonical:
            expected_changes.add(canonical_label)
        for label in selected:
            expected_changes.add(label)
            destination_label = f"{processed_prefix}{Path(label).name}"
            expected_changes.add(destination_label)
            expected = (processed / Path(label).name).read_bytes()
            destination = root / destination_label
            if not destination.is_file() or destination.read_bytes() != expected:
                raise ValueError(f"processed batch does not preserve its committed source: {label}")

        actual_changes = _changed_paths(root)
        if actual_changes != expected_changes:
            unexpected = sorted(actual_changes - expected_changes)
            missing = sorted(expected_changes - actual_changes)
            raise ValueError(
                "temporary materialization changed an unauthorized path set: "
                f"unexpected={unexpected}, missing={missing}"
            )

    return {
        "source_batches": len(selected),
        "added_candidates": len(report["added"]),
        "published_canonical_sha256": _sha256(published_canonical),
        "materialized_canonical_sha256": _sha256(current_canonical),
        "changed_paths": sorted(expected_changes),
    }


def verify_published_at_head(root: Path, script: str, arguments: list[str]) -> dict:
    """Run a verifier against an isolated, clean checkout of the committed HEAD."""
    root = root.resolve()
    with TemporaryDirectory() as directory:
        checkout = Path(directory) / "published"
        cloned = subprocess.run(
            ["git", "clone", "--quiet", "--no-local", str(root), str(checkout)],
            text=True,
            capture_output=True,
        )
        if cloned.returncode:
            raise ValueError(f"could not isolate published HEAD: {cloned.stderr.strip()}")
        result = subprocess.run(
            [sys.executable, script, *arguments],
            cwd=checkout,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ValueError(f"published repository verification failed: {detail}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(f"published verifier returned invalid JSON: {error}") from error
