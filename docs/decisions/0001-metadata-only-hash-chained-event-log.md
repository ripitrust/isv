# 0001. The event log is metadata only, hash-chained, one local file per change

- **Status:** accepted (isv 0.1.0, 2026-10-26)

**Context.** To improve the flow with evidence, every step must leave a record. Logs of agent work
easily collect code, prompts and secrets, and a shared log file conflicts when several agents or
worktrees write at once.

**Decision.** `isv log` appends JSON lines to one file per change under `.isv/log/` in the main
checkout. Each line carries the SHA-256 of the previous one, so edits are detectable (`isv
verify-log`). The schema accepts only short typed fields, caps free text at 200 characters and refuses
text that looks like a secret. The log is git-ignored and never sent anywhere. Facts git and GitHub
already hold (PR size, merge time) are derived at report time, not logged.

**Rejected.** Mining agent transcripts (fragile, privacy-heavy); a shared committed log (merge
conflicts, leaks); hooks as the only capture (tied to one agent tool).

**Consequences.** The schema only grows, so old logs stay readable; reading never validates fields.
Cross-repository reviews need a script that reads each machine's logs. Fixing a wrong event means
appending a correction, not editing a line.
