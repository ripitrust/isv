---
name: frame
description: Frame a significant change before any code is written. Re-teach the current system, ask the human only for real decisions, propose the first design yourself, test it for simplicity and necessity, and produce one short brief with executable acceptance checks. Use when starting a new subsystem, data model, public or cross-service contract, money or security rule, or anything hard to undo — or when unsure which tier a change is.
---

# frame — intent before code

**Input:** an idea, issue or requirement. **Output:** an approved brief at
`<docs_dir>/<YYYY-MM-DD>-<slug>.md` (see `.isv/config.toml`), then hand-off to `slice`.

**Never in this skill:** production code. Questions the code can answer (answer them yourself).
More than one decision on screen at a time.

**Language:** concrete scenario before abstraction; define every term at first use; one analogy for
any new concept; no sentence the decider has to read twice.

Record each step with `isv log <event> --change <YYYYMMDD-slug> k=v ...` (set `ISV_ACTOR` to
`agent:<tool>/<model>` once per session). If `isv` is missing, say so and continue without logging.

**Version:** a change runs on the flow version it started under: `flow` on its `change.started`
(`isv trace <id>`); a change without one started before 0.1.8 and runs on 0.1.7. If that is older
than the installed skills, follow that version's text for this change (the isv repository at tag
`v<version>`).

## Steps

1. **Tier.** Classify by the change, not by who asks:
   T0 patch · T1 slice inside the existing design · T2 new subsystem, model, contract, money/security
   rule or irreversible step. If T0 or T1, say so in one line, `isv log tier.set tier=… reason=…`, and
   stop: T1 goes to `slice build`, T0 is done directly and then `verify`. If the human overrides the
   tier, log `tier.set … overridden_by=human`. For T2: `isv log change.started tier=T2 slug=<slug>`.

2. **Current-state primer** (at most one screen, generated from the code now, never from memory or an
   old doc): what exists, how a request flows today, exactly where this change lands, with file links.
   Ask the human to correct it. `isv log primer.shown lines=<n>`.

3. **Grill, then triage decisions.** List the open questions. Answer every factual one from the code
   or docs yourself. Sort the rest:
   - *product / money rule* → human, framed in business terms;
   - *one-way technical door* (hard to undo, real consequences) → human, framed by consequence;
   - *reversible technical choice* → decide it yourself and record it as agent-decided.

   Present human decisions **one at a time** as decision cards (`isv template decision-card`, at most
   12 lines). For each: `isv log decision.presented decision=d<n> kind=<kind>`.
   Offer **Explain** as the last choice: a button where your tool shows choices, the card's
   "explain" reply where it does not or the options already fill its button limit. When it is
   chosen, run `explain` on the decision (`target=d<n> stage=frame depth=<n>`, one deeper each time
   on the same card) and show the same card again. An explanation is not a teach-back: the decision
   stays open.
   Resolution, logged with `isv log decision.resolved decision=d<n> outcome=… teachback=…`:
   - the human answers the card's check question or restates the choice in one sentence →
     `outcome=ruled teachback=pass` (or `fail`: explain again, simpler, then re-ask);
   - the human replies with only a choice → the decision is still open: ask the check question
     once more. Only the human's explicit skip ("skip", "no check") closes it:
     `outcome=adopted teachback=declined` and
     `isv log override step=teachback by=human reason=explicit-skip`. Never log a bare choice as
     the human's override;
   - reversible choices you made → `outcome=agent-decided`.
   What a user pays or receives, and which price applies, is a product decision, never agent-decided.
   Target: at most 3–5 human decisions per change.

4. **Propose the first design yourself:** prose, one small diagram, and one or two rejected
   alternatives in a line each. The human argues; you revise.

5. **Explainability test.** Write the design in at most five plain sentences plus one diagram. If you
   cannot, the design is too complex: simplify the design, not the wording, and try again.
   `isv log explainability.test result=pass|fail` for each attempt.

6. **Write the brief** from `isv template brief`, within `brief.max_lines`. Fill the **Surface
   budget**: every new table, flag, RPC, service or dependency, each with why an existing one cannot
   do it, naming what you checked. Acceptance checks must be executable (a command or test and its
   expected result) and must fail on a wrong implementation: for each, name one mutation of the code
   that turns it red (drop the lock, round down, skip the audit row).

7. **Brief review — one round, two reviewers in parallel, no loop.** Each reviewer has **fresh
   context** and gets only the brief, repository access, the sources of truth the brief cites (design
   docs, earlier rulings, code it names) and its prompt.

   **Necessity**, a subagent with no conversation history:

   > You are reviewing a design brief before any code exists. Restate in three sentences what it will
   > build; if you cannot, report that first. Then return at most 10 items, each labelled exactly one of
   > REMOVE/SIMPLIFY (something that need not exist, or exists already in the repo — name it),
   > QUESTION (a decision or assumption the author must confirm), or MISSING-CHECK (behaviour with no
   > executable acceptance check). Every item needs evidence: a file path, a repo object, or a concrete
   > failing scenario. Do not propose new mechanisms, tables, flags or components. An empty list is a
   > valid answer.

   **Fidelity**, a different model family: write the prompt to a file and run
   `isv review --prompt-file <file> --author agent:<tool>/<model> > <out>`, naming your own tool (it
   picks the reviewer for it from `.isv/config.toml` and can take minutes, so run it in the
   background). Exit code 3 means no usable external reviewer: use a second fresh-context subagent
   and `isv log note` why.

   > You are checking a design brief against its sources before any code exists. Sources: <list>.
   > Return at most 10 items, each labelled exactly one of CONTRADICTION (the brief conflicts with a
   > source or with itself — quote both sides), MISSING-CHECK (a boundary, race or timing case with no
   > executable acceptance check) or QUESTION. Every item needs evidence: file:line on both sides or a
   > concrete failing scenario. Do not propose new mechanisms, tables, flags or components. An empty
   > list is a valid answer.

   Show both lists to the human together; apply what they accept; revise the brief once. A finding a
   test can settle becomes an acceptance check, not more prose. Review again only if the revision adds
   to the surface budget, and then only that part. Log one result per reviewer:
   `isv log necessity.result lens=necessity|fidelity reviewer=<tool/model> remove=<n> ask=<n> missing_check=<n> contradiction=<n> accepted_…`.

8. **Spike** only if an empirical question remains (behaviour, performance, an API's real response):
   a throwaway branch `spike/<slug>`, never merged. Write the answer into the brief as evidence.

9. **Approval.** The human approves the brief once. Set its status to `approved` and hand off to
   `slice`. If the human skipped or changed any step above, `isv log override step=<step> by=human
   reason=…`. If the human drops the change at any point, run `slice close` with `outcome=abandoned`.

## Stop and ask

An assumption in the brief turns out false · an acceptance check cannot be made executable ·
anything irreversible or outward-facing is next. `isv log stop.line reason=<code> detail=…`.
