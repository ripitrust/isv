# Changelog

Flow (METHOD.md, skills) and CLI share one version. Each entry says what changed and the
evidence that motivated it.

## 0.1.1 — 2026-10-26

- slice: new `close` mode. When the last slice merges, or the change is abandoned (`frame`
  routes there too), it fills the brief's Outcome, sets the brief to `closed` and logs
  `change.closed`. A T1 change now logs `change.started` in `build`, so it is counted.
- report: human decisions per change counts T2 changes only, since T1 changes never reach
  `frame`; 0.1.0 baselines stay comparable.
- slice build and verify: a PR that changes a public API or contract updates its docs in the
  same PR, and the reviewer checks it.
- tests: every schema event must be logged by some skill (`note` excepted).
- Evidence: during the first live `frame` run in a pilot repository, the owner asked where the
  old flow's final summary step had gone. It had no successor: no skill filled the Outcome or
  logged `change.closed`, so `isv report` could never count a closed change, and the old step's
  "update public docs on API change" rule had been dropped.

## 0.1.0 — 2026-10-26

First internal beta.

- Method: tiers T0/T1/T2, decision triage with teach-back, brief with surface budget and
  executable checks, one-pass necessity review, bounded fresh-context code review with
  MERGE / NEEDS-HUMAN / RETHINK verdicts, stop-the-line conditions.
- Skills: frame, slice, verify, explain.
- CLI: hash-chained per-change event log, report, trace, verify-log, PR checks
  (pr-body, surface, risk), templates, push guard hook.
- Motivation: review of an existing four-step flow, where design documents grew instead of
  shrinking under review, approvals were given without understanding, and reviews had no
  round cap. Baseline metrics will come from this beta.
