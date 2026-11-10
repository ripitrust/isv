"""Mechanical checks a CI job (or an agent) runs on a change.

- ``pr_body``: the PR body has every required section.
- ``surface``: every new table / flag / RPC / dependency (as defined by the project's
  detectors) added since the base is named in the PR body's "Surface budget" section.
- ``risk``: which changed files fall under the project's risk paths.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from isv.config import Config

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_SURFACE_SECTION = "surface budget"
_NONE_MARKERS = frozenset({"none", "n/a", "-", "nothing new"})


@dataclass(frozen=True)
class Finding:
    kind: str
    identifier: str
    path: str


def matches(path: str, globs: tuple[str, ...]) -> bool:
    """Glob match where a leading ``**/`` also matches files at the top level."""
    for glob in globs:
        if fnmatch(path, glob) or (glob.startswith("**/") and fnmatch(path, glob[3:])):
            return True
    return False


def _sections(body: str) -> dict[str, str]:
    """Map lower-cased heading text → the text under it, until the next heading."""
    found: dict[str, str] = {}
    marks = list(_HEADING.finditer(body))
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(body)
        found[mark.group(1).strip().lower()] = body[mark.end():end].strip()
    return found


def _section(sections: dict[str, str], name: str) -> str | None:
    # "Risk & rollback" satisfies a required "Risk".
    wanted = name.lower()
    for heading, text in sections.items():
        if heading.startswith(wanted):
            return text
    return None


def pr_body(body: str, config: Config) -> list[str]:
    """Return one message per missing or empty required section."""
    sections = _sections(body)
    problems = []
    for name in config.pr_sections:
        text = _section(sections, name)
        if text is None:
            problems.append(f"missing section: ## {name}")
        elif not text:
            problems.append(f"empty section: ## {name}")
    return problems


class CheckError(RuntimeError):
    """A check could not run, e.g. its base ref does not exist."""


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        # Every caller diffs against a base ref, and a missing one is the usual cause.
        reason = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "failed"
        raise CheckError(f"git {' '.join(args)}: {reason} (check --base)")
    return result.stdout


def changed_files(base: str, cwd: Path) -> list[str]:
    return [line for line in _git(["diff", "--name-only", f"{base}...HEAD"], cwd).splitlines() if line]


def detect_surface(base: str, config: Config, cwd: Path) -> list[Finding]:
    """New surface introduced by added lines since ``base``, per configured detector."""
    files = changed_files(base, cwd)
    findings: list[Finding] = []
    for detector in config.detectors:
        pattern = re.compile(detector.pattern)
        for path in (f for f in files if matches(f, detector.paths)):
            diff = _git(["diff", "--unified=0", f"{base}...HEAD", "--", path], cwd)
            for line in diff.splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                for match in pattern.finditer(line[1:]):
                    identifier = match.group(1) if match.groups() else match.group(0)
                    findings.append(Finding(detector.name, identifier.strip(), path))
    # One entry per (kind, identifier), keeping the first path seen.
    unique: dict[tuple[str, str], Finding] = {}
    for finding in findings:
        unique.setdefault((finding.kind, finding.identifier), finding)
    return list(unique.values())


def surface(body: str, findings: list[Finding]) -> list[str]:
    """Each detected item must be named in the Surface budget section, with a reason."""
    text = _section(_sections(body), _SURFACE_SECTION)
    if text is None:
        return ["missing section: ## Surface budget"]

    declared_none = text.strip().lower() in _NONE_MARKERS
    if declared_none and findings:
        listed = ", ".join(f"{f.kind} {f.identifier}" for f in findings)
        return [f"Surface budget says none, but the diff adds: {listed}"]

    return [
        f"{f.kind} '{f.identifier}' ({f.path}) is new but not justified in ## Surface budget"
        for f in findings
        if f.identifier not in text
    ]


def risk(base: str, config: Config, cwd: Path) -> list[str]:
    """Changed files that fall under the project's risk paths."""
    return [path for path in changed_files(base, cwd) if matches(path, config.risk_paths)]
