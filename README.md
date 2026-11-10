# isv — Intent → Slice → Verify

A small development flow for people who build software with coding agents (Claude Code, Codex).
It sizes the process to the change, puts your attention on real decisions and risky merges, keeps
review bounded, and logs metadata so you can measure whether the flow helps.

Four skills, one dependency-free Python CLI, and a local audit log. Status: **0.2.3, beta**, used
on real work in several repositories since 2026-10-26. [CHANGELOG.md](CHANGELOG.md) records what
changed and the evidence for each change; [docs/decisions](docs/decisions) records the lasting
design decisions.

## Why

Agent-assisted work tends to fail in the same ways: design documents grow under review instead of
shrinking, decisions get approved without being understood, reviews loop without an end, and every
change gets the same heavy process. isv answers with four rules:

- **Size the process to the change.** Most changes need no design document.
- **The human decides; the agent does the rest.** You rule on product rules and hard-to-undo
  choices, and show you understood them. The agent answers factual questions and makes reversible
  choices, and records both.
- **Review is independent and bounded.** A fresh-context reviewer, evidence for every finding, a
  hard round cap, and a verdict that says who merges.
- **Measure, then change the flow.** Every step leaves a metadata event, and each retro changes at
  most three things.

The full rules are in [METHOD.md](METHOD.md).

## How it works

```
  intent ──frame──▶ brief ──slice cut──▶ issues ──slice build──▶ PR ──verify──▶ merge
           (T2 only)  ▲ you approve        ▲ you approve           verdict:
                      │ once               │ once                  MERGE / NEEDS-HUMAN / RETHINK
```

