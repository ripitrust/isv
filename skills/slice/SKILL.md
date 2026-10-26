---
name: slice
description: Turn an approved brief into vertical slices (cut), then build each slice as one small, tested pull request (build). Use after a brief is approved, or with "slice build <issue>" for a single self-contained change inside the existing design (tier T1).
---

# slice — small verified steps

Two modes. Log with `isv log <event> --change <id> …` (see `frame` for setup).

## cut: brief → slices

1. Split the brief into **vertical** slices: each delivers observable behaviour end to end, fits one
   pull request and one context window (aim for at most ~400 non-test lines). Order by dependency;
   put enabling refactors first.
2. For each slice create an issue from `isv template slice-issue`: goal, acceptance checks (the brief's
   A-ids), out of scope, dependencies, and whether it touches a **risk path** (`risk.paths` in
   `.isv/config.toml`). `isv log slice.created slice=s<n> risk_path=true|false checks=<n> issue=<n>`.
3. The human approves the slice list **once**. That one go-ahead covers every slice; do not ask again
   per slice unless a stop-the-line condition fires.

## build: slice → pull request

1. **Read** the brief and the issue. Restate the acceptance checks as tests and see them fail.
2. **Smallest change that works**, taking the first rung that fully solves it: does it need to exist →
   existing code → standard library or platform → an installed dependency → minimal new code.
   **Never cut:** validation at trust boundaries, error handling that prevents data loss, security,
   money and precision invariants, anything the brief requires. Complete every affected caller and test.
3. **Run the project's checks** (tests, lint, types, migrations) and keep the output.
4. **Self-check with fresh eyes:** a subagent with no history reads the diff once for bugs and for
   code that can be deleted. Apply what holds.
5. **PR body** from `isv template pr-body`. Then run locally:
   `isv check pr-body --body-file <file>` and `isv check surface --base <base> --body-file <file>`.
   New surface beyond the brief's budget is a stop-the-line, not a footnote.
6. **Open the PR** linked to the issue, then run `verify` on it.
7. **Continue** with the next unblocked slice without asking, unless a stop-the-line fires.

## Stop and ask

An assumption in the brief is false (`assumption-falsified`) · new surface exceeds the brief's budget
(`budget`) · the review round cap was hit (`cap`) · an acceptance check cannot be executed
(`not-executable`) · the next action is irreversible or outward-facing (`irreversible`).
`isv log stop.line reason=<code> detail=…`.

Whenever you or the human skip or alter a step, `isv log override step=<step> by=<human|agent> reason=…`.
