"""Utilities to enforce the project-structure skill contract."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Users/niceday/Developer/Data")
REQUIRED_DOCS = ("REQUIRES.md", "PLAN.md", "TASKS.md")
REQUIRED_TOP_LEVEL = {
    "AGENTS.md",
    "data",
    "docs",
    "project_settings.yaml",
    "README.md",
    "src",
    "tests",
    "pyproject.toml",
    ".gitignore",
}
ALLOWED_FILES = {
    ".env",
    ".env.example",
    "LICENSE",
}
DATA_SUBDIRS = ("out", "reports", "store")


class StructureIssue(Exception):
    """Raised when the tree validation fails irrecoverably."""


def _iter_top_level(root: Path) -> Iterable[Path]:
    for item in root.iterdir():
        if item.name in (".git", "__pycache__"):
            continue
        yield item


def check_tree(root: Path = PROJECT_ROOT) -> list[str]:
    """Validate the repository layout against the skill definition."""

    issues: list[str] = []
    allowed = REQUIRED_TOP_LEVEL | ALLOWED_FILES

    for item in _iter_top_level(root):
        if item.name.startswith(".") and item.name not in allowed:
            continue
        if item.name in allowed:
            continue
        issues.append(f"Unexpected top-level entry: {item.name}")

    docs_dir = root / "docs"
    if not docs_dir.exists():
        issues.append("Missing docs directory")
    else:
        for doc_name in REQUIRED_DOCS:
            if not (docs_dir / doc_name).exists():
                issues.append(f"Missing docs/{doc_name}")

    project_settings = root / "project_settings.yaml"
    if not project_settings.exists():
        issues.append("Missing project_settings.yaml")

    version_file = root / "src" / "dropbox_link_generate" / "version.py"
    if not version_file.exists():
        issues.append("Missing src/dropbox_link_generate/version.py")

    data_link = root / "data"
    expected_target = DATA_ROOT / f"{root.name}-data"
    if not data_link.exists():
        issues.append("Missing data symlink")
    elif not data_link.is_symlink():
        issues.append("data should be a symlink")
    else:
        current_target = data_link.resolve()
        if current_target != expected_target:
            issues.append(f"data symlink should point to {expected_target}")
        for sub in DATA_SUBDIRS:
            if not (current_target / sub).exists():
                issues.append(f"Missing data/{sub} directory")

    return issues


def normalize_structure(root: Path = PROJECT_ROOT) -> list[str]:
    """Attempt to fix structure issues and return a changelog."""

    changes: list[str] = []

    root.mkdir(parents=True, exist_ok=True)

    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    for doc_name in REQUIRED_DOCS:
        doc_path = docs_dir / doc_name
        if not doc_path.exists():
            doc_path.touch()
            changes.append(f"Created docs/{doc_name}")

    ps_file = root / "project_settings.yaml"
    if not ps_file.exists():
        ps_file.touch()
        changes.append("Created project_settings.yaml")

    data_target = DATA_ROOT / f"{root.name}-data"
    data_target.mkdir(parents=True, exist_ok=True)
    for sub in DATA_SUBDIRS:
        subdir = data_target / sub
        if not subdir.exists():
            subdir.mkdir()
            changes.append(f"Created data/{sub}")

    data_link = root / "data"
    if data_link.exists() and not data_link.is_symlink():
        raise StructureIssue("data exists but is not a symlink; manual cleanup required")
    if not data_link.exists():
        data_link.symlink_to(data_target)
        changes.append(f"Created data symlink -> {data_target}")

    return changes
