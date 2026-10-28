"""Replay reviewed enrichment with the same provenance checks as live ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

try:
    from .enrichment_common import research_path_from_review
    from .merge_enrichment_patches import merge
except ImportError:
    from enrichment_common import research_path_from_review
    from merge_enrichment_patches import merge


def replay_reviewed_enrichment(
    batches: list[tuple[str, bytes]], canonical: Path, root: Path,
    read_research: Callable[[str], bytes],
) -> list[dict]:
    """Validate preserved research and apply each batch in its recorded order.

    The caller supplies committed inputs or history-bound processed inputs.
    No relaxed patch application or projected field comparison is used here.
    """
    root = root.resolve()
    canonical = canonical.resolve()
    curated = root / "radar/inbox/curated/enrichment"
    processed = root / "radar/inbox/processed/enrichment"
    research = root / "radar/inbox/research"
    curated.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, raw in batches:
        if Path(name).name != name or not name.endswith(".json"):
            raise ValueError("enrichment batch must have a direct JSON filename")
        batch = json.loads(raw)
        target = research_path_from_review(batch.get("review", {}), root, research)
        target.write_bytes(read_research(str(target.relative_to(root))))
        path = curated / name
        path.write_bytes(raw)
        reports.append(merge([path], False, canonical, processed, root, research))
    return reports
