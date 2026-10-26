# Changelog

Flow (METHOD.md, skills) and CLI share one version. Each entry says what changed and the
evidence that motivated it.

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
