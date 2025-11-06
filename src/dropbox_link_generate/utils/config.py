from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .errors import ConfigError


@dataclass
class DropboxOAuthCredentials:
    app_key: str
    app_secret: str
    refresh_token: str
    access_token: Optional[str] = None


@dataclass
class Config:
    oauth: DropboxOAuthCredentials
    dropbox_root: Path
    verbose: bool = False
    log_file: Optional[str] = None
    archive_dir: Optional[Path] = None

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> "Config":
        """Load configuration from environment and optional .env file.

        Required:
        - DROPBOX_APP_KEY
        - DROPBOX_APP_SECRET
        - DROPBOX_REFRESH_TOKEN
        - DROPBOX_ROOT (absolute path)
        Optional:
        - DROPBOX_ACCESS_TOKEN (prefetched short-lived token)
        - VERBOSE (truthy values)
        - LOG_FILE
        """
        if env_path is not None:
            if env_path.is_dir():
                load_dotenv(env_path / ".env")
            else:
                load_dotenv(env_path)
        else:
            load_dotenv()

        refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN", "").strip()
        app_key = os.getenv("DROPBOX_APP_KEY", "").strip()
        app_secret = os.getenv("DROPBOX_APP_SECRET", "").strip()
        access_token = os.getenv("DROPBOX_ACCESS_TOKEN", "").strip() or None
        root_str = os.getenv("DROPBOX_ROOT", "").strip()
        verbose_str = os.getenv("VERBOSE", "").strip().lower()
        log_file = os.getenv("LOG_FILE", "").strip() or None
        archive_str = os.getenv("DROPBOX_ARCHIVE_DIR", "").strip()

        if not app_key:
            raise ConfigError("Missing DROPBOX_APP_KEY in environment/.env")
        if not app_secret:
            raise ConfigError("Missing DROPBOX_APP_SECRET in environment/.env")
        if not refresh_token:
            raise ConfigError("Missing DROPBOX_REFRESH_TOKEN in environment/.env")
        if not root_str:
            raise ConfigError("Missing DROPBOX_ROOT in environment/.env")

        root = Path(root_str).expanduser()
        if not root.is_absolute():
            raise ConfigError("DROPBOX_ROOT must be an absolute path")
        if not root.exists() or not root.is_dir():
            raise ConfigError("DROPBOX_ROOT does not exist or is not a directory")

        archive_dir: Optional[Path] = None
        if archive_str:
            archive_dir = Path(archive_str).expanduser()
            if not archive_dir.is_absolute():
                raise ConfigError("DROPBOX_ARCHIVE_DIR must be an absolute path")
            if archive_dir.exists() and not archive_dir.is_dir():
                raise ConfigError("DROPBOX_ARCHIVE_DIR must be a directory")

            resolved_root = root.resolve()
            resolved_archive = archive_dir.resolve()
            try:
                resolved_archive.relative_to(resolved_root)
            except ValueError:
                raise ConfigError("DROPBOX_ARCHIVE_DIR must be inside DROPBOX_ROOT")

        verbose = verbose_str in {"1", "true", "yes", "on"}
        credentials = DropboxOAuthCredentials(
            app_key=app_key,
            app_secret=app_secret,
            refresh_token=refresh_token,
            access_token=access_token,
        )
        return cls(
            oauth=credentials,
            dropbox_root=root,
            verbose=verbose,
            log_file=log_file,
            archive_dir=archive_dir,
        )
