from pathlib import Path
import os

import pytest

from dropbox_link_generate.utils.paths import normalize_and_validate_path
from dropbox_link_generate.utils.errors import NotInDropboxRoot, PathValidationError


def test_normalize_and_validate_inside_root(tmp_path: Path):
    root = tmp_path / "Dropbox"
    root.mkdir()
    f = root / "dir" / "file.txt"
    f.parent.mkdir(parents=True)
    f.write_text("hello")

    resolved, api_path = normalize_and_validate_path(f, root)
    assert resolved == f.resolve()
    assert api_path == "/dir/file.txt"


def test_reject_outside_root(tmp_path: Path):
    root = tmp_path / "Dropbox"
    root.mkdir()
    f = tmp_path / "file.txt"
    f.write_text("hi")

    with pytest.raises(NotInDropboxRoot):
        normalize_and_validate_path(f, root)


def test_reject_directory(tmp_path: Path):
    root = tmp_path / "Dropbox"
    d = root / "dir"
    d.mkdir(parents=True)
    with pytest.raises(PathValidationError):
        normalize_and_validate_path(d, root)


def test_symlink_inside_root_ok(tmp_path: Path):
    root = tmp_path / "Dropbox"
    root.mkdir()
    target = root / "a.txt"
    target.write_text("data")
    link = root / "link.txt"
    link.symlink_to(target)

    resolved, api_path = normalize_and_validate_path(link, root)
    assert resolved == target.resolve()
    assert api_path == "/a.txt"


def test_symlink_inside_root_pointing_outside_rejected(tmp_path: Path):
    root = tmp_path / "Dropbox"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("nope")
    link = root / "leak.txt"
    link.symlink_to(outside)

    from dropbox_link_generate.utils.errors import NotInDropboxRoot

    with pytest.raises(NotInDropboxRoot):
        normalize_and_validate_path(link, root)


def test_symlink_outside_root_even_if_target_inside_rejected(tmp_path: Path):
    root = tmp_path / "Dropbox"
    root.mkdir()
    target = root / "inside.txt"
    target.write_text("ok")
    outside_link = tmp_path / "ln"
    outside_link.symlink_to(target)

    with pytest.raises(NotInDropboxRoot):
        normalize_and_validate_path(outside_link, root)

