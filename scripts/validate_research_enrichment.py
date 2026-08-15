#!/usr/bin/env python3
"""Validate one untrusted RADAR enrichment research batch without writing data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .enrichment_common import CANONICAL, RESEARCH, EnrichmentError, read_json, validate_research_batch
except ImportError:  # Direct script execution.
    from enrichment_common import CANONICAL, RESEARCH, EnrichmentError, read_json, validate_research_batch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", help="one JSON file directly inside radar/inbox/research")
    args = parser.parse_args()
    path = Path(args.batch).resolve()
    if path.parent != RESEARCH.resolve():
        parser.error("batch must be directly inside radar/inbox/research")
    try:
        report = validate_research_batch(read_json(path), read_json(CANONICAL), path)
    except EnrichmentError as error:
        parser.exit(2, f"validate research enrichment: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
