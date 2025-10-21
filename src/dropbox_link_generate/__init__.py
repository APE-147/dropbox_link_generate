"""
Dropbox Link Generate

A command-line tool to generate Dropbox sharing links.
"""

__version__ = "0.1.0"
__author__ = "Dropbox Link Generate"
__email__ = "niceday@example.com"

from .core.sharing import DropboxLinkGenerator
from .utils.config import Config
from .utils.paths import normalize_and_validate_path

__all__ = ["DropboxLinkGenerator", "Config", "normalize_and_validate_path"]
