# RADAR executor operational addendum

Prepend the following instructions to the existing `Yamamoto + Listening Notes
RADAR` automation prompt. Preserve its editorial scope, priority safeguards,
and notification content. This addendum governs operational state, heartbeats,
and failure reporting; the repository remains authoritative.

---

Run one Listening Notes discovery attempt using `iosorio/listening-notes` as
the durable authority. Before research, fetch the current `main` and read
`docs/RADAR_OPERATIONS.md`, `radar/discovery/status.json`,
`radar/discovery/runs.json`, `docs/PRIORITIES.md`, `docs/EDITORIAL.md`,
`docs/DOMAINS.md`, and `radar/inbox/README.md`. Read
`docs/RADAR_ENRICHMENT.md` before proposing an existing-event update. Do not use
a remembered checkout or infer enabled state from the automation's switch.

Validate desired state. If a scheduled attempt sees `enabled=false`, skip
research and do not record a successful scan. If operational state cannot be
read or validated, report the failure instead of assuming ON. Only an explicitly
requested manual override may research while requested state is OFF, and it
must use `trigger: manual`.

For a research attempt, generate one unique run ID, record the real start time,
and serialize attempts and publication. Check both documented domains with
Yamamoto first, following the existing editorial prompt and current repository
rules. Track actual source/candidate counts and broad, non-private threads.
Keep discovery dates from the actual research; never infer them from show dates
or filenames. Publish admitted new candidates as version 2 `*-intake.json`
batches; preserve the existing enrichment review gate. Do not edit canonical
events directly and do not claim canonical ingestion until observed.

Finish EVERY research attempt with exactly one completed heartbeat, including
successful scans with zero admitted events and failed scans. Use the full run
schema in `docs/RADAR_OPERATIONS.md` and
`scripts/validate_radar_discovery.py`. Use `success` only if the intended scan
completed, `partial` for useful work with gaps, and `error` for failed research.
Record actual start/completion times, accurate counters, executor identity,
and a concise error summary for partial/error. Never label this configuration
audit, a schedule update, or a publication retry as a discovery run.

Append the record using `scripts/record_radar_run.py` when a checkout is
available, or perform the equivalent validated append through authenticated
GitHub tools. Publish the heartbeat and any reviewed intake together in one
commit based on freshly fetched `main`. Preserve every existing heartbeat
unchanged. Use normal non-force publication and verify the commit with a fresh
read. On a concurrent update, refetch and reapply the same record without
clobbering the other publisher's work. An identical existing run ID means the
publication already succeeded; never create a second run for the retry.

If research fails but GitHub writes work, publish the real partial/error
heartbeat. If GitHub publication fails, explicitly report the failure and
retain the original record for retry; never claim it was recorded. Do not put
credentials, private URLs, email addresses, or research transcripts in GitHub.

Keep successful zero-result scans silent to the user while still publishing
their heartbeat. Notify qualifying new/materially changed events as required
by the existing prompt. Report operational failures even with zero events; the
old “nothing new, do not notify” rule must not suppress a failure report.
