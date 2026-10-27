---
name: slice
description: Turn an approved brief into vertical slices (cut), build each slice as one small, tested pull request (build), and close the change once the last one merges or the change is abandoned (close). Use after a brief is approved, or with "slice build <issue>" for a single self-contained change inside the existing design (tier T1).
---

# slice — small verified steps

Three modes. Log with `isv log <event> --change <id> …` (see `frame` for setup).

## cut: brief → slices

1. Split the brief into **vertical** slices: each delivers observable behaviour end to end, fits one
   pull request and one context window (aim for at most ~400 non-test lines). Order by dependency;
   put enabling refactors first.
2. Show the human the slice list: each slice's goal, acceptance checks (the brief's A-ids; every
   check belongs to a slice), dependencies, and whether it touches a **risk path** (`risk.paths` in
   `.isv/config.toml`). The human approves the list **once**. That one go-ahead covers every slice;
   do not ask again per slice unless a stop-the-line condition fires.
3. Then create one issue per slice from `isv template slice-issue` (goal, acceptance checks, out of
   scope, dependencies, risk path).
   `isv log slice.created slice=s<n> risk_path=true|false checks=<n> issue=<n>`.

## build: slice → pull request

1. **Read** the brief (T2) and the issue. Restate the acceptance checks as tests and see them fail.
   A T1 change has no `frame` step, so open it here:
   `isv log change.started --change <YYYYMMDD-slug> tier=T1 slug=<slug> issue=<n>`.
2. **Smallest change that works**, taking the first rung that fully solves it: does it need to exist →
   existing code → standard library or platform → an installed dependency → minimal new code.
   **Never cut:** validation at trust boundaries, error handling that prevents data loss, security,
   money and precision invariants, anything the brief requires. Complete every affected caller and test,
   and update the docs of any public API or contract the slice changes, in the same PR.
3. **Run the project's checks** (tests, lint, types, migrations) and keep the output.
4. **Self-check with fresh eyes:** a subagent with no history reads the diff once for bugs and for
   code that can be deleted. Apply what holds.
5. **PR body** from `isv template pr-body`. Then run locally:
   `isv check pr-body --body-file <file>` and `isv check surface --base <base> --body-file <file>`.
   New surface beyond the brief's budget is a stop-the-line, not a footnote.
6. **Open the PR** linked to the issue, then run `verify` on it.
7. **Continue** with the next unblocked slice without asking, unless a stop-the-line fires. When none
   is left, run `close` once the last PR has merged.

## close: change → record

Run when every slice of the change has merged (`gh pr view <n> --json state`) and every acceptance
check has run, or when the human abandons the change.

1. **Every check ran.** List each acceptance check with its result and evidence (test, command
   output, CI run). A check that has not run, including one that must run against a deployed
   environment, blocks the close: `isv log stop.line reason=not-executable detail=…`, make it
   runnable as a slice under the same brief (`build`), and run it.
2. **T2:** fill the brief's **Outcome** section with that list and set its status to `closed`. It
   replaces a separate summary document; ship it through the repository's normal review path.
3. Once that has merged: `isv log change.closed --change <id> outcome=shipped|abandoned
   detail=<one line>`. `shipped` means every acceptance check ran and passed.

## Stop and ask

An assumption in the brief is false, or a slice needs a different answer to a decision the human
made (`assumption-falsified`: bring a new card, never record it as agent-decided) · new surface
exceeds the brief's budget (`budget`) · the review round cap was hit (`cap`) · an acceptance check
cannot be executed (`not-executable`) · the next action is irreversible or outward-facing
(`irreversible`).
`isv log stop.line reason=<code> detail=…`.

Whenever you or the human skip or alter a step, `isv log override step=<step> by=<human|agent> reason=…`.
