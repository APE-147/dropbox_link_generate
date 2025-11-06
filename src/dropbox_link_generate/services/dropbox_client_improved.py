from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import dropbox
from dropbox.exceptions import ApiError, AuthError, BadInputError, HttpError
from dropbox.sharing import RequestedVisibility, SharedLinkSettings

from ..utils.config import DropboxOAuthCredentials
from ..utils.errors import DropboxClientError, DropboxRateLimitError


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
            error_msg = self._format_auth_error(e)
            raise DropboxClientError(error_msg) from e
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

    def _format_auth_error(self, auth_error: AuthError) -> str:
        base_msg = "Authentication with Dropbox failed"

        if hasattr(auth_error, 'error') and auth_error.error:
            error_detail = auth_error.error
            if hasattr(error_detail, 'missing_scope') and error_detail.missing_scope:
                missing_scopes = error_detail.missing_scope
                if isinstance(missing_scopes, list):
                    scopes_str = ", ".join(missing_scopes)
                else:
                    scopes_str = str(missing_scopes)

                base_msg += f": Missing required permission(s): {scopes_str}"
                base_msg += (
                    "\nPlease update your Dropbox app permissions at "
                    "https://www.dropbox.com/developers/apps"
                )
                base_msg += f"\nRequired permissions: {scopes_str}"
                base_msg += (
                    "\nAfter updating permissions, refresh your OAuth credentials "
                    "and update DROPBOX_REFRESH_TOKEN in your .env file."
                )
                return base_msg

        base_msg += ": Invalid or expired credentials"
        base_msg += (
            "\nPlease verify DROPBOX_APP_KEY, DROPBOX_APP_SECRET, and DROPBOX_REFRESH_TOKEN "
            "in the configuration or run `dplk auth` to refresh credentials."
        )
        return base_msg


__all__ = ["DropboxClient", "_to_raw_url"]
