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
    cfg = Config.from_env()
    assert cfg.token == "token123"
    assert cfg.dropbox_root == root


def test_config_missing_token(tmp_path: Path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    monkeypatch.delenv("DROPBOX_TOKEN", raising=False)
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    with pytest.raises(ConfigError):
        Config.from_env()


def test_config_missing_root(monkeypatch):
    monkeypatch.setenv("DROPBOX_TOKEN", "t")
    monkeypatch.delenv("DROPBOX_ROOT", raising=False)
    with pytest.raises(ConfigError):
        Config.from_env()

