# 0003. The external reviewer is a configured command, chosen by the author's tool

- **Status:** accepted (isv 0.1.3, extended in 0.1.7, 2026-10-26/27)

**Context.** An agent reviewing its own model family's work shares its blind spots, so risk-path PRs
and the brief's fidelity review need a reviewer from another family. Which reviewers exist differs per
machine and repository, and a team may write with more than one agent tool.

**Decision.** `isv review --prompt-file F` passes the prompt on stdin to `review.external_cmd` from
the repository's config, split with shlex and run without a shell in the current checkout, and returns
the reviewer's output and exit code. `[review.external_cmd_by_tool]` picks a different command by the
`<tool>` of the change's author (`--author`, default `ISV_ACTOR`). Exit code 3 means no usable
reviewer, and the skill falls back to a fresh-context subagent.

**Rejected.** Hard-coding one reviewer (ties isv to a vendor); a shell string (injection surface);
choosing by the reviewing session instead of the author (a Claude session reviewing a Codex-written PR
would pick Codex).

**Consequences.** The config file can run commands, so it is reviewed like code. Reviewers must be
kept read-only by their own flags. A same-family fallback is possible and must be visible in the
record.
