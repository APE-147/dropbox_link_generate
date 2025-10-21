from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..services.dropbox_client import DropboxClient
from ..utils.clipboard import copy_to_clipboard
from ..utils.errors import DplkError
from ..utils.paths import normalize_and_validate_path


@dataclass
class DropboxLinkGenerator:
    dropbox_root: Path
    client: DropboxClient
    logger: logging.Logger

    def generate(self, user_path: str | Path, copy: bool = True) -> str:
        resolved, api_path = normalize_and_validate_path(user_path, self.dropbox_root)
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

