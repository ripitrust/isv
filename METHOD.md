# ISV — Intent → Slice → Verify

Version 0.1.1. A development flow for one human working with coding agents. It aims for
code that is correct, small and understood by the person who owns it, with as few human
interruptions as that allows.

```
  intent ──frame──▶ brief ──slice cut──▶ issues ──slice build──▶ PR ──verify──▶ merge
           (T2 only)  ▲ human approves      ▲ human approves        verdict:
                      │ once                │ once                  MERGE / NEEDS-HUMAN / RETHINK
```

## Principles

1. **Size the process to the change.** Most changes need no design document.
2. **The human decides; the agent does the rest.** Humans rule on product rules and
   decisions that are hard to undo. Agents answer factual questions and make reversible choices,
   and record them.
3. **Understanding is a deliverable.** A decision the human cannot explain back has not been made.
4. **Every addition must earn its place.** New tables, flags, services and dependencies are
   declared up front and checked mechanically.
5. **Review is independent and bounded.** Fresh context, evidence for every finding, a hard round cap.
6. **Measure, then change the flow.** Every step leaves a metadata event; retros change at most
   three things.

## Tiers

| Tier | What | Flow |
|---|---|---|
| T0 patch | Bug fix, copy, config value, dependency bump; no new behaviour; under `tiers.t0_max_changed_lines` | change → `verify` |
| T1 slice | New behaviour inside the existing design | `slice build` → `verify` → `slice close` |
| T2 design | New subsystem, data model, public or cross-service contract, money or security rule, irreversible step | `frame` → `slice cut` → `slice build` × n → `verify` × n → `slice close` |

Classify by the change, not by who asks. When unsure, run `frame`: its first step only tiers.

## Human touchpoints

1. Framing: rule on the decisions `frame` surfaces (target: 3–5 per change, one at a time).
2. Approve the brief once.
3. Approve the slice list once.
4. Approve merges whose verdict is NEEDS-HUMAN (changes touching a configured risk path).
5. Release.

Everything else proceeds without asking, unless a stop-the-line condition fires.

## Decisions

| Kind | Who decides | How it is shown |
|---|---|---|
| product / money rule | human | business terms |
| one-way technical door | human | by consequence |
| reversible technical choice | agent | recorded as agent-decided |

Each human decision is a decision card (at most 12 lines) with a check question. Outcomes:
*ruled* (the human explained it back), *adopted* (the human picked without engaging; recorded
honestly), *agent-decided*.

## The brief

One file per T2 change, at most `brief.max_lines` lines, written from `isv template brief`.
It opens with five plain sentences anyone can read. It holds decisions, a **surface budget**
(every new thing and why an existing one cannot do it) and **executable acceptance checks**.
Before approval, a fresh-context reviewer makes one **necessity pass**. It may only remove,
question or flag missing checks; it may not add mechanisms. When the last slice merges or the
change is abandoned, `slice close` sets the brief to `closed` and fills its Outcome section, which
replaces a separate summary document.

## Review

A PR that changes a public API or contract updates its docs in the same PR.
At most `review.max_rounds` rounds. From round 2, the reviewer sees only the new diff and still-open
IMPORTANT findings. Each finding needs file:line or a failing case and is IMPORTANT, NIT (capped)
or PRE-EXISTING. Verdicts:

- **MERGE**: nothing IMPORTANT open, no risk path touched.
- **NEEDS-HUMAN**: a risk path is touched. The human gets a briefing of at most 15 lines.
- **RETHINK**: the cap was reached with an IMPORTANT finding still open. The approach goes back
  to the human.

## Stop the line

The agent stops and asks when:

- an assumption turns out false;
- new surface exceeds the budget;
- the review cap is hit;
- an acceptance check cannot be executed;
- the next action is irreversible or outward-facing.

## Comprehension

- `frame` opens with a current-state primer generated from the code.
- Designs must pass the explainability test: five sentences and one diagram. When a design fails,
  the design gets simpler, not the wording.
- The `explain` skill answers "I'm lost" one level at a time, grounded in the code.

## Measurement

`isv log` records metadata events (no code, no prompts, no secrets) to a local, hash-chained,
per-change log. `isv report` turns the log into the flow's health metrics:

- human decisions per change and teach-back pass rate;
- explain requests per change;
- review rounds and reviewer precision;
- the share of findings that remove code;
- verdicts, stop-lines and overrides.

`isv note` records friction in one line.

**Retro** after each T2 change and monthly. Change at most three things, bump this document's
version, and record why in CHANGELOG.md.

## Configuration

Project specifics live in `.isv/config.toml` (`isv init`): docs directory, limits, risk paths, required
PR sections, surface detectors. The skills and this method stay project-agnostic.
