import zipfile
from pathlib import Path

from click.testing import CliRunner

from dropbox_link_generate.cli import main


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
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
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
    monkeypatch.setenv("DROPBOX_ROOT", str(root))
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
