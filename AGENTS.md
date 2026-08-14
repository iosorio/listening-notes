# Listening Notes — Agent Guide

## Source of truth

This repository is the permanent, portable system of record for Listening Notes.
Chats and AI tools are research and editorial workspaces, never authoritative
storage. Record decisions, source links, verification dates, and editorial text
in the repository so a future human or tool can continue the work independently.

## Editorial and data rules

- Do not delete an historical concert record merely because its date has passed.
  Preserve it and update its status or archive material when appropriate.
- Keep factual information separate from editorial judgment. Facts need sources;
  priorities, recommendations, and travel verdicts are explicitly editorial.
- Preserve provenance. Never turn an unverified lead, remembered detail, or
  resale listing into a fact.
- Clearly distinguish official/face-value ticket information from resale or
  secondary-market information. Never present resale prices as face value.
- A ticket price is unknown until its source and verification date are recorded.
  Use `null` rather than guessing.
- English and Spanish are first-class languages. Write each editorial field for
  its audience; do not rely on literal translation.
- Listening Notes has two native geographic domains: Greater Tokyo / Kantō and
  the Washington–Baltimore–Philadelphia–Newark–New York corridor. Do not frame
  Tokyo as a distant exception to a US-only radar.
- Tsuyoshi Yamamoto is the current narrative guide, not the project’s ultimate
  destination or musical authority. His unfinished Tokyo search gives RADAR a
  direction; editorial judgment still determines inclusion. Preserve the
  documented priority treatment for a verified Yamamoto appearance.
- Attendance classification and attendance evidence are separate. A direct user
  confirmation is sufficient for `attended`; a purchase email alone is not.

## Technical rules

- Prefer static HTML, CSS, JavaScript, and JSON. Introduce a framework or
  dependency only when its continuing value clearly exceeds its maintenance cost.
- Keep data human-readable, Git-friendly, and validatable with the standard
  library where possible.
- Preserve working URLs while migrating. Make changes in small, reversible
  commits and validate the site and event data before committing.
- Do not publish, deploy, or alter repository settings without explicit user
  authorization.

See `docs/PROJECT.md`, `docs/EDITORIAL.md`, `docs/PRIORITIES.md`, and
`docs/DATA_MODEL.md` before changing the site or adding events. Also read
`docs/DOMAINS.md` and `docs/ATTENDANCE.md` for geographic or archive work.
