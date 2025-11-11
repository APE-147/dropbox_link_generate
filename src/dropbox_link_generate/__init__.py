"""Dropbox Link Generate - generate Dropbox sharing links via CLI."""

from .core.sharing import DropboxLinkGenerator
from .utils.config import Config
from .utils.paths import normalize_and_validate_path
from .version import __version__, get_version

__author__ = "Dropbox Link Generate"
__email__ = "niceday@example.com"

__all__ = [
    "__version__",
    "get_version",
    "DropboxLinkGenerator",
    "Config",
    "normalize_and_validate_path",
]
