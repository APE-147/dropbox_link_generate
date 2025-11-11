from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import dropbox
from dropbox.exceptions import ApiError, AuthError, BadInputError, HttpError
from dropbox.sharing import RequestedVisibility, SharedLinkSettings

from ..utils.config import DropboxOAuthCredentials
from ..utils.errors import DropboxAuthError, DropboxClientError, DropboxRateLimitError


def _to_raw_url(url: str) -> str:
    """Convert a Dropbox share URL to raw content URL (?raw=1)."""
    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4]))
    query.pop("dl", None)
    query["raw"] = "1"
    parts[4] = urlencode(query)
    return urlunparse(parts)


@dataclass
class DropboxClient:
    credentials: DropboxOAuthCredentials
    timeout: float = 5.0
    user_agent: Optional[str] = None

    def __post_init__(self) -> None:
        self._dbx = dropbox.Dropbox(
            timeout=self.timeout,
            user_agent=self.user_agent,
            oauth2_access_token=self.credentials.access_token,
            oauth2_refresh_token=self.credentials.refresh_token,
            app_key=self.credentials.app_key,
            app_secret=self.credentials.app_secret,
        )

    def get_or_create_shared_link(self, path: str) -> str:
        url = self._with_retry(lambda: self._list_first_shared_link(path))
        if url:
            return _to_raw_url(url)

        created_url = self._with_retry(lambda: self._create_shared_link(path))
        return _to_raw_url(created_url)

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
        except AuthError as e:
            raise DropboxAuthError(
                "Authentication with Dropbox failed. "
                "Please verify DROPBOX_APP_KEY, DROPBOX_APP_SECRET, and DROPBOX_REFRESH_TOKEN "
                "or run `dplk auth` to refresh credentials."
            ) from e
        except ApiError as e:
            if getattr(e, "status_code", None) == 429:
                time.sleep(1.0)
                try:
                    return func()
                except Exception as e2:
                    raise DropboxRateLimitError("Rate limit exceeded (429)") from e2
            raise DropboxClientError(str(e)) from e
        except (HttpError, BadInputError) as e:
            try:
                return func()
            except Exception as e2:  # pragma: no cover
                raise DropboxClientError("Network or HTTP error with Dropbox API") from e2


__all__ = ["DropboxClient", "_to_raw_url"]
