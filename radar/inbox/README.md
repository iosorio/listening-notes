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