Each change gets a tier: **T0** patch (verify only), **T1** slice (build, verify, close) or **T2**
design (frame first). [METHOD.md § Tiers](METHOD.md#tiers) says which is which.

| Skill | What it does |
|---|---|
| `isv:frame` | Re-teaches the current system, asks you only the real decisions (one card at a time), proposes the design, and writes one short brief with executable acceptance checks |
| `isv:slice` | Cuts the brief into vertical slices, builds each as one small tested PR, and closes the change |
| `isv:verify` | Reviews one PR with a fresh-context reviewer (another model family on risk paths), at most 3 rounds, and records the verdict on the PR |
| `isv:explain` | Explains any part of the system, a PR or a term in plain words, one level deeper each time |

## Quickstart

**1. Install the CLI** (Python 3.11+, no dependencies):

```bash
uv tool install git+https://github.com/ripitrust/isv    # or: pipx install git+https://github.com/ripitrust/isv
```

**2. Install the skills** as a plugin:

| Agent | Commands |
|---|---|
| Claude Code | `claude plugin marketplace add ripitrust/isv`, then `claude plugin install isv@isv` |
| Codex | `codex plugin marketplace add ripitrust/isv`, then `codex plugin add isv@isv` |

Both show the skills as `isv:frame`, `isv:slice`, `isv:verify` and `isv:explain`. Any other agent
that reads `SKILL.md` files can use `skills/` directly.

**3. Set up a repository** once:

```bash
cd your-repo && isv init     # writes .isv/config.toml and git-ignores .isv/log/
```

Then edit `.isv/config.toml`: at least the **risk paths** (what you want to approve yourself) and,
if you have one, a **reviewer from another model family** (see [Reviewers](#reviewers)).

**4. Work.** In an agent session in that repository:

| You want to | Type |
|---|---|
| Design something new, or you're unsure of the tier | `/isv:frame <idea or issue>` |
| Build one change inside the existing design | `/isv:slice build <issue>` |
| Fix something small | ask for it as usual, then `/isv:verify <PR>` |
| Review any PR | `/isv:verify <PR>` |
| Understand something | `/isv:explain <thing>` |

Agents log each step with `isv log` and name themselves with `ISV_ACTOR=agent:<tool>/<model>`.

## What you'll see

- **Decision cards**, one at a time, each with a plain question, options described by what happens
  in practice, a recommendation, and a check question. Reply with your choice *and* your answer to
  the check, for example `A — the user ends with 8,000 credits`. A bare choice is asked again once;
  say "skip" to close it without answering, which is logged.
- **A brief** in `project.docs_dir` (at most 250 lines): a summary of at most five plain sentences,
  the problem, the design, rejected alternatives, your decisions, a surface budget (every new table,
  flag, RPC or dependency, and why an existing one can't do the job), and acceptance checks that
  must fail on a wrong implementation. You approve it once, and the slice list once.
- **One record comment per PR**, starting `isv verdict: <VERDICT>`, listing every review finding and
  how it was handled. PRs waiting on you carry a `needs-human` label:

  ```bash
  gh search prs --state open --label needs-human --author @me
  ```

The verdict is MERGE (nothing important open, no risk path: merge per the repository's rules),
NEEDS-HUMAN (a risk path is touched: you approve the merge) or RETHINK (the round cap was hit with
an important finding open: you decide the approach); see [METHOD.md § Review](METHOD.md#review).

## Configuration

`.isv/config.toml` holds everything project-specific; `isv template config` prints the annotated
default.

| Key | Default | Meaning |
|---|---|---|
| `project.docs_dir` | `docs/designs` | where briefs live, one file per change |
| `project.adr_dir` | unset | where lasting decisions (hard to reverse, surprising, a real trade-off) get a one-paragraph ADR at close; unset means the brief is the record |
| `project.test_globs` | common test paths | excluded from PR size metrics |
| `tiers.t0_max_changed_lines` | `100` | the largest change that can be a T0 |
| `brief.max_lines` | `250` | brief length limit |
| `review.max_rounds` | `3` | review round cap |
| `review.max_nits` | `5` | nits reported per round |
| `review.external_cmd` | unset | reviewer from another model family; unset means a fresh-context subagent |
| `review.external_cmd_by_tool` | empty | a reviewer per authoring tool, e.g. `codex = "claude -p …"` |
| `risk.paths` | none | globs whose changes need your merge approval (NEEDS-HUMAN) |
| `pr.required_sections` | Why, What, Verification, Risk, Surface budget | sections `isv check pr-body` requires |
| `surface.detectors` | none | patterns that find new tables, settings, RPCs or dependencies in added lines |

## Reviewers

Risk-path PRs, and the brief's fidelity review, go to a reviewer from another model family through
`isv review`, which pipes the prompt to `review.external_cmd` (no shell, run in the current
checkout) and returns its output. When nothing is configured it exits 3, and the skill uses a
fresh-context subagent instead.

```toml
[review]
external_cmd = "codex exec -s read-only --ephemeral -"            # Claude Code writes, Codex reviews

[review.external_cmd_by_tool]
codex = "claude -p --strict-mcp-config --tools Read,Grep,Glob"    # Codex writes, Claude reviews
```

Keep reviewers read-only, as above. `claude -p` needs a working headless login (see
`claude setup-token`). A reviewer sends the brief or diff to its model provider.

## Team setup

To have Claude Code offer the plugin to everyone who trusts a repository, commit this in its
`.claude/settings.json`. The hook blocks force-push and `--no-verify`, and needs the CLI installed:

```json
{
  "extraKnownMarketplaces": {"isv": {"source": {"source": "github", "repo": "ripitrust/isv"}}},
  "enabledPlugins": {"isv@isv": true},
  "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "isv guard"}]}]}
}
```

Register the marketplace from this one source on every machine, so it matches what repositories
declare.

## CLI

```text
isv init                                 set up .isv/ in this repository
isv log <event> [--change ID] k=v ...    record one metadata event (docs/events.md)
isv note "<one line>" [--change ID]      record friction
isv report [--change ID] [--github]      flow metrics
isv trace <change>                       the audit chain of one change
isv verify-log                           check the hash chains
isv check pr-body --body-file F          required PR sections present
isv check surface --base B --body-file F new tables/flags/RPCs/deps are declared
isv check risk --base B                  risk paths touched → human merge
isv template <name>                      brief | decision-card | pr-body | slice-issue | config
isv review --prompt-file F [--author A]  run the external reviewer for the author's tool
isv guard                                PreToolUse hook: blocks force-push and --no-verify
```

`isv review` exits with the reviewer's exit code, 3 when no reviewer is usable, and 1 when the prompt
file or command line is invalid. With `[review.external_cmd_by_tool]` set, it picks the reviewer by
the `<tool>` of `--author agent:<tool>/<model>` (default `ISV_ACTOR`), and says so on stderr when no
tool is given.

## Measuring the flow

`isv report` turns the log into the flow's health metrics: human decisions per change, teach-back
coverage, review rounds and reviewer precision, verdicts, stop-the-line events and overrides.
`isv trace <change>` shows one change's chain from start to close. The event schema is in
[docs/events.md](docs/events.md).

## Versions and updates

Each change runs on the flow version it started under (`flow` on its `change.started`), so a release
never changes the rules of work already in progress. Releases are tagged `v<version>`. To update:

```bash
uv tool upgrade isv                  # or: pipx upgrade isv
claude plugin marketplace update isv && claude plugin update isv@isv
codex plugin marketplace upgrade && codex plugin add isv@isv
```

## Privacy and security

- The log stays in the repository's main checkout and is git-ignored. It holds metadata only: event
  names, counts, ids and short reasons, never code, prompts or diffs, and it refuses text that looks
  like a secret.
- `review.external_cmd` runs a command from the repository's config. Review changes to that file like
  code.
- External reviewers send what they review to their model provider.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes to isv go through isv itself.

## License

[MIT](LICENSE)
