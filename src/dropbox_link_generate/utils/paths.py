from __future__ import annotations

import os
from pathlib import Path

from .errors import NotInDropboxRoot, PathValidationError


def _is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


def normalize_and_validate_path(
    user_path: str | Path,
    dropbox_root: Path,
) -> tuple[Path, str]:
    """Validate a user path and return (resolved_path, dropbox_api_path).

    Rules:
    - Path must be textually under dropbox_root (no outside path allowed)
    - Follow symlinks only if the path itself is within dropbox_root and the
      fully resolved target remains within dropbox_root as well
    - Return path resolved to real file and its Dropbox API path (leading '/')
    """
    p = Path(user_path).expanduser()
    # Absolute without resolving symlinks
    if not p.is_absolute():
        p_abs = (Path.cwd() / p)
    else:
        p_abs = p

    dropbox_root = dropbox_root.resolve()

    # First gate: textual under root
    if not _is_subpath(p_abs, dropbox_root):
        raise NotInDropboxRoot(
            f"Path is not under DROPBOX_ROOT: {p_abs} not in {dropbox_root}"
        )

    # Existence check before resolving
    if not p_abs.exists():
        raise PathValidationError(f"Path does not exist: {p_abs}")
    if p_abs.is_dir():
        raise PathValidationError("Only files are supported (got a directory)")

    # Second gate: fully resolved must still stay within root
    resolved = p_abs.resolve(strict=True)
    if not _is_subpath(resolved, dropbox_root):
        raise NotInDropboxRoot(
            "Symlink target escapes DROPBOX_ROOT; refusing to follow"
        )

    rel = resolved.relative_to(dropbox_root)
    api_path = "/" + str(rel).replace(os.sep, "/")
    return resolved, api_path

