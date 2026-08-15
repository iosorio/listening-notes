# RADAR enrichment backfill

This workflow adds verified links and editorial listening recommendations to
events that already exist in `radar/events.json`. It is deliberately separate
from new-event creation. The canonical JSON remains the only production event
dataset; inbox files are auditable handoffs.

## Lifecycle and responsibility

```text
editorial research
→ radar/inbox/research/
→ deterministic validation and safe diff
→ explicit human or interactive Codex review
→ radar/inbox/curated/enrichment/
→ deterministic merge and full validation
→ radar/inbox/processed/enrichment/
→ GitHub Pages
```

Research agents verify factual destinations and choose meaningful recordings.
Validators check structure, domains, forbidden patterns, patch scope,
consistency, conflicts, and idempotency. They cannot prove that a URL is the
authoritative page; that remains an editorial review responsibility. GitHub
Actions does not call an AI service or make editorial decisions.

## Research batch contract

```json
{
  "batch_version": 1,
  "kind": "research_event_enrichment_patches",
  "batch_id": "backfill-s-2026-08-15-001",
  "created_on": "2026-08-15",
  "events": [
    {
      "id": "existing-event-id-2026",
      "links": {
        "official_event": "https://venue.example/events/exact-event",
        "official_tickets": "https://tickets.example/events/exact-event"
      },
      "recommended_listening": [
        {
          "artist": "Artist",
          "title": "Album",
          "kind": "album",
          "apple_music_url": "https://music.apple.com/us/album/album/123"
        }
      ],
      "enrichment": {"status": "complete", "missing": []},
      "sources": [
        {
          "publisher": "Official venue",
          "url": "https://venue.example/events/exact-event",
          "checked_on": "2026-08-15"
        }
      ]
    }
  ]
}
```

Every patch requires an existing stable `id` and an `enrichment` declaration.
It may contain only `links`, `recommended_listening`, `enrichment`, `sources`,
optional `provenance`, and optional `replacement_reason`. Any correction to
dates, venue, lineup, status, attendance, priority, prices, geography, or
editorial copy must use a separate factual/editorial review.

Official links must be exact HTTPS event or authorized purchase/reservation
destinations. Apple Music links must use `music.apple.com` and an exact
`/album/`, `/song/`, or `/playlist/` path. Search results, artist profiles,
generic homepages, aggregators, private Gmail URLs, email addresses, and
fabricated destinations are prohibited.

`complete` means both official links and at least one exact Apple Music URL are
present after the patch. `pending` means an expected destination is not yet
verifiable. `unavailable` means research reasonably established that it does
not exist or does not apply. Pending and unavailable patches list every missing
component and explain it in `note`; URLs are never invented for completeness.

## Explicit promotion

Run the read-only validator, inspect its reported changes and conflicts, and
then promote the exact approved file:

```sh
python3 scripts/validate_research_enrichment.py radar/inbox/research/BATCH.json
python3 scripts/promote_research_enrichment.py \
  radar/inbox/research/BATCH.json \
  --approved-by "Reviewer name" \
  --dry-run
python3 scripts/promote_research_enrichment.py \
  radar/inbox/research/BATCH.json \
  --approved-by "Reviewer name"
```

If review finds an error, do not promote it. Produce a corrected research batch
with a new batch ID so the original handoff remains durable. Promotion copies
the approved patches into a `curated_event_enrichment_patches` envelope and
records the original path and SHA-256. The curated merger rejects altered or
untraceable promotions.

## Conservative merge semantics

Omitted fields are no-ops. Empty arrays never delete canonical data. Links,
recommendations, sources, and provenance are additive by default.

A different non-null official URL or a different exact Apple Music URL for the
same artist/title/kind is a conflict. A deliberate replacement requires a
non-empty `replacement_reason` and a source whose URL is the new destination.
The reason remains preserved in the processed curated batch. Unrelated canonical
fields are never modified.

Sources are deduplicated by their full normalized JSON record so verifications
with materially different dates or notes remain historical evidence. Apple
Music recommendations are deduplicated by exact URL and then by normalized
artist/title/kind. Provenance backfill records are appended under
`provenance.enrichment_history` and deduplicated exactly. Reapplying an archived
batch produces a no-op instead of duplicate data.

## Automation and credentials

The ingest workflow routes direct `curated/*.json` creation batches to
`merge_inbox.py` and nested `curated/enrichment/*.json` patches to
`merge_enrichment_patches.py`. Both merges, canonical validation, tests,
archiving, and the resulting commit happen in one serial job. A bot-actor guard
and GitHub's `GITHUB_TOKEN` recursion protection prevent workflow loops.

No repository secret is required. Do not create an `OPENAI_API_KEY`, personal
access token, Apple Music credential, or deploy key. The job requests only
`contents: write` and uses its automatically generated `GITHUB_TOKEN`. Keep the
repository-wide Actions default at read access and keep “Allow GitHub Actions
to create and approve pull requests” disabled. GitHub Pages continues to serve
`main` from the repository root without a deployment secret.
