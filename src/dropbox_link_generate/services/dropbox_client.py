from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import dropbox
from dropbox.exceptions import ApiError, AuthError, BadInputError, HttpError
from dropbox.sharing import RequestedVisibility, SharedLinkSettings

from ..utils.errors import (
    DropboxClientError,
    DropboxRateLimitError,
)


def _to_raw_url(url: str) -> str:
    """Convert a Dropbox share URL to raw content URL (?raw=1)."""
    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4]))
    # Clear conflicting params (dl), prefer raw=1
    query.pop("dl", None)
    query["raw"] = "1"
    parts[4] = urlencode(query)
    return urlunparse(parts)


@dataclass
class DropboxClient:
    token: str
    timeout: float = 5.0
    user_agent: Optional[str] = None

    def __post_init__(self) -> None:
        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        # The official SDK takes a timeout parameter (seconds)
        self._dbx = dropbox.Dropbox(oauth2_access_token=self.token, timeout=self.timeout)

    def get_or_create_shared_link(self, path: str) -> str:
        """Return a raw shared link for the given Dropbox path.

        Behavior:
        - If a shared link already exists, reuse it (idempotent)
        - Otherwise create with public visibility
        - 5s timeout per call, 1 quick retry on transient errors
        - On 429, perform a brief backoff and retry once
        """
        # First: try listing existing links
        url = self._with_retry(lambda: self._list_first_shared_link(path))
        if url:
            return _to_raw_url(url)

        # Create new link
        created_url = self._with_retry(lambda: self._create_shared_link(path))
        return _to_raw_url(created_url)

    # Internal helpers -----------------------------------------------------
    def _list_first_shared_link(self, path: str) -> Optional[str]:
        res = self._dbx.sharing_list_shared_links(path=path, direct_only=True)
        links = res.links or []
        return links[0].url if links else None

    def _create_shared_link(self, path: str) -> str:
        settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
        res = self._dbx.sharing_create_shared_link_with_settings(path=path, settings=settings)
        return res.url

    def _with_retry(self, func):
        try:
            return func()
        except AuthError as e:  # invalid token etc.
            raise DropboxClientError("Authentication with Dropbox failed") from e
        except ApiError as e:
            # ApiError may wrap HTTP errors; check for 429
            if getattr(e, "status_code", None) == 429:
                # minimal backoff then retry once
                time.sleep(1.0)
                try:
                    return func()
                except Exception as e2:
                    raise DropboxRateLimitError("Rate limit exceeded (429)") from e2
            raise DropboxClientError(str(e)) from e
        except (HttpError, BadInputError) as e:
            # Quick retry once
            try:
                return func()
            except Exception as e2:  # pragma: no cover - rare path
                raise DropboxClientError("Network or HTTP error with Dropbox API") from e2


__all__ = ["DropboxClient", "_to_raw_url"]

