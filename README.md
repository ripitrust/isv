# isv

**Intent → Slice → Verify.** A small development flow for working with coding agents. Four
skills, one dependency-free CLI, and a local audit log that measures whether the flow helps.

Status: 0.1.3, internal beta. No results are claimed yet; `isv report` exists to produce them.

## What is in it

| Part | What it does |
|---|---|
| [METHOD.md](METHOD.md) | The flow: tiers, human touchpoints, review rules, stop-the-line, measurement |
| `skills/frame` | Turns intent into a short brief with real decisions and executable checks (T2 only) |
| `skills/slice` | Cuts a brief into vertical slices; builds each as one small, tested PR; closes the change |
| `skills/verify` | Fresh-context, evidence-bound review with a round cap and a verdict |
| `skills/explain` | Plain-words explanation grounded in the code, one level at a time |
| `isv` CLI | Event log, report, audit trace, PR checks, templates, a push guard hook |

## Install

```bash
uv tool install --editable /path/to/isv     # or: pipx install /path/to/isv
cd your-repo && isv init                     # writes .isv/config.toml, ignores .isv/log/
```

The skills are a Claude Code plugin (`.claude-plugin/`). Any agent that reads `SKILL.md` files can
use them. They call only `isv` and standard git/gh.

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
isv review --prompt-file F              run the external reviewer (review.external_cmd)
isv guard                               PreToolUse hook: blocks force-push and --no-verify
```

`isv review` passes the prompt file on stdin to `review.external_cmd` (a command line, run without
a shell from the repository root) and returns the reviewer's output and exit code. It exits 3 when
no reviewer is configured or the command is not found, so callers fall back to a subagent, and 1
when the prompt file or the command line is invalid.

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
python3 -m unittest discover -s tests
uvx ruff check .
```

Python 3.11+, standard library only.
