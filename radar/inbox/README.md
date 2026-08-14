# Radar inbox

This directory is a handoff layer between research/editorial agents and the canonical `radar/events.json` dataset.

## Directories

- `curated/`: batches already approved for canonical merge after schema validation.
- Future: `discovered/` may hold unreviewed candidates, but nothing from it should be published automatically.

## Rules

1. `radar/events.json` remains the canonical event dataset.
2. Inbox files are small, append-only handoff artifacts; they must never be treated as a second production database.
3. A merge tool must validate every candidate against the canonical schema, detect duplicate IDs/conflicts, preserve provenance, and refuse destructive overwrites by default.
4. Private Gmail URLs, email addresses, or sensitive correspondence must never be copied into the public repository. Record evidence summaries only.
5. Official ticket prices and resale prices remain distinct. Unknown values stay `null`.
6. After a successful merge, move or copy the batch to a `processed/` archive (or record equivalent processing metadata) so the same batch cannot be applied twice.
7. The merge must be deterministic and leave `events.json` valid, formatted, and reviewable in Git.

## Merge workflow

Run a review-only pass first:

```sh
python3 scripts/merge_inbox.py --batch radar/inbox/curated/example.json --dry-run
python3 scripts/merge_inbox.py --all --dry-run
```

The report lists additions, duplicate-ID conflicts, records blocked for missing
canonical metadata, and defaults applied during normalization. A blocked record
stays in `curated/`; it is not fabricated into the production dataset.

After a clean review, run the same command without `--dry-run`. The tool
validates schema version 3 before and after merging, never deletes or blindly
overwrites canonical events, formats deterministic date/ID order, and moves
successfully processed source batches to `radar/inbox/processed/`. That move
preserves the handoff artifact in Git while preventing accidental re-ingestion.
If a batch has both mergeable and incomplete candidates, the original batch is
archived and a new `-deferred` batch containing only the blocked records stays
in `curated/` until its metadata is completed.
