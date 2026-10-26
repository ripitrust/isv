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
   conversation history, from a **different model family** when the PR touches a risk path and one is
   available. Give it the material above and this prompt:

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

5. **Verdict** — `isv log verdict pr=<n> verdict=… rounds=<r>`:
   - **MERGE**: no open IMPORTANT finding and no risk path touched → merge per the repository's rules.
   - **NEEDS-HUMAN**: a risk path is touched → write a briefing of at most 15 lines: what changes for
     users, money, data or security, in plain words; a before/after table; the checks that ran; how to
     roll back. The human approves the merge.
   - **RETHINK**: the round cap is reached with an IMPORTANT finding open → stop, and bring the
     approach question to the human (`isv log stop.line reason=cap`).

On someone else's pull request: run the same review, do not merge, and post findings only if the
human asks.
