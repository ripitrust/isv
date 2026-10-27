"""Metrics from the event log, plus optional PR facts derived from GitHub.

The report answers the questions the flow is judged by: how many decisions reach the
human and how they are resolved, where comprehension breaks, whether reviews converge
and how precise they are, and where the flow stops or is overridden.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from isv.checks import matches
from isv.config import Config
from isv.events import Event

HUMAN_DECISION_KINDS = frozenset({"product", "one-way"})
_REVIEW_KINDS = ("remove", "ask", "missing_check", "contradiction")


@dataclass
class Report:
    changes_by_tier: Counter[str] = field(default_factory=Counter)
    closed: Counter[str] = field(default_factory=Counter)
    human_decisions_per_change: float | None = None
    decision_outcomes: Counter[str] = field(default_factory=Counter)
    teachback_first_pass: float | None = None
    teachback_coverage: float | None = None
    explain_requests: Counter[str] = field(default_factory=Counter)
    explain_per_change: float | None = None
    explainability_fail_rate: float | None = None
    necessity_items: Counter[str] = field(default_factory=Counter)
    necessity_accepted: Counter[str] = field(default_factory=Counter)
    review_accepted_by_lens: Counter[str] = field(default_factory=Counter)
    rounds_per_pr: float | None = None
    max_rounds: int = 0
    reviewer_precision: float | None = None
    finding_responses: Counter[str] = field(default_factory=Counter)
    removal_share: float | None = None
    verdicts: Counter[str] = field(default_factory=Counter)
    stop_lines: Counter[str] = field(default_factory=Counter)
    overrides: Counter[str] = field(default_factory=Counter)
    notes: list[str] = field(default_factory=list)
    github: dict[str, float] = field(default_factory=dict)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def build(events: list[Event]) -> Report:
    report = Report()
    changes = {e.change for e in events if e.event == "change.started"}
    # Only T2 changes reach frame, where human decisions happen; T1 would dilute the ratio.
    framed = {e.change for e in events if e.event == "change.started" and e.data["tier"] == "T2"}
    human_decisions: Counter[str] = Counter()
    teachbacks: list[str] = []
    human_kind: set[tuple[str, str]] = set()
    # Latest teach-back per human decision; a decision brought back as a new card counts once.
    human_teachback: dict[tuple[str, str], str] = {}
    explain_by_change: Counter[str] = Counter()
    explainability: list[str] = []
    rounds: dict[int, int] = defaultdict(int)
    findings_total = removal_total = 0

    for e in events:
        d = e.data
        match e.event:
            case "change.started":
                report.changes_by_tier[str(d["tier"])] += 1
            case "change.closed":
                report.closed[str(d["outcome"])] += 1
            case "decision.presented" if d["kind"] in HUMAN_DECISION_KINDS:
                human_decisions[e.change] += 1
                human_kind.add((e.change, str(d["decision"])))
            case "decision.resolved":
                report.decision_outcomes[str(d["outcome"])] += 1
                if d.get("teachback") in {"pass", "fail"}:
                    teachbacks.append(str(d["teachback"]))
                key = (e.change, str(d["decision"]))
                if key in human_kind:
                    human_teachback[key] = str(d.get("teachback", "skipped"))
            case "explain.requested":
                report.explain_requests[str(d["stage"])] += 1
                explain_by_change[e.change] += 1
            case "explainability.test":
                explainability.append(str(d["result"]))
            case "necessity.result":
                for kind in _REVIEW_KINDS:
                    report.necessity_items[kind] += int(d.get(kind, 0))
                    accepted = int(d.get(f"accepted_{kind}", 0))
                    report.necessity_accepted[kind] += accepted
                    # Logs from before 0.1.3 have no lens: they came from the necessity pass.
                    report.review_accepted_by_lens[str(d.get("lens", "necessity"))] += accepted
            case "review.round":
                pr = int(d["pr"])
                rounds[pr] = max(rounds[pr], int(d["round"]))
                found = sum(int(d.get(k, 0)) for k in ("important", "nit", "pre_existing"))
                findings_total += found
                removal_total += int(d.get("removal", 0))
            case "finding.resolved":
                report.finding_responses[str(d["response"])] += 1
            case "verdict":
                report.verdicts[str(d["verdict"])] += 1
            case "stop.line":
                report.stop_lines[str(d["reason"])] += 1
            case "override":
                report.overrides[str(d["step"])] += 1
            case "note":
                report.notes.append(f"{e.ts[:10]} {e.change}: {d['text']}")

    if framed:
        report.human_decisions_per_change = round(
            sum(human_decisions[c] for c in framed) / len(framed), 2
        )
    if changes:
        report.explain_per_change = round(
            sum(explain_by_change[c] for c in changes) / len(changes), 2
        )
    report.teachback_first_pass = _ratio(teachbacks.count("pass"), len(teachbacks))
    covered = sum(1 for t in human_teachback.values() if t in {"pass", "fail"})
    report.teachback_coverage = _ratio(covered, len(human_teachback))
    report.explainability_fail_rate = _ratio(explainability.count("fail"), len(explainability))
    if rounds:
        report.rounds_per_pr = round(statistics.mean(rounds.values()), 2)
        report.max_rounds = max(rounds.values())
    resolved = sum(report.finding_responses.values())
    report.reviewer_precision = _ratio(report.finding_responses["fixed"], resolved)
    report.removal_share = _ratio(removal_total, findings_total)
    return report


def github_facts(events: list[Event], config: Config) -> dict[str, float]:
    """Median non-test PR size and hours to merge for PRs named in the log (needs `gh`)."""
    prs = sorted({int(e.data["pr"]) for e in events if "pr" in e.data})
    sizes: list[int] = []
    hours: list[float] = []
    for pr in prs:
        try:
            raw = subprocess.run(
                ["gh", "pr", "view", str(pr), "--json", "files,createdAt,mergedAt"],
                cwd=config.root, capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        data = json.loads(raw)
        sizes.append(
            sum(
                f["additions"] + f["deletions"]
                for f in data["files"]
                if not matches(f["path"], config.test_globs)
            )
        )
        if data.get("mergedAt"):
            opened = datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
            merged = datetime.fromisoformat(data["mergedAt"].replace("Z", "+00:00"))
            hours.append((merged - opened).total_seconds() / 3600)

    facts: dict[str, float] = {"prs": float(len(sizes))}
    if sizes:
        facts["median_non_test_lines"] = float(statistics.median(sizes))
    if hours:
        facts["median_hours_to_merge"] = round(statistics.median(hours), 2)
    return facts


def render(report: Report) -> str:
    def fmt(value: object) -> str:
        if value is None:
            return "n/a"
        if isinstance(value, Counter):
            return ", ".join(f"{k} {v}" for k, v in value.most_common()) or "none"
        return str(value)

    rows = [
        ("Changes by tier", report.changes_by_tier),
        ("Closed", report.closed),
        ("Human decisions per T2 change", report.human_decisions_per_change),
        ("Decision outcomes", report.decision_outcomes),
        ("Teach-back coverage (human decisions)", report.teachback_coverage),
        ("Teach-back first-pass rate", report.teachback_first_pass),
        ("Explain requests per change", report.explain_per_change),
        ("Explain requests by stage", report.explain_requests),
        ("Explainability fail rate", report.explainability_fail_rate),
        ("Brief review items raised", report.necessity_items),
        ("Brief review items accepted", report.necessity_accepted),
        ("Brief review accepted by lens", report.review_accepted_by_lens),
        ("Review rounds per PR (mean)", report.rounds_per_pr),
        ("Review rounds, max", report.max_rounds or None),
        ("Reviewer precision (fixed / resolved)", report.reviewer_precision),
        ("Finding responses", report.finding_responses),
        ("Removal share of findings", report.removal_share),
        ("Verdicts", report.verdicts),
        ("Stop-the-line by reason", report.stop_lines),
        ("Overrides by step", report.overrides),
    ]
    rows += [(f"GitHub: {k.replace('_', ' ')}", v) for k, v in report.github.items()]
    width = max(len(label) for label, _ in rows)
    lines = [f"{label.ljust(width)}  {fmt(value)}" for label, value in rows]
    if report.notes:
        lines += ["", "Notes:", *(f"  {n}" for n in report.notes[-20:])]
    return "\n".join(lines)
