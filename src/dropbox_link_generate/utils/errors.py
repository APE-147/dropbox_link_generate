class DplkError(Exception):
    """Base exception for dplk errors."""


class ConfigError(DplkError):
    """Configuration related error."""


class PathValidationError(DplkError):
    """Raised when the provided path fails validation."""


class NotInDropboxRoot(PathValidationError):
    """Raised when a path is not within the configured Dropbox root."""


class DropboxClientError(DplkError):
    """Generic Dropbox client error wrapper."""


class DropboxRateLimitError(DropboxClientError):
    """Raised on HTTP 429 rate limit responses."""

