# Event Data Model

`radar/events.json` is the only event dataset. It is JSON, formatted with one
object per event where practical, and is designed to stay readable in Git.

## Root shape

```json
{
  "schema_version": 3,
  "events": []
}
```

## Event shape

```json
{
  "id": "artist-project-2026",
  "artist": "Artist",
  "subtitle": null,
  "dates": {"start": "YYYY-MM-DD", "end": null},
  "showtimes": [],
  "venue": {"id": "venue-city", "name": "Venue", "city": "City", "state": "State", "country": "US"},
  "geographic_domain": "us_corridor",
  "geography": "Local",
  "priority": "A+",
  "category": "Masters",
  "genres": ["Jazz"],
  "musical_axes": [],
  "status": "considering",
  "lineup": [],
  "factual_description": null,
  "editorial": {
    "en": {"why_it_matters": "…", "trip_verdict": "…"},
    "es": {"why_it_matters": "…", "trip_verdict": "…"}
  },
  "links": {"official_event": null, "official_tickets": null},
  "tickets": {
    "currency": "USD",
    "official": {"minimum": null, "maximum": null, "source_url": null, "checked_on": null},
    "resale": {"minimum": null, "maximum": null, "url": null, "checked_on": null}
  },
  "sources": [],
  "recommended_listening": [],
  "attendance": {"status": null, "evidence": [], "notes": null, "setlist": null, "photo_paths": []}
}
```

## Field rules

- `id` is stable and never reused. It normally ends in a year and may end in a
  full ISO date when that is needed to distinguish a historical/show record.
  Correct a record in place; do not make a new ID solely because copy, pricing,
  or a URL changed.
- `dates.start` is required; `dates.end` is optional and inclusive.
- `showtimes` is an array because multi-night engagements can have distinct
  times. Use ISO-like local time strings such as `19:30` only when verified.
- `status` is one of `considering`, `going`, `attended`, or `passed`. Priority
  may be `null` only for a normalized historical archive record whose original
  evidence does not support an editorial rating.
- `geographic_domain` is `tokyo_kanto`, `us_corridor`, `north_america`, or
  `rest_of_world`. `venue.id` is stable and resolves to one canonical identity
  in `radar/venue_identities.json`: name, factual city/state/country, and
  `radar_area`. The same venue must never be reintroduced under an alternate
  ID, display name, or city spelling. District of Columbia venues use
  `Washington, DC`.
- `radar_area` is a controlled editorial browsing group on the canonical venue,
  not an event field or a correction to `venue.city`. Its values are `dmv`,
  `baltimore`, `philadelphia`, `newark`, `new_york`, `tokyo`, `kanagawa`,
  `saitama`, `new_jersey`, and `unassigned`. The registry validator rejects a
  missing or unknown value. A new venue can use `unassigned` while its scene is
  reviewed; RADAR then exposes it under a visible “Area to review” / “Zona por
  revisar” filter. A missing venue ID at runtime also goes there rather than
  removing its events. Register the venue and choose an area before publication.
  Every event at a venue inherits the same group through `venue.id`.
- `radar_area` does not derive `geographic_domain`, `geography`, priority, or
  bilingual `trip_verdict`. Columbia, MD belongs to the DMV browsing scene
  while its existing `Regional` geography and travel judgment remain intact.
- `factual_description` is source-backed; set it to `null` when not verified.
- `editorial` has native English and Spanish copy. Do not put display-language
  lookup tables in application JavaScript.
- `sources` records provenance as `{ "url", "publisher", "checked_on", "note" }`.
  Legacy source objects remain preserved; new enrichment patches use this
  documented shape.
- All ticket prices are numeric face values or resale values in `currency`.
  Unknown prices are `null`; never infer them from a resale listing.
  Supported explicit currency codes are `USD` and `JPY`; never infer a currency
  from the venue's country or convert amounts to satisfy validation. A verified
  JPY amount remains in yen, with its official source and verification date.
  For example, ALFIE's September 12, 2026 Sora Ichikawa show has a tax-inclusive
  JPY 5,500 music charge in its [official schedule](https://alfie.tokyo/schedule/202609.html),
  verified September 11. Required food/drink orders are separate, not an inferred
  part of the stored charge. A venue's telephone reservation policy does not
  supply an exact online `official_tickets` destination.
- `recommended_listening` contains objects with `artist`, `title`, `kind`
  (`album`, `track`, or `playlist`), and optional `apple_music_url`.
- `enrichment` declares `complete`, `pending`, or `unavailable`. `complete`
  requires exact official event and ticket destinations plus at least one exact
  Apple Music album, song, or playlist URL. The other states list every missing
  component and include an explanatory note.
- `provenance` remains an object. Enrichment patches preserve its existing
  `status` and `note`; optional backfill records are appended idempotently under
  `provenance.enrichment_history`.
- `attendance` preserves personal material after a show; photo paths refer to
  committed local assets only. Its `status` and evidence records follow
  `docs/ATTENDANCE.md`; they do not infer attendance from a ticket email.

## Migration policy

Legacy records may retain source-less editorial copy during migration, but must
use empty `sources`, null URLs/prices, and a provenance-backfill note. New or
factually changed records require source entries before publication.
