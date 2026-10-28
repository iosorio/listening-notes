# October 27 listening-link review

The four Cultural Discovery records entered canonical RADAR with empty
`recommended_listening` and explicit `pending / apple_music` declarations.
Their editorial text already named listening ideas, but the handoff did not
establish exact catalog objects. Pending was valid data, not evidence that a
recording did not exist. The merger correctly preserved those unknowns; it
does not search Apple Music or turn editorial text into invented URLs.

The corrected research batch is
`radar/inbox/research/cultural-four-apple-music-2026-10-27-002.json`.
It must be validated, explicitly promoted, and consumed by the normal
enrichment merger. Canonical events are not edited directly.

## Decisions, verified October 27

- **Minyo Crusaders:** Apple Music returned the exact *From Japan With Love*
  album, also named in Cotton Club's event discography. This is preparation
  for the band, not a promise about the January guests or setlist.
- **Kit Fitzgerald:** the exact *Peter Gordon Love of Life Orchestra* album
  is contextual listening for the composer and featured musician named by
  Roulette. It does not stand for Fitzgerald's video works or the combined
  contribution of Peter Gordon, Max Gordon and Blake Leyh.
- **Randy Coleman memorial:** the correct catalog identity is **Randolph
  Coleman**. Apple Music returned *Projection No.2, for Flute, Piano, and
  Electric Piano (1961). I*, credited to Randolph Coleman as artist and
  composer. Roulette identifies the memorial's subject as the Oberlin
  composer/mentor. This is a historical work, not announced memorial
  repertoire. The Randy Coleman rock-singer result (*Last Salutation*) is
  an unrelated namesake and is excluded.
- **Opera Praktikos:** no matching recording of the bespoke adaptation or
  its identified performers was verified. A generic Callas/Bellini recording
  is not presented as this production. Keep the missing link explicit with
  `unavailable / apple_music`; reconsider if a suitable exact release is
  established. This is a documented no-match in this review, not a claim
  about the entire world's catalog.

The research batch preserves exact API-returned artist/title/URL strings,
verification date, primary presenter URLs, reasons and identity exclusions.
Unknown ticket inventory, existing prices, priorities, attendance, discovery
times and ingestion timestamps are unchanged.

## Superseded unpublished review

The first draft proposed a generic Bellini reference and two recordings of
memorial contributors. Before publication, a more precise composer match and
the production-specific identity review superseded those choices. Its research
and generated curated envelope are preserved byte-for-byte under
`radar/inbox/review/enrichment/`, with `superseded` in their filenames. They
are inactive review evidence, not processed batches or approved intake.
Only batch `-002` is eligible for promotion and ingestion.

## Continuing handling

`scripts/audit_enrichment.py` and the validation workflow expose upcoming
listening omissions as a review queue. The interface labels missing links and
shows the queue count in the technical area. The public recommendation links
name the actual recording artist/title and distinguish recorded context from
live repertoire. This leaves qualified events visible while keeping research
uncertainty explicit.
