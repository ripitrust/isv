"""Event log: append-only JSON Lines, one file per change, hash-chained.

Each line is one event. ``prev`` holds the SHA-256 of the previous line in the same
file (the first line points at GENESIS), so editing or deleting a line is detectable
with ``isv verify-log``. Appends take an exclusive file lock, so parallel agents
working on the same change cannot interleave lines or break the chain.

Only metadata is recorded: the schema below accepts short typed fields, caps free
text, and rejects text that looks like a secret.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
GENESIS = "0" * 64
GENERAL_LOG = "_general"
MAX_TEXT = 200

TIERS = frozenset({"T0", "T1", "T2"})

# event -> (required fields, optional fields)
EVENTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "change.started": (frozenset({"tier", "slug"}), frozenset({"issue", "flow"})),
    "change.closed": (frozenset({"outcome"}), frozenset({"detail"})),
    "tier.set": (frozenset({"tier", "reason"}), frozenset({"overridden_by"})),
    "primer.shown": (frozenset({"lines"}), frozenset()),
    "decision.presented": (frozenset({"decision", "kind"}), frozenset({"card_lines"})),
    "decision.resolved": (frozenset({"decision", "outcome"}), frozenset({"teachback"})),
    "explain.requested": (frozenset({"target", "stage"}), frozenset({"depth"})),
    "explainability.test": (frozenset({"result"}), frozenset()),
    "necessity.result": (
        frozenset({"remove", "ask", "missing_check"}),
        frozenset(
            {"accepted_remove", "accepted_ask", "accepted_missing_check", "lens", "reviewer",
             "contradiction", "accepted_contradiction"}
        ),
    ),
    "slice.created": (frozenset({"slice", "risk_path"}), frozenset({"checks", "issue"})),
    "review.round": (
        frozenset({"pr", "round", "reviewer"}),
        frozenset({"important", "nit", "pre_existing", "removal"}),
    ),
    "finding.resolved": (frozenset({"pr", "finding", "response"}), frozenset({"reason"})),
    "verdict": (frozenset({"pr", "verdict", "rounds"}), frozenset()),
    "review.skipped": (frozenset({"pr", "round"}), frozenset({"reason"})),
    "stop.line": (frozenset({"reason"}), frozenset({"detail"})),
    "override": (frozenset({"step", "by", "reason"}), frozenset()),
    "note": (frozenset({"text"}), frozenset()),
}

ENUMS: dict[str, frozenset[str]] = {
    "tier": TIERS,
    "overridden_by": frozenset({"human", "agent"}),
    "kind": frozenset({"product", "one-way", "reversible"}),
    "outcome": frozenset({"ruled", "adopted", "agent-decided", "shipped", "abandoned"}),
    # declined: the human explicitly skipped the check; skipped: no teach-back happened.
    "teachback": frozenset({"pass", "fail", "declined", "skipped"}),
    "stage": frozenset({"frame", "slice", "verify", "other"}),
    "result": frozenset({"pass", "fail"}),
    "response": frozenset({"fixed", "wrong", "intentional", "not-worth", "pre-existing"}),
    "verdict": frozenset({"MERGE", "NEEDS-HUMAN", "RETHINK"}),
    "reason_code": frozenset(
        {"assumption-falsified", "budget", "cap", "not-executable", "irreversible"}
    ),
    "by": frozenset({"human", "agent"}),
    "lens": frozenset({"necessity", "fidelity"}),
}

# Outcome values allowed per event (the shared "outcome" enum covers two events).
OUTCOME_BY_EVENT = {
    "decision.resolved": frozenset({"ruled", "adopted", "agent-decided"}),
    "change.closed": frozenset({"shipped", "abandoned"}),
}

INT_FIELDS = frozenset(
    {
        "issue", "lines", "card_lines", "depth", "remove", "ask", "missing_check",
        "accepted_remove", "accepted_ask", "accepted_missing_check", "checks", "pr",
        "round", "rounds", "important", "nit", "pre_existing", "removal", "contradiction",
        "accepted_contradiction",
    }
)
BOOL_FIELDS = frozenset({"risk_path"})
TEXT_FIELDS = frozenset({"reason", "detail", "text", "target", "step", "reviewer"})
ID_FIELDS = frozenset({"slug", "decision", "slice", "finding", "flow"})

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# Refuse obvious secrets: keys, tokens, private keys, credential assignments.
_SECRET_PATTERN = re.compile(
    r"(sk|rk|pk)_(live|test)_|whsec_|AKIA[0-9A-Z]{16}|-----BEGIN|"
    r"(password|passwd|secret|token|api[_-]?key)\s*[=:]",
    re.IGNORECASE,
)


class EventError(ValueError):
    """An event that does not fit the schema; the message names the field."""


@dataclass(frozen=True)
class Event:
    seq: int
    ts: str
    event: str
    change: str
    actor: str
    data: dict[str, object]
    prev: str


def _coerce(field: str, raw: object) -> object:
    if field in INT_FIELDS:
        try:
            value = int(str(raw))
        except ValueError as exc:
            raise EventError(f"{field} must be an integer") from exc
        if value < 0:
            raise EventError(f"{field} must not be negative")
        return value

    if field in BOOL_FIELDS:
        text = str(raw).lower()
        if text not in {"true", "false", "yes", "no"}:
            raise EventError(f"{field} must be true or false")
        return text in {"true", "yes"}

    text = str(raw)
    if field in ID_FIELDS and not _ID_PATTERN.match(text):
        raise EventError(f"{field} must be a short id (letters, digits, . _ -)")
    if "\n" in text or "\r" in text:
        raise EventError(f"{field} must be a single line")
    if len(text) > MAX_TEXT:
        raise EventError(f"{field} is longer than {MAX_TEXT} characters")
    if _SECRET_PATTERN.search(text):
        raise EventError(f"{field} looks like it contains a secret; not recorded")
    return text


def validate(event: str, fields: dict[str, object]) -> dict[str, object]:
    """Return the coerced fields, or raise EventError naming the first problem."""
    if event not in EVENTS:
        raise EventError(f"unknown event {event!r}; known: {', '.join(sorted(EVENTS))}")

    required, optional = EVENTS[event]
    missing = required - fields.keys()
    if missing:
        raise EventError(f"{event} needs: {', '.join(sorted(missing))}")
    unknown = fields.keys() - required - optional
    if unknown:
        raise EventError(f"{event} does not take: {', '.join(sorted(unknown))}")

    data = {name: _coerce(name, value) for name, value in fields.items()}

    for name, value in data.items():
        allowed = OUTCOME_BY_EVENT.get(event) if name == "outcome" else ENUMS.get(name)
        if event == "stop.line" and name == "reason":
            allowed = ENUMS["reason_code"]
        if allowed is not None and value not in allowed:
            raise EventError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return data


def _line_hash(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()


def _log_file(log_dir: Path, change: str | None) -> Path:
    name = change or GENERAL_LOG
    if change is not None and not _ID_PATTERN.match(change):
        raise EventError("change must be a short id (letters, digits, . _ -)")
    return log_dir / f"{name}.jsonl"


def append(
    log_dir: Path, event: str, fields: dict[str, object], *, change: str | None, actor: str
) -> Event:
    """Validate and append one event under an exclusive lock; return what was written."""
    data = validate(event, fields)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = _log_file(log_dir, change)

    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            handle.seek(0)
            lines = [line for line in handle.read().splitlines() if line.strip()]
            prev = _line_hash(lines[-1]) if lines else GENESIS
            record = {
                "schema": SCHEMA_VERSION,
                "seq": len(lines) + 1,
                "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event": event,
                "change": change or GENERAL_LOG,
                "actor": actor,
                "data": data,
                "prev": prev,
            }
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

    return Event(
        seq=record["seq"], ts=record["ts"], event=event, change=record["change"],
        actor=actor, data=data, prev=prev,
    )


def read_all(log_dir: Path) -> list[Event]:
    """Every event in every log file, ordered by timestamp then sequence."""
    events: list[Event] = []
    if not log_dir.is_dir():
        return events

    for path in sorted(log_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            events.append(
                Event(
                    seq=raw["seq"], ts=raw["ts"], event=raw["event"], change=raw["change"],
                    actor=raw["actor"], data=raw["data"], prev=raw["prev"],
                )
            )
    events.sort(key=lambda e: (e.ts, e.change, e.seq))
    return events


def verify_chain(log_dir: Path) -> list[str]:
    """Return one problem description per broken link; an empty list means intact."""
    problems: list[str] = []
    if not log_dir.is_dir():
        return problems

    for path in sorted(log_dir.glob("*.jsonl")):
        expected_prev = GENESIS
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for number, line in enumerate(lines, start=1):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{path.name}:{number}: not valid JSON")
                break
            if raw.get("prev") != expected_prev or raw.get("seq") != number:
                problems.append(f"{path.name}:{number}: chain broken (edited, removed or reordered)")
                break
            expected_prev = _line_hash(line)
    return problems
