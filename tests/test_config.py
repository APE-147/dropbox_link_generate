import os
from pathlib import Path

import pytest

from dropbox_link_generate.utils.config import Config
from dropbox_link_generate.utils.errors import ConfigError


def test_config_from_env_ok(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    monkeypatch.setenv("DROPBOX_TOKEN", "token123")
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    cfg = Config.from_env(env_path=tmp_path)
    assert cfg.token == "token123"
    assert cfg.dropbox_root == root
    assert cfg.archive_dir is None


def test_config_with_archive_dir(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    archive = root / "archives"
    monkeypatch.setenv("DROPBOX_TOKEN", "token123")
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", str(archive))

    cfg = Config.from_env(env_path=tmp_path)
    assert cfg.archive_dir == archive


def test_config_missing_token(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    monkeypatch.delenv("DROPBOX_TOKEN", raising=False)
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    with pytest.raises(ConfigError):
        Config.from_env(env_path=tmp_path)


def test_config_missing_root(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DROPBOX_TOKEN", "t")
    monkeypatch.delenv("DROPBOX_ROOT", raising=False)
    with pytest.raises(ConfigError):
        Config.from_env(env_path=tmp_path)


def test_config_archive_dir_must_be_inside_root(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    outside = tmp_path / "other"
    outside.mkdir()
    monkeypatch.setenv("DROPBOX_TOKEN", "token123")
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", str(outside))

    with pytest.raises(ConfigError):
        Config.from_env(env_path=tmp_path)


def test_config_archive_dir_absolute(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    monkeypatch.setenv("DROPBOX_TOKEN", "token123")
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", "relative/path")

    with pytest.raises(ConfigError):
        Config.from_env(env_path=tmp_path)
