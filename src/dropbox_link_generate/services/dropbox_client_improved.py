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
        except AuthError as e:
            # Improved error handling with specific scope information
            error_msg = self._format_auth_error(e)
            raise DropboxClientError(error_msg) from e
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

    def _format_auth_error(self, auth_error: AuthError) -> str:
        """Format AuthError with helpful information about required permissions."""
        base_msg = "Authentication with Dropbox failed"

        # Check if it's a scope permission error
        if hasattr(auth_error, 'error') and auth_error.error:
            error_detail = auth_error.error
            if hasattr(error_detail, 'missing_scope') and error_detail.missing_scope:
                missing_scopes = error_detail.missing_scope
                if isinstance(missing_scopes, list):
                    scopes_str = ", ".join(missing_scopes)
                else:
                    scopes_str = str(missing_scopes)

                base_msg += f": Missing required permission(s): {scopes_str}"
                base_msg += f"\nPlease update your Dropbox app permissions at https://www.dropbox.com/developers/apps"
                base_msg += f"\nRequired permissions: {scopes_str}"
                base_msg += f"\nAfter updating permissions, regenerate your access token and update the DROPBOX_TOKEN in your .env file."
                return base_msg

        # Generic auth error
        base_msg += ": Invalid or expired access token"
        base_msg += f"\nPlease check your DROPBOX_TOKEN in the .env file"
        return base_msg


__all__ = ["DropboxClient", "_to_raw_url"]