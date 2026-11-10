# 0004. A change keeps the flow version it started under

- **Status:** accepted (isv 0.1.8, 2026-10-27)

**Context.** During the first design-tier change, five flow releases landed while it was open: its
review records ended up in mixed formats, records were edited after merge, and a newly added review
step was never run for it.

**Decision.** `isv log change.started` records the installed version as `flow`, and the change follows
that version's rules until it closes. Releases are tagged `v<version>` so an agent can read an older
version's skills. Releases apply to changes started after them; only a fix for a defect that blocks
work may reach an open change, noted in its log.

**Rejected.** Freezing all releases while any change is open (blocks improvement across many
repositories); always following the newest skills (changes the rules under work in progress).

**Consequences.** Several versions can be in use at once, and agents may need an older tag's text.
Flow changes reach a team only as new changes start.
