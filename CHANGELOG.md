# Changelog

Flow (METHOD.md, skills) and CLI share one version. Each entry says what changed and the
evidence that motivated it.

## 0.1.3 — 2026-10-26

- frame: the brief review is one round with two reviewers in parallel: necessity (cut, question,
  missing checks) and fidelity (contradictions with the brief's sources or itself, missed
  boundary cases). One combined triage; a second look only at new surface.
- `isv review --prompt-file F` runs `review.external_cmd`, a reviewer from another model family,
  with the prompt on stdin; exit code 3 when none is usable, so the skill falls back to a
  subagent. verify uses it for risk-path PRs.
- `necessity.result` takes optional `lens`, `reviewer` and `contradiction` fields (additive);
  `isv report` shows accepted items per lens.
- Evidence: on the first live brief, the necessity pass (10 items) and a review against the
  design doc and sibling code (6 items, 2 important) barely overlapped, and the pilot noted that
  no reviewer from another model family was reachable.

## 0.1.2 — 2026-10-26

- `isv log` accepts `k=v` fields on either side of an option. argparse without CPython
  gh-59317 (3.11, 3.12.0–3.12.6, 3.13.0) stops collecting them at the first option, so
  `isv log <event> --change <id> k=v`, the order every skill uses, failed there; every version
  failed when fields sat on both sides. Python 3.11+ stays supported.
- docs/events.md: the example line matches what `isv log` writes (`schema`, not `v`; sorted
  keys, inside `data` too), a test keeps them in step, and the tier values are listed.
- Evidence: two independent reviews of this change ran the suite on 3.11–3.14, traced the
  argparse fix to 3.12.7 and 3.13.1, and compared the doc with real log lines.

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
