# isv

**Intent → Slice → Verify.** A small development flow for working with coding agents. Four
skills, one dependency-free CLI, and a local audit log that measures whether the flow helps.

Status: 0.1.8, internal beta. No results are claimed yet; `isv report` exists to produce them.

## What is in it

| Part | What it does |
|---|---|
| [METHOD.md](METHOD.md) | The flow: tiers, human touchpoints, review rules, stop-the-line, measurement |
| `skills/frame` | Turns intent into a short brief with real decisions and executable checks (T2 only) |
| `skills/slice` | Cuts a brief into vertical slices; builds each as one small, tested PR; closes the change |
| `skills/verify` | Fresh-context, evidence-bound review with a round cap and a verdict |
| `skills/explain` | Plain-words explanation grounded in the code, one level at a time |
| `isv` CLI | Event log, report, audit trace, PR checks, templates, a push guard hook |

Each PR an agent opens and reviews gets one `isv verdict:` comment with its findings and how each
was handled. PRs waiting on you also get a `needs-human` label: `gh search prs --state open --label needs-human --author @me`.

## Install

Each person, once, with read access to this repository:

```bash
uv tool install git+https://github.com/ripitrust/isv    # the CLI; or: pipx install git+https://github.com/ripitrust/isv
```

| Agent | Skills, as a plugin from this repository's marketplace |
|---|---|
| Claude Code | `claude plugin marketplace add ripitrust/isv`, then `claude plugin install isv@isv` |
| Codex | `codex plugin marketplace add ripitrust/isv`, then `codex plugin add isv@isv` |

Both show the skills as `isv:frame`, `isv:slice`, `isv:verify` and `isv:explain`. The skills call
only `isv` and standard git/gh; any other agent that reads `SKILL.md` files can use `skills/`
directly. Register the marketplace from this one source on every machine, a maintainer's included,
so it matches what repositories declare.

Each repository, once:

```bash
cd your-repo && isv init     # writes .isv/config.toml, ignores .isv/log/
```

To have Claude Code offer the plugin to everyone who trusts the repository, commit this in its
`.claude/settings.json`, with the guard hook below:

```json
{
  "extraKnownMarketplaces": {"isv": {"source": {"source": "github", "repo": "ripitrust/isv"}}},
  "enabledPlugins": {"isv@isv": true}
}
```

## CLI

```text
isv log <event> [--change ID] k=v ...   record one metadata event (docs/events.md)
isv note "<one line>" [--change ID]     record friction
isv report [--change ID] [--github]     flow metrics
isv trace <change>                      the audit chain of one change
isv verify-log                          check the hash chains
isv check pr-body --body-file F         required PR sections present
isv check surface --base B --body-file F   new tables/flags/RPCs/deps are declared
isv check risk --base B                 risk paths touched → human merge
isv template <name>                     brief | decision-card | pr-body | slice-issue | config
isv review --prompt-file F [--author A]  run the external reviewer for the author's tool
isv guard                               PreToolUse hook: blocks force-push and --no-verify
```

`isv review` passes the prompt file on stdin to `review.external_cmd` (a command line from the main
checkout's config, run without a shell in the current checkout, so run it from the PR's head) and
returns the reviewer's output and exit code. It exits 3 when
no reviewer is configured or the command is not found, so callers fall back to a subagent, and 1
when the prompt file or the command line is invalid.

When authors use different tools, `[review.external_cmd_by_tool]` names a reviewer per tool, picked
by the `<tool>` of the change's author: `--author agent:<tool>/<model>`, or `ISV_ACTOR` without it.
For example, Claude reviews what Codex wrote. A tool not listed uses `review.external_cmd`; an empty
entry means no external reviewer (exit 3). If the table is set and no author tool is given,
`isv review` says so on stderr, since the default reviewer may share the author's model family.

Guard hook (`.claude/settings.json`):

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "isv guard"}]}]}}
```

## Privacy

The log stays in the repository's main checkout and is git-ignored. It holds metadata only:
event names, counts, ids and short reasons. It never holds code, prompts or diffs, and it
refuses text that looks like a secret. Nothing is sent anywhere.

## Development

```bash
uv tool install --editable /path/to/isv     # the CLI follows your checkout
python3 -m unittest discover -s tests
uvx ruff check .
```

Python 3.11+, standard library only.
