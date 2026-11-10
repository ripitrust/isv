# 0002. Own small skills and a standard-library CLI, not a stack of plugins

- **Status:** accepted (isv 0.1.0, 2026-10-26)

**Context.** Several agent-workflow plugins cover parts of the same ground (design interviews, slicing,
minimal-change rules, review loops). Installing them side by side gives agents competing instructions
for the same step, and the review loops some of them use only ever add text.

**Decision.** isv ships four skills of its own (frame, slice, verify, explain) as plain `SKILL.md`
files and one Python CLI with no third-party dependencies. It borrows ideas from other flows and
writes them into its own text, with the evidence for each in the CHANGELOG. The skills call only
`isv`, git and `gh`, so any agent that reads `SKILL.md` files can follow them; they ship as a Claude
Code and Codex plugin from one marketplace.

**Rejected.** Installing several external plugins together (overlapping steps, unbounded loops);
a CLI with dependencies (install friction, supply-chain surface).

**Consequences.** Every idea taken from elsewhere must be rewritten and justified here. The CLI stays
small enough to read in one sitting; anything needing a library needs a surface-budget line.
