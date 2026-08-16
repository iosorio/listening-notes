# Radar inbox

This directory is a handoff layer between research/editorial agents and the canonical `radar/events.json` dataset.

## Directories

- `research/`: untrusted enrichment research for existing canonical IDs. It is
  validated and reviewed but never merged directly.
- `curated/`: reviewed new-event candidates handled by `merge_inbox.py`.
- `curated/enrichment/`: explicitly reviewed patches for existing IDs, handled
  only by `merge_enrichment_patches.py`.
- `processed/` and `processed/enrichment/`: immutable Git history of successfully
  ingested creation and enrichment batches.

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

## Existing-event enrichment workflow

Research is structurally validated without writing canonical data:

```sh
python3 scripts/validate_research_enrichment.py radar/inbox/research/example.json
python3 scripts/validate_research_enrichment.py --all-unprocessed
```

The all-unprocessed check skips a preserved research artifact only when a
processed enrichment batch references the same path and batch ID and records
the exact SHA-256 and patch content. Any new, altered, or ambiguously archived
research remains subject to the full current validation contract. This lets Git
retain original research provenance without incorrectly treating an old,
already-applied patch as a proposal against the later canonical state.

After an explicit human or interactive Codex review, promote that exact batch:

```sh
python3 scripts/promote_research_enrichment.py \
  radar/inbox/research/example.json \
  --approved-by "Reviewer name" \
  --dry-run
python3 scripts/promote_research_enrichment.py \
  radar/inbox/research/example.json \
  --approved-by "Reviewer name"
```

The generated curated batch records the source path, batch ID, SHA-256, reviewer,
and review date. The original research file remains unchanged. Review the
generated diff, then test the deterministic merge locally if desired:

```sh
python3 scripts/merge_enrichment_patches.py --all --dry-run
```

Once the curated batch is committed to `main`, the ingest workflow applies it,
validates the entire canonical dataset, runs the tests, archives the batch, and
commits only the expected RADAR files. Exact contracts and replacement rules
are documented in `docs/RADAR_ENRICHMENT.md`.
