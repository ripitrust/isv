"""`isv` command line: the one tool skills, CI and humans call.

    isv init                              set up .isv/ in this repository
    isv log <event> [--change ID] k=v...  record one event
    isv note "<one line>" [--change ID]   record a friction note (humans)
    isv report [--change ID] [--github]   metrics from the log
    isv trace <change>                    the audit chain of one change
    isv verify-log                        check the log's hash chain
    isv check pr-body|surface|risk        mechanical checks for CI and agents
    isv template <name>                   print a template (brief, decision-card, ...)
    isv guard                             hook adapter: block unsafe shell commands
    isv review --prompt-file F            run the external reviewer on a prompt
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict
from importlib import resources
from pathlib import Path

from isv import __version__, checks, guard
from isv import config as config_mod
from isv import events as events_mod
from isv import report as report_mod

TEMPLATES = ("brief", "decision-card", "pr-body", "slice-issue", "config")
_TEMPLATE_FILES = {name: f"{name}.toml" if name == "config" else f"{name}.md" for name in TEMPLATES}
_GITIGNORE_LINE = ".isv/log/"
_EXIT_FAILED = 1
_EXIT_NO_REVIEWER = 3  # no usable external reviewer: the caller falls back to a subagent


def _template(name: str) -> str:
    return resources.files("isv.templates").joinpath(_TEMPLATE_FILES[name]).read_text(encoding="utf-8")


def _parse_fields(pairs: list[str]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise events_mod.EventError(f"expected key=value, got {pair!r}")
        fields[key] = value
    return fields


def _actor(explicit: str | None, default: str) -> str:
    return explicit or os.environ.get("ISV_ACTOR") or default


def cmd_init(_: argparse.Namespace) -> int:
    root = config_mod.repo_root()
    target = root / config_mod.CONFIG_RELATIVE
    if target.exists():
        print(f"exists: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_template("config"), encoding="utf-8")
        print(f"created: {target}")

    gitignore = root / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    if _GITIGNORE_LINE not in lines:
        with gitignore.open("a", encoding="utf-8") as handle:
            handle.write(("\n" if lines and lines[-1] else "") + f"# isv event log (local)\n{_GITIGNORE_LINE}\n")
        print(f"added {_GITIGNORE_LINE} to {gitignore}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    written = events_mod.append(
        cfg.log_dir, args.event, _parse_fields(args.fields),
        change=args.change, actor=_actor(args.actor, "agent:unknown"),
    )
    print(f"logged {written.event} #{written.seq} ({written.change})")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    written = events_mod.append(
        cfg.log_dir, "note", {"text": args.text}, change=args.change, actor=_actor(args.actor, "human")
    )
    print(f"noted ({written.change})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    events = events_mod.read_all(cfg.log_dir)
    if args.change:
        events = [e for e in events if e.change == args.change]
    if args.since:
        events = [e for e in events if e.ts >= args.since]

    built = report_mod.build(events)
    if args.github:
        built.github = report_mod.github_facts(events, cfg)
    if args.json:
        print(json.dumps(asdict(built), indent=2, default=dict))
    else:
        print(report_mod.render(built))
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    events = [e for e in events_mod.read_all(cfg.log_dir) if e.change == args.change]
    briefs = sorted((cfg.root / cfg.docs_dir).glob(f"*{args.change.split('-', 1)[-1]}*.md"))
    print(f"change {args.change}")
    for brief in briefs:
        print(f"  brief: {brief.relative_to(cfg.root)}")
    if not events:
        print("  (no events)")
        return 0
    for e in events:
        fields = " ".join(f"{k}={v}" for k, v in sorted(e.data.items()))
        print(f"  {e.ts}  #{e.seq:<3} {e.event:<20} {fields}  [{e.actor}]")
    return 0


def cmd_verify_log(_: argparse.Namespace) -> int:
    problems = events_mod.verify_chain(config_mod.load().log_dir)
    for problem in problems:
        print(problem)
    print("log intact" if not problems else f"{len(problems)} broken chain(s)")
    return _EXIT_FAILED if problems else 0


def _body(args: argparse.Namespace) -> str:
    return Path(args.body_file).read_text(encoding="utf-8") if args.body_file != "-" else sys.stdin.read()


def cmd_check(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    cwd = Path.cwd()
    if args.what == "pr-body":
        problems = checks.pr_body(_body(args), cfg)
    elif args.what == "surface":
        found = checks.detect_surface(args.base, cfg, cwd)
        for item in found:
            print(f"new {item.kind}: {item.identifier} ({item.path})")
        problems = checks.surface(_body(args), found)
    else:
        touched = checks.risk(args.base, cfg, cwd)
        print("risk path: " + ("yes" if touched else "no"))
        for path in touched:
            print(f"  {path}")
        return 0

    for problem in problems:
        print(f"FAIL {problem}")
    if not problems:
        print(f"{args.what}: ok")
    return _EXIT_FAILED if problems else 0


def cmd_template(args: argparse.Namespace) -> int:
    print(_template(args.name), end="")
    return 0


def cmd_guard(_: argparse.Namespace) -> int:
    return guard.main()


def _reviewer(cfg: config_mod.Config, author: str) -> tuple[str, str]:
    """(config key, command) of the reviewer for the tool that wrote the change.

    agent:codex/gpt-6 → review.external_cmd_by_tool.codex when listed, else review.external_cmd.
    """
    tool = author.removeprefix("agent:").partition("/")[0] if author.startswith("agent:") else ""
    if tool in cfg.review_external_cmd_by_tool:
        return f"review.external_cmd_by_tool.{tool}", cfg.review_external_cmd_by_tool[tool]

    if cfg.review_external_cmd_by_tool and not tool:
        # The author is unknown, so the default reviewer may share its model family.
        print(
            "isv: no agent:<tool>/<model> author (--author or ISV_ACTOR); using review.external_cmd",
            file=sys.stderr,
        )
    return "review.external_cmd", cfg.review_external_cmd


def cmd_review(args: argparse.Namespace) -> int:
    cfg = config_mod.load()
    prompt = Path(args.prompt_file)
    if not prompt.is_file():
        print(f"isv: prompt file not found: {prompt}", file=sys.stderr)
        return _EXIT_FAILED

    key, command = _reviewer(cfg, _actor(args.author, ""))
    try:
        argv = shlex.split(command)
    except ValueError:
        print(f"isv: {key} is not a valid command line", file=sys.stderr)
        return _EXIT_FAILED
    if not argv:
        print(f"isv: no {key} configured", file=sys.stderr)
        return _EXIT_NO_REVIEWER

    try:
        with prompt.open(encoding="utf-8") as stdin:
            # A command line from the repository's own config, run like any project script.
            result = subprocess.run(
                argv, stdin=stdin, stdout=subprocess.PIPE, text=True, cwd=cfg.root, check=False
            )
    except FileNotFoundError:
        print(f"isv: reviewer command not found: {argv[0]}", file=sys.stderr)
        return _EXIT_NO_REVIEWER
    sys.stdout.write(result.stdout)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="isv", description="Intent → Slice → Verify toolkit")
    parser.add_argument("--version", action="version", version=f"isv {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="set up .isv/ in this repository").set_defaults(func=cmd_init)

    log = sub.add_parser("log", help="record one event")
    log.add_argument("event", help=f"one of: {', '.join(sorted(events_mod.EVENTS))}")
    log.add_argument("fields", nargs="*", help="key=value pairs")
    log.add_argument("--change", help="change id, e.g. 20261027-ledger-core")
    log.add_argument("--actor", help="human | agent:<tool>/<model> (default: $ISV_ACTOR)")
    log.set_defaults(func=cmd_log)

    note = sub.add_parser("note", help="record a one-line friction note")
    note.add_argument("text")
    note.add_argument("--change")
    note.add_argument("--actor")
    note.set_defaults(func=cmd_note)

    rep = sub.add_parser("report", help="metrics from the log")
    rep.add_argument("--change")
    rep.add_argument("--since", help="ISO date, e.g. 2026-11-01")
    rep.add_argument("--github", action="store_true", help="add PR facts via gh")
    rep.add_argument("--json", action="store_true")
    rep.set_defaults(func=cmd_report)

    trace = sub.add_parser("trace", help="audit chain of one change")
    trace.add_argument("change")
    trace.set_defaults(func=cmd_trace)

    sub.add_parser("verify-log", help="check the hash chain").set_defaults(func=cmd_verify_log)

    chk = sub.add_parser("check", help="mechanical checks")
    chk.add_argument("what", choices=("pr-body", "surface", "risk"))
    chk.add_argument("--body-file", default="-", help="PR body file, or - for stdin")
    chk.add_argument("--base", default="origin/main", help="base ref for diff-based checks")
    chk.set_defaults(func=cmd_check)

    tpl = sub.add_parser("template", help="print a template")
    tpl.add_argument("name", choices=TEMPLATES)
    tpl.set_defaults(func=cmd_template)

    sub.add_parser("guard", help="hook adapter: block unsafe shell commands").set_defaults(func=cmd_guard)

    rev = sub.add_parser("review", help="run the external reviewer for the author's tool (review.*)")
    rev.add_argument("--prompt-file", required=True, help="prompt, passed to the reviewer on stdin")
    rev.add_argument("--author", help="the change's agent:<tool>/<model> (default: $ISV_ACTOR)")
    rev.set_defaults(func=cmd_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    # Some argparse versions stop filling `fields` at the first option (`log <event> --change c
    # k=v`), so leftover k=v land here; anything else unknown is still an error.
    if extra:
        if not hasattr(args, "fields") or any(arg.startswith("-") for arg in extra):
            parser.error(f"unrecognized arguments: {' '.join(extra)}")
        args.fields += extra
    try:
        return int(args.func(args))
    except events_mod.EventError as exc:
        print(f"isv: {exc}", file=sys.stderr)
        return _EXIT_FAILED
