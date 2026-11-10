# Contributing

isv is developed with isv. Every change follows [METHOD.md](METHOD.md): tier it, open a PR, have it
reviewed by a fresh-context reviewer (another model family when it touches `isv/events.py` or
`isv/guard.py`, the risk paths in `.isv/config.toml`), and record the verdict on the PR.

## Before opening a PR

```bash
uv tool install --editable .              # the CLI follows your checkout
python3 -m unittest discover -s tests     # Python 3.11+
uvx ruff check .
claude plugin validate .
isv check pr-body --body-file <body>      # PR body from `isv template pr-body`
```

- **Tests first** for any behaviour change, and see them fail for the right reason.
- **Standard library only.** A new dependency needs a surface-budget line saying why the standard
  library can't do it.
- **The event schema** (`isv/events.py`, `docs/events.md`) only grows: old logs must stay readable.
- **CHANGELOG.md:** each entry says what changed and the evidence that motivated it.

## Releases

Flow (METHOD.md, skills) and CLI share one version, set in `pyproject.toml`, `isv/__init__.py`,
`.claude-plugin/plugin.json`, `METHOD.md` and `README.md`. A release is tagged `v<version>` after
merge. Changes already open keep the version they started under, so a release never changes the
rules of work in progress; flow changes land at a retro, at most three at a time.

A decision that is hard to reverse, surprising and a real trade-off gets a short ADR in
[docs/decisions](docs/decisions).

## Reporting problems

Open an issue with what you ran, what you expected, and what happened. For friction with the flow
itself, `isv note "<one line>"` in your repository records it for the next retro.
