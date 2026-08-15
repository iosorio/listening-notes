# Listening Notes

Listening Notes is a personal, bilingual music publication and knowledge base.
Its Live Music Radar is a deliberately selective record of performances worth
protecting time, attention, or travel for—not a comprehensive event calendar.
Tsuyoshi Yamamoto and the Tokyo jazz world around him are its current narrative
guide: an unfinished search that gives RADAR direction without defining its
destination.

## Product shape

- `index.html` is an editorial listening feature.
- `radar/` is the bilingual live-music radar.
- `radar/events.json` is the single underlying event dataset and canonical source of truth.
- `radar/inbox/curated/` is the trusted ingestion queue for verified discoveries.
- `assets/` holds local editorial images.

The site is intentionally static so it can remain publishable through GitHub
Pages and usable without a framework, service, or AI platform.

The two native domains are Greater Tokyo/Kantō and the US corridor. Automated
discovery may publish verified qualifying discoveries into the curated inbox;
it never edits the canonical dataset directly.

## Durable operating model

GitHub stores the project history and reviewed knowledge. Research may begin in
a chat or scheduled RADAR scan, but an event is durable only after it enters the
repository. Verified automated discoveries are written as curated inbox batches.
The `RADAR ingest` GitHub Action runs `scripts/merge_inbox.py`, rejects duplicate
or incomplete candidates, validates the resulting schema, merges accepted events
into `radar/events.json`, and preserves the processed handoff for provenance.

Events remain in the dataset after their date. The radar will gradually become
a personal history of live listening: upcoming plans, attended shows, notes,
setlists, photos, and reflections can accumulate on the same stable event ID.

## Change sequence

1. Discover a candidate event.
2. Verify factual event information from primary or authoritative sources.
3. Check the canonical dataset for duplicates or material updates.
4. Record the verified candidate in `radar/inbox/curated/` with sources and bilingual editorial judgment.
5. Let the RADAR ingest workflow validate and merge it into `radar/events.json`.
6. GitHub Pages publishes the updated static RADAR.

Ticket prices are recorded only when explicitly verified. Automated discovery
must not invent prices, showtimes, lineups, source URLs, or attendance status.

## Current boundaries

The initial catalog is a legacy migration set. Some retained factual fields
predate this documentation and lack source links; those records are marked for
provenance backfill rather than silently treated as fully verified.
