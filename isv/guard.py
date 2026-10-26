"""Shell-command guard for agent hooks (e.g. Claude Code PreToolUse on Bash).

Reads the hook's JSON from stdin and blocks commands that rewrite shared history or
skip verification. Exit code 2 blocks the call and returns the reason to the agent.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED_EXIT = 2

_RULES = (
    (
        re.compile(r"\bgit\s+push\b[^;&|]*(\s-f\b|\s--force\b|\s--force-with-lease\b|\s\+\S)"),
        "force-push rewrites shared history; push normally or ask the human",
    ),
    (
        re.compile(r"--no-verify\b"),
        "--no-verify skips the checks that protect the repo; fix the failing check instead",
    ),
)


def check(command: str) -> str | None:
    """The reason a command is blocked, or None if it may run."""
    for pattern, reason in _RULES:
        if pattern.search(command):
            return reason
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = str(payload.get("tool_input", {}).get("command", ""))
    reason = check(command)
    if reason is None:
        return 0
    print(f"isv guard: blocked: {reason}", file=sys.stderr)
    return BLOCKED_EXIT
