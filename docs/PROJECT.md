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
- `radar/events.json` is the single underlying event dataset.
- `assets/` holds local editorial images.

The site is intentionally static so it can remain publishable through GitHub
Pages and usable without a framework, service, or AI platform.

The two native domains are Greater Tokyo/Kantō and the US corridor. Automated
discovery is external; it may suggest leads but never publishes them directly.

## Durable operating model

GitHub stores the project history and reviewed knowledge. Research may begin in
a chat, but source URLs, factual corrections, decisions, and editorial copy
must be recorded in this repository before they are treated as durable.

Events remain in the dataset after their date. The radar will gradually become
a personal history of live listening: upcoming plans, attended shows, notes,
setlists, photos, and reflections can accumulate on the same stable event ID.

## Change sequence

1. Discover a candidate event and verify it from primary or authoritative sources.
2. Check the canonical dataset for duplicates or material updates.
3. Record a new candidate in `radar/inbox/curated/` with sources, bilingual editorial judgment, exact official event/ticket URLs, and editorial Apple Music links where available.
4. For an existing event, record unreviewed link research in `radar/inbox/research/`, validate it, and explicitly promote the approved batch to `radar/inbox/curated/enrichment/`.
5. Let the RADAR ingest workflow route creation batches and enrichment patches to their separate deterministic mergers.
6. Validate the resulting `radar/events.json`; GitHub Pages then publishes the updated static RADAR.

Ticket prices are recorded only when explicitly verified. Discovery must not
invent prices, showtimes, lineups, source URLs, attendance status, or links.

## RADAR enrichment

Discovery research supplies verified enrichment in each curated inbox candidate;
the merge validates it before canonical ingestion. Upcoming candidates declare
`enrichment.status` as `complete`, `pending`, or `unavailable`. A complete
record has exact official event and ticket URLs plus at least one exact Apple
Music recommendation. Pending or unavailable records explicitly list missing
fields and explain why. URLs are never invented to satisfy validation.
`radar/events.json` remains the only canonical dataset.

Existing-event backfill never runs directly from unreviewed research. The
research validator produces a structural diff, a human or interactive Codex
review explicitly approves promotion, and the curated patch merger modifies
only enrichment fields. GitHub Actions performs no AI or editorial reasoning.
See `docs/RADAR_ENRICHMENT.md` for the contracts and commands.

## Current boundaries

The initial catalog is a legacy migration set. Some retained factual fields
predate this documentation and lack source links; those records are marked for
provenance backfill rather than silently treated as fully verified.
