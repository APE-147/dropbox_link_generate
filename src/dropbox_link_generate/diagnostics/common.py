"""Shared helpers for diagnostic commands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import dropbox
from dotenv import load_dotenv


@dataclass
class Credentials:
    """Dropbox OAuth credential bundle."""

    app_key: str
    app_secret: str
    refresh_token: str
    access_token: Optional[str]


@dataclass
class EnvCheck:
    """Result of validating the environment configuration."""

    missing: list[str]
    dropbox_root: Optional[Path]


REQUIRED_ENV_VARS: tuple[str, ...] = (
    "DROPBOX_APP_KEY",
    "DROPBOX_APP_SECRET",
    "DROPBOX_REFRESH_TOKEN",
)


def load_credentials() -> Credentials:
    """Load Dropbox credentials from the environment/.env file."""

    load_dotenv()
    app_key = os.getenv("DROPBOX_APP_KEY", "").strip()
    app_secret = os.getenv("DROPBOX_APP_SECRET", "").strip()
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN", "").strip()
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN", "").strip() or None

    return Credentials(
        app_key=app_key,
        app_secret=app_secret,
        refresh_token=refresh_token,
        access_token=access_token,
    )


def validate_env() -> EnvCheck:
    """Validate required environment variables and Dropbox root path."""

    load_dotenv()
    missing: list[str] = []
    for key in ("DROPBOX_ROOT", *REQUIRED_ENV_VARS):
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(key)

    root_value = os.getenv("DROPBOX_ROOT", "").strip() or None
    dropbox_root = Path(root_value).expanduser() if root_value else None

    return EnvCheck(missing=missing, dropbox_root=dropbox_root)


def build_client(credentials: Credentials) -> dropbox.Dropbox:
    """Instantiate a Dropbox client from credentials."""

    if not credentials.app_key or not credentials.app_secret or not credentials.refresh_token:
        raise ValueError("Missing Dropbox OAuth credentials")

    return dropbox.Dropbox(
        app_key=credentials.app_key,
        app_secret=credentials.app_secret,
        oauth2_refresh_token=credentials.refresh_token,
        oauth2_access_token=credentials.access_token,
        timeout=10.0,
    )
