# Event reference (schema v1)

Each line in `.isv/log/<change>.jsonl` is one JSON object:

```json
{"actor":"agent:claude-code/opus","change":"20261026-ledger","data":{"pr":12,"rounds":2,"verdict":"MERGE"},
 "event":"verdict","prev":"<sha256>","schema":1,"seq":3,"ts":"2026-10-26T09:12:00Z"}
```

- `schema` is the line format version; keys are written in sorted order.
- `prev` is the SHA-256 of the previous line in the same file; the first line uses 64 zeros.
  `isv verify-log` checks every chain.
- Events without `--change` go to `_general.jsonl`.
- `actor` comes from `--actor`, then `$ISV_ACTOR`, then the default: `agent:unknown` for `log`
  and `human` for `note`.
- Recorded: metadata only. Text fields are single-line, at most 200 characters, and text that
  looks like a secret is refused. Ids are short, `[A-Za-z0-9._-]`.

| Event | Required | Optional |
|---|---|---|
| `change.started` | `tier` (T0, T1, T2), `slug` | `issue`, `flow` (flow version; `isv log` adds the installed one) |
| `change.closed` | `outcome` (shipped, abandoned) | `detail` |
| `tier.set` | `tier` (T0, T1, T2), `reason` | `overridden_by` (human, agent) |
| `primer.shown` | `lines` | |
| `decision.presented` | `decision`, `kind` (product, one-way, reversible) | `card_lines` |
| `decision.resolved` | `decision`, `outcome` (ruled, adopted, agent-decided) | `teachback` (pass, fail, declined, skipped) |
| `explain.requested` | `target`, `stage` (frame, slice, verify, other) | `depth` |
| `explainability.test` | `result` (pass, fail) | |
| `necessity.result` (one per brief reviewer) | `remove`, `ask`, `missing_check` | `accepted_remove`, `accepted_ask`, `accepted_missing_check`, `lens` (necessity, fidelity; absent counts as necessity), `reviewer`, `contradiction`, `accepted_contradiction` |
| `slice.created` | `slice`, `risk_path` (true, false) | `checks`, `issue` |
| `review.round` | `pr`, `round`, `reviewer` | `important`, `nit`, `pre_existing`, `removal` |
| `finding.resolved` | `pr`, `finding`, `response` (fixed, wrong, intentional, not-worth, pre-existing) | `reason` |
| `verdict` | `pr`, `verdict` (MERGE, NEEDS-HUMAN, RETHINK), `rounds` | |
| `review.skipped` | `pr`, `round` | `reason` |
| `stop.line` | `reason` (assumption-falsified, budget, cap, not-executable, irreversible) | `detail` |
| `override` | `step`, `by` (human, agent), `reason` | |
| `note` | `text` | |

Counts (`lines`, `pr`, `round`, `important`, …) are non-negative integers.

Schema changes are additive within a major version. Renaming or removing a field bumps `schema`.
