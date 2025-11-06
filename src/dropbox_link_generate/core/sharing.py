from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..services.dropbox_client import DropboxClient
from ..utils.clipboard import copy_to_clipboard
from ..utils.errors import ConfigError, NotInDropboxRoot, PathValidationError
from ..utils.paths import normalize_and_validate_path


@dataclass
class DropboxLinkGenerator:
    dropbox_root: Path
    client: DropboxClient
    logger: logging.Logger
    archive_dir: Optional[Path] = None

    def generate(self, user_path: str | Path, copy: bool = True) -> str:
        prepared_path = self._prepare_path(user_path)
        resolved, api_path = normalize_and_validate_path(prepared_path, self.dropbox_root)
        self.logger.debug("Resolved path %s to Dropbox API path %s", resolved, api_path)

        link = self.client.get_or_create_shared_link(api_path)
        self.logger.info("Generated/Found link: %s", link)

        if copy:
            ok = copy_to_clipboard(link)
            if ok:
                self.logger.debug("Link copied to clipboard")
            else:
                # Non-fatal, only warn
                self.logger.warning("Failed to copy link to clipboard")

        return link

    # Internal helpers -------------------------------------------------
    def _prepare_path(self, user_path: str | Path) -> Path:
        path = Path(user_path).expanduser()

        if path.is_dir():
            resolved_dir = self._validate_directory(path)
            archive_path = self._archive_directory(resolved_dir)
            self.logger.debug(
                "Archived directory %s to %s before link generation",
                resolved_dir,
                archive_path,
            )
            return archive_path

        return path

    def _validate_directory(self, directory: Path) -> Path:
        if not directory.exists():
            raise PathValidationError(f"Path does not exist: {directory}")
        if not directory.is_dir():
            raise PathValidationError(f"Expected directory path, got: {directory}")

        root = self.dropbox_root.resolve()
        absolute_dir = directory if directory.is_absolute() else (Path.cwd() / directory)

        if not self._is_subpath(absolute_dir, root):
            raise NotInDropboxRoot(
                f"Directory is not under DROPBOX_ROOT: {absolute_dir} not in {root}"
            )

        resolved = absolute_dir.resolve(strict=True)
        if not self._is_subpath(resolved, root):
            raise NotInDropboxRoot("Symlink target escapes DROPBOX_ROOT; refusing to archive")

        return resolved

    def _archive_directory(self, directory: Path) -> Path:
        if self.archive_dir is None:
            raise ConfigError("Directory inputs require DROPBOX_ARCHIVE_DIR to be configured")

        archive_root = self.archive_dir.resolve()
        root = self.dropbox_root.resolve()
        if not self._is_subpath(archive_root, root):
            raise ConfigError("Configured archive directory must stay inside DROPBOX_ROOT")

        archive_root.mkdir(parents=True, exist_ok=True)

        archive_name = directory.name + ".zip"
        destination = archive_root / archive_name

        with tempfile.TemporaryDirectory(prefix="dplk-zip-") as tmpdir:
            temp_base = Path(tmpdir) / directory.name
            shutil.make_archive(
                base_name=str(temp_base),
                format="zip",
                root_dir=str(directory.parent),
                base_dir=directory.name,
            )
            temp_zip = temp_base.with_suffix(".zip")

            if destination.exists():
                if destination.is_dir():
                    raise PathValidationError(
                        f"Archive destination is a directory, cannot overwrite: {destination}"
                    )
                destination.unlink()

            shutil.move(str(temp_zip), destination)

        return destination

    @staticmethod
    def _is_subpath(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except Exception:
            return False
