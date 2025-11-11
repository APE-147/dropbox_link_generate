import os
import zipfile
from pathlib import Path

from click.testing import CliRunner

from dropbox_link_generate.cli import AuthResult, main
from dropbox_link_generate.utils.errors import DropboxAuthError


def test_cli_success(tmp_path, monkeypatch):
    # Prepare Dropbox root and file
    root = tmp_path / "Dropbox"
    root.mkdir()
    f = root / "a.txt"
    f.write_text("hello")

    # Env config
    monkeypatch.setenv("DROPBOX_APP_KEY", "app_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "app_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "refresh")
    monkeypatch.setenv("DROPBOX_ROOT", str(root.resolve()))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", "")

    # Stub clipboard copy to avoid external deps
    monkeypatch.setattr(
        "dropbox_link_generate.utils.clipboard.copy_to_clipboard", lambda *_args, **_kwargs: True
    )

    # Stub Dropbox client behavior
    def fake_get_or_create(_self, path: str) -> str:
        assert path == "/a.txt"
        return "https://www.dropbox.com/s/xyz/a.txt?raw=1"

    monkeypatch.setattr(
        "dropbox_link_generate.services.dropbox_client.DropboxClient.get_or_create_shared_link",
        fake_get_or_create,
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(f)])
    assert result.exit_code == 0
    assert result.output.strip().endswith("?raw=1")


def test_cli_reject_outside_root(tmp_path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    f = tmp_path / "outside.txt"
    f.write_text("hi")
    monkeypatch.setenv("DROPBOX_APP_KEY", "app_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "app_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "refresh")
    monkeypatch.setenv("DROPBOX_ROOT", str(root.resolve()))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", "")

    runner = CliRunner()
    result = runner.invoke(main, [str(f)])
    assert result.exit_code == 1
    assert "DROPBOX_ROOT" in result.output


def test_cli_archives_directory(tmp_path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    directory = root / "project"
    directory.mkdir()
    file_in_dir = directory / "file.txt"
    file_in_dir.write_text("data")

    archive_dir = root / "archives"

    monkeypatch.setenv("DROPBOX_APP_KEY", "app_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "app_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "refresh")
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", str(archive_dir))

    monkeypatch.setattr(
        "dropbox_link_generate.utils.clipboard.copy_to_clipboard",
        lambda *_args, **_kwargs: True,
    )

    captured = {}

    def fake_get_or_create(_self, path: str) -> str:
        captured["path"] = path
        return "https://www.dropbox.com/s/xyz/project.zip?raw=1"

    monkeypatch.setattr(
        "dropbox_link_generate.services.dropbox_client.DropboxClient.get_or_create_shared_link",
        fake_get_or_create,
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(directory)])

    assert result.exit_code == 0
    expected_path = "/archives/project.zip"
    assert "path" in captured
    assert captured["path"] == expected_path
    generated_zip = archive_dir / "project.zip"
    assert generated_zip.exists()
    with zipfile.ZipFile(generated_zip) as zf:
        assert "project/file.txt" in zf.namelist()


def test_cli_auto_auth_on_missing_refresh_token(tmp_path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    file_path = root / "file.txt"
    file_path.write_text("data")

    monkeypatch.setenv("DROPBOX_APP_KEY", "app_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "app_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "")
    monkeypatch.setenv("DROPBOX_ROOT", str(root.resolve()))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", "")

    monkeypatch.setattr(
        "dropbox_link_generate.utils.clipboard.copy_to_clipboard",
        lambda *_args, **_kwargs: True,
    )

    auth_result = AuthResult(
        app_key="app_key",
        app_secret="app_secret",
        refresh_token="new_refresh",
        access_token=None,
        expires_at=None,
        scopes=["sharing.read"],
    )

    called = {"auth": False}

    def fake_auth_flow(**_kwargs):
        called["auth"] = True
        return auth_result

    monkeypatch.setattr("dropbox_link_generate.cli._perform_auth_flow", fake_auth_flow)

    def fake_get_or_create(_self, path: str) -> str:
        assert path == "/file.txt"
        assert os.environ["DROPBOX_REFRESH_TOKEN"] == "new_refresh"
        return "https://example.com/file.txt?raw=1"

    monkeypatch.setattr(
        "dropbox_link_generate.services.dropbox_client.DropboxClient.get_or_create_shared_link",
        fake_get_or_create,
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(file_path)])

    assert result.exit_code == 0
    assert called["auth"] is True
    assert "https://example.com/file.txt?raw=1" in result.output


def test_cli_auto_auth_on_dropbox_auth_error(tmp_path, monkeypatch):
    root = tmp_path / "Dropbox"
    root.mkdir()
    file_path = root / "file.txt"
    file_path.write_text("data")

    monkeypatch.setenv("DROPBOX_APP_KEY", "app_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "app_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "stale_token")
    monkeypatch.setenv("DROPBOX_ROOT", str(root.resolve()))
    monkeypatch.setenv("DROPBOX_ARCHIVE_DIR", "")

    monkeypatch.setattr(
        "dropbox_link_generate.utils.clipboard.copy_to_clipboard",
        lambda *_args, **_kwargs: True,
    )

    auth_result = AuthResult(
        app_key="app_key",
        app_secret="app_secret",
        refresh_token="fresh_token",
        access_token=None,
        expires_at=None,
        scopes=["sharing.read"],
    )

    def fake_auth_flow(**_kwargs):
        return auth_result

    monkeypatch.setattr("dropbox_link_generate.cli._perform_auth_flow", fake_auth_flow)

    call_counter = {"count": 0}

    def fake_get_or_create(_self, path: str) -> str:
        call_counter["count"] += 1
        assert path == "/file.txt"
        if call_counter["count"] == 1:
            raise DropboxAuthError("token expired")
        assert os.environ["DROPBOX_REFRESH_TOKEN"] == "fresh_token"
        return "https://example.com/file.txt?raw=1"

    monkeypatch.setattr(
        "dropbox_link_generate.services.dropbox_client.DropboxClient.get_or_create_shared_link",
        fake_get_or_create,
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(file_path)])

    assert result.exit_code == 0
    assert call_counter["count"] == 2
    assert os.environ["DROPBOX_REFRESH_TOKEN"] == "fresh_token"
    assert "https://example.com/file.txt?raw=1" in result.output
