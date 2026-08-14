# Listening Notes

Listening Notes is a personal, bilingual music publication and knowledge base.
Its Live Music Radar is a deliberately selective record of performances worth
protecting time, attention, or travel for—not a comprehensive event calendar.
Tsuyoshi Yamamoto and the Tokyo jazz world around him are its north star.

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

1. Verify factual event information from primary sources.
2. Record sources and ticket-price verification before presenting prices.
3. Add or update editorial judgment in both languages.
4. Validate JSON and the static pages locally.
5. Commit one coherent change with a descriptive message.

## Current boundaries

The initial catalog is a legacy migration set. Some retained factual fields
predate this documentation and lack source links; those records are marked for
provenance backfill rather than silently treated as fully verified.
