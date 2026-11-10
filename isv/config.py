"""Project configuration (`.isv/config.toml`) and repository paths.

The log and the config live at the root of the main checkout, found through git's
common directory, so every worktree of a repository shares one log.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_RELATIVE = Path(".isv") / "config.toml"
LOG_RELATIVE = Path(".isv") / "log"

DEFAULT_PR_SECTIONS = ("Why", "What", "Verification", "Risk", "Surface budget")
DEFAULT_TEST_GLOBS = (
    "tests/**", "test/**", "**/test_*.py", "**/*_test.py", "**/*_test.go",
    "**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx",
)


@dataclass(frozen=True)
class Detector:
    """A kind of new surface (table, flag, RPC, dependency...) found in added lines."""

    name: str
    paths: tuple[str, ...]
    pattern: str


@dataclass(frozen=True)
class Config:
    root: Path
    docs_dir: str = "docs/designs"
    adr_dir: str = ""  # unset: the brief's Decisions table is the only decision record
    brief_max_lines: int = 250
    t0_max_changed_lines: int = 100
    review_max_rounds: int = 3
    review_max_nits: int = 5
    review_external_cmd: str = ""
    # Reviewer per authoring tool, keyed by the <tool> of `isv review --author` (default ISV_ACTOR).
    review_external_cmd_by_tool: dict[str, str] = field(default_factory=dict)
    risk_paths: tuple[str, ...] = ()
    test_globs: tuple[str, ...] = DEFAULT_TEST_GLOBS
    pr_sections: tuple[str, ...] = DEFAULT_PR_SECTIONS
    detectors: tuple[Detector, ...] = field(default_factory=tuple)

    @property
    def log_dir(self) -> Path:
        override = os.environ.get("ISV_LOG_DIR")
        return Path(override) if override else self.root / LOG_RELATIVE


def repo_root(start: Path | None = None) -> Path:
    """Root of the main checkout (not the worktree), or the start directory outside git."""
    cwd = start or Path.cwd()
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return cwd
    return Path(common).parent


def checkout_root(start: Path | None = None) -> Path:
    """Root of the current checkout (a worktree's own root), or the start directory outside git."""
    cwd = start or Path.cwd()
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return cwd
    return Path(top)


def load(start: Path | None = None) -> Config:
    root = repo_root(start)
    path = root / CONFIG_RELATIVE
    if not path.is_file():
        return Config(root=root)

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    project = raw.get("project", {})
    review = raw.get("review", {})
    detectors = tuple(
        Detector(name=d["name"], paths=tuple(d["paths"]), pattern=d["pattern"])
        for d in raw.get("surface", {}).get("detectors", [])
    )
    return Config(
        root=root,
        docs_dir=project.get("docs_dir", Config.docs_dir),
        adr_dir=project.get("adr_dir", Config.adr_dir),
        brief_max_lines=raw.get("brief", {}).get("max_lines", Config.brief_max_lines),
        t0_max_changed_lines=raw.get("tiers", {}).get(
            "t0_max_changed_lines", Config.t0_max_changed_lines
        ),
        review_max_rounds=review.get("max_rounds", Config.review_max_rounds),
        review_max_nits=review.get("max_nits", Config.review_max_nits),
        review_external_cmd=review.get("external_cmd", Config.review_external_cmd),
        review_external_cmd_by_tool=dict(review.get("external_cmd_by_tool", {})),
        risk_paths=tuple(raw.get("risk", {}).get("paths", ())),
        test_globs=tuple(project.get("test_globs", DEFAULT_TEST_GLOBS)),
        pr_sections=tuple(raw.get("pr", {}).get("required_sections", DEFAULT_PR_SECTIONS)),
        detectors=detectors,
    )
