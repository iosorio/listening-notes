# Cultural Discovery recovery — October 21, 2026

## Outcome and limits

The authenticated GitHub Contents API successfully published the recovered
Cultural Discovery intake to `main`. The existing RADAR ingest workflow then
added both candidates to canonical RADAR and archived the identical intake.
The existing Cultural Discovery automation was re-enabled without changing its
Tuesday/Friday morning schedule. This maintenance operation was not a new
discovery scan and did not create or alter a discovery heartbeat.

The precise cause of the October 20 write rejection has not been reconstructed.
Today's successful authenticated branch, file, and production writes establish
that this publication route worked on October 21; they do not establish why the
earlier attempt failed. No repository permissions, credentials, branch
protections, workflow definitions, validators, or test expectations were changed
or weakened during this recovery.

## Original unpublished artifacts

The original draft is preserved in commit
[`d1a8ec0`](https://github.com/iosorio/listening-notes/commit/d1a8ec0ed96fb6a305bdca4612bd4f155c80821c).
Its two candidate IDs and their `discovered_at` value
`2026-10-20T14:50:12.300Z` were retained in the recovery intake.

That commit also proposed run `radar-20261020T144003000Z-cultural-6f73a9`
as `success` with `events_published: 2`, although the draft did not reach
`main`. That proposed success record was deliberately not copied into the
ledger. Its preserved draft is evidence of the attempted work, not evidence of
a successful production publication. The recovery does not backdate success or
fabricate a replacement scan.

## Validation and publication evidence

1. Prepared the revised version-2 intake in branch
   `fix/cultural-discovery-recovery-20261021`, based on current production commit
   `e248e0f194c37d95f35df7d1f9775a55c64c8a8a`.
2. Rechecked the primary Promax, Wolf Trap, and official international-tour
   pages. The historical date-specific Lawson ticket URL was retained with an
   explicit October 21 HTTP 503 recheck note. No current ticket availability
   was inferred from that failed request. Unknown data and missing enrichment
   remain explicitly unknown.
3. Performed preliminary contract checks before staging. Then used the
   repository's existing `Validate static site data` workflow on draft
   [PR #6](https://github.com/iosorio/listening-notes/pull/6) to run the full
   official dry-run and tests against a complete repository checkout.
   No execution on the user's Mac Pro is claimed; this validation ran on the
   GitHub-hosted runner.
4. [Validation run 39652918787](https://github.com/iosorio/listening-notes/actions/runs/39652918787),
   job `119405631712`, executed
   `python scripts/merge_inbox.py --batch radar/inbox/curated/zelda-40th-cultural-recovery-2026-10-21-intake.json --dry-run`.
   The report admitted exactly the two intended IDs and returned empty
   `conflicts`, `semantic_conflicts`, `blocked`, and `normalization` arrays.
   Canonical events, Signal history, and discovery-state validation passed;
   all 136 repository tests passed.
5. Published the identical validated intake through the authenticated Contents
   API in commit
   [`d3bb3f3`](https://github.com/iosorio/listening-notes/commit/d3bb3f37bd6f6838090d5e5bb51b110c539a067b).
   Fresh reads confirmed the same blob SHA on the validated branch and `main`:
   `107f20d783adecd85ecc134488442b64f002ce02`.
6. [RADAR ingest run 39653157759](https://github.com/iosorio/listening-notes/actions/runs/39653157759)
   completed successfully on October 21 at approximately 18:30:45 UTC.
   The bot's canonical update is
   [`308b2d5`](https://github.com/iosorio/listening-notes/commit/308b2d5bab51b6ae347b7bc7d93c69c690840bdb).
   It adds the two intended records to the existing 314-event catalog, bringing
   it to 316 records. The original intake blob is now preserved at
   `radar/inbox/processed/zelda-40th-cultural-recovery-2026-10-21-intake.json`.
   The assistant did not directly edit `radar/events.json`.
7. The production publication's
   [validation run 39653157779](https://github.com/iosorio/listening-notes/actions/runs/39653157779)
   also completed successfully. PR #6 is a validation-only record and must not
   be merged; its intake was already published independently after validation.

## Recovered canonical records

| Event ID | Dates | Priority |
| --- | --- | --- |
| `hyrule-symphony-orchestra-zelda-40th-tokyo-2027-01-23` | January 23, 2027, 13:00 local; Tokyo Garden Theater | A+ |
| `national-symphony-orchestra-zelda-40th-wolf-trap-2027-07-30` | July 30–31, 2027, 20:00 local; Filene Center at Wolf Trap | A |

These are two event records, with the Wolf Trap record covering two nights.
The review is identified as `ChatGPT interactive editorial recovery review`,
not independent human or Codex review. Editorial admission and priority remain
separate decisions; neither event was assigned a scarcity tier.

## Schedule and telemetry

The existing `RADAR Cultural Discovery` task was re-enabled at
`2026-10-21T18:30:28.224285Z`. Its schedule remains Tuesday and Friday around
10:00 America/New_York, with flexible timing. The next scheduled opportunity
following recovery is Friday, October 23, 2026. No duplicate task was created.
The task instructions explicitly prohibit self-disabling or changing cadence
in response to errors. A rejected operation must be reported, not bypassed.

The production ledger remained unchanged throughout recovery: its blob SHA
before and after canonical ingestion was
`8342501f37cb31f96d9683a02a538d4063ce3d6d`.
The latest daily success at that verification was
`radar-20261021T121824000Z-p6m3q8v2kn`, completed at
`2026-10-21T12:20:32.369Z` by
`ChatGPT automation — Yamamoto + Listening Notes RADAR`.
Daily discovery retains its existing schedule, `every_24_hours` desired state,
and 36-hour silence threshold. Health Watch continues to distinguish the two
executor identities; a cultural scan must not mask stale daily discovery.

Publication and ingestion recovery are verified. A new scheduled Cultural
Discovery scan and its verified truthful heartbeat are still needed before
claiming that recurring cultural discovery itself is healthy. The first real
post-reactivation scan is instructed to report its actual run ID, completion
time, status, counters, and publishing evidence even if it finds no new events.
Reactivation, validation, and maintenance alone must never produce a discovery
heartbeat. Notification delivery preferences were not changed in this recovery.
