---
name: verify
description: Independently review one pull request with a fresh-context reviewer — evidence-bound findings on two axes (does it meet the acceptance checks; is it as simple as it can be), a hard round cap, and a verdict of MERGE, NEEDS-HUMAN or RETHINK. Use at the end of every slice build, or on any pull request on request.
---

# verify — independent, bounded review

Log with `isv log <event> --change <id> …` (see `frame` for setup).

## Steps

1. **Gather:** the diff against the base, the PR body, the linked issue and brief (acceptance checks),
   the check output, and `isv check risk --base <base>`.

2. **Review with fresh context.** A reviewer that did not write the code: a subagent with no
   conversation history. When the PR touches a risk path, use a **different model family** instead:
   write the material and prompt to a file and run `isv review --prompt-file <file> > <out>` (exit
   code 3: none is usable, so use the subagent and `isv log note` why). Give the reviewer the material
   above and this prompt:

   > Review this pull request on two axes. SPEC: is every acceptance check met; is anything partial
   > (including the docs of a public API or contract it changes), wrong, or beyond scope?
   > SIMPLICITY: what could be removed, what duplicates an existing mechanism
   > (name it), what need not exist? Every finding needs a file:line or a concrete failing case — no
   > evidence, no finding. Label each IMPORTANT (breaks behaviour, data, money, security or the spec),
   > NIT (at most `review.max_nits`, then just a count), or PRE-EXISTING (not introduced here). Do not
   > ask for new mechanisms, abstractions or configuration beyond what the acceptance checks require.
   > Do not repeat findings already dismissed. An empty review is a valid answer.

   `isv log review.round pr=<n> round=<r> reviewer=<tool/model> important=<n> nit=<n> pre_existing=<n> removal=<n>`.

3. **Author triage:** answer every finding: fixed, or dismissed as wrong / intentional / not-worth /
   pre-existing, each with a one-line reason. `isv log finding.resolved pr=<n> finding=f<k> response=…`.

4. **Rounds:** at most `review.max_rounds` (default 3). From round 2, review only the new diff plus
   still-open IMPORTANT findings.

5. **Verdict** — `isv log verdict pr=<n> verdict=… rounds=<r>` (if both NEEDS-HUMAN and RETHINK apply,
   RETHINK):
   - **MERGE**: no open IMPORTANT finding and no risk path touched → merge per the repository's rules.
   - **NEEDS-HUMAN**: a risk path is touched → write a briefing of at most 15 lines: what changes for
     users, money, data or security, in plain words; a before/after table; what merging triggers (a
     deploy, a migration); the checks that ran and any that did not; how to roll back. The human
     approves the merge.
   - **RETHINK**: the round cap is reached with an IMPORTANT finding open → stop, and bring the
     approach question to the human (`isv log stop.line reason=cap`).

6. **Record it on the PR**, where the human looks, and tell the human the verdict in the
   conversation. Post one comment with `gh pr comment <n> --body-file <file>`. Its first line is
   `isv verdict: <VERDICT>`, followed by:
   - every finding from every round, one line each: round, reviewer, label, what it says with its
     file:line, and the response (fixed in <commit or PR>, or dismissed and why);
   - for NEEDS-HUMAN, the briefing; for RETHINK, the open finding and the approach question.

   If the PR merged before the review returned, still post the record, with first line
   `isv verdict: none (merged before the review returned)`; fix what holds in a follow-up PR and
   `isv log override step=verify by=human reason=…`.

   NEEDS-HUMAN and RETHINK both wait on the human, so both get the same label:

   ```
   gh label create needs-human --color D93F0B --force
   gh pr edit <n> --add-label needs-human
   ```

   On MERGE, remove it if an earlier round added it: check `gh pr view <n> --json labels`, then
   `gh pr edit <n> --remove-label needs-human`. The human lists everything waiting on them with
   `gh search prs --state open --label needs-human --author @me` (when agents open PRs under the
   human's account; otherwise scope it with `--owner <org>`).

On someone else's pull request: run the same review, do not merge, and do not label or comment
unless the human asks.
