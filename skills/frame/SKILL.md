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
   Resolution, logged with `isv log decision.resolved decision=d<n> outcome=… teachback=…`:
   - the human answers the card's check question or restates the choice in one sentence →
     `outcome=ruled teachback=pass` (or `fail`: explain again, simpler, then re-ask);
   - the human picks without engaging → `outcome=adopted teachback=skipped` (honest, not a ruling);
   - reversible choices you made → `outcome=agent-decided`.
   Target: at most 3–5 human decisions per change.

4. **Propose the first design yourself:** prose, one small diagram, and one or two rejected
   alternatives in a line each. The human argues; you revise.

5. **Explainability test.** Write the design in at most five plain sentences plus one diagram. If you
   cannot, the design is too complex: simplify the design, not the wording, and try again.
   `isv log explainability.test result=pass|fail` for each attempt.

6. **Write the brief** from `isv template brief`, within `brief.max_lines`. Fill the **Surface
   budget**: every new table, flag, RPC, service or dependency, each with why an existing one cannot
   do it, naming what you checked. Acceptance checks must be executable (a command or test and its
   expected result).

7. **Necessity pass — one pass, no loop.** Start a reviewer with **fresh context** (a subagent with no
   conversation history; prefer a different model family; otherwise a new session) and give it only
   the brief, repository access and this prompt:

   > You are reviewing a design brief before any code exists. Restate in three sentences what it will
   > build; if you cannot, report that first. Then return at most 10 items, each labelled exactly one of
   > REMOVE/SIMPLIFY (something that need not exist, or exists already in the repo — name it),
   > QUESTION (a decision or assumption the author must confirm), or MISSING-CHECK (behaviour with no
   > executable acceptance check). Every item needs evidence: a file path, a repo object, or a concrete
   > failing scenario. Do not propose new mechanisms, tables, flags or components. An empty list is a
   > valid answer.

   Show the items to the human; apply what they accept; revise the brief once.
   `isv log necessity.result remove=<n> ask=<n> missing_check=<n> accepted_remove=<n> …`.

8. **Spike** only if an empirical question remains (behaviour, performance, an API's real response):
   a throwaway branch `spike/<slug>`, never merged. Write the answer into the brief as evidence.

9. **Approval.** The human approves the brief once. Set its status to `approved` and hand off to
   `slice`. If the human skipped or changed any step above, `isv log override step=<step> by=human
   reason=…`. If the human drops the change at any point, run `slice close` with `outcome=abandoned`.

## Stop and ask

An assumption in the brief turns out false · an acceptance check cannot be made executable ·
anything irreversible or outward-facing is next. `isv log stop.line reason=<code> detail=…`.
