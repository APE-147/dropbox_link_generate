import logging
import sys
from typing import Optional


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Configure root logger according to flags.

    - Default level INFO when verbose=False, DEBUG when verbose=True
    - Logs to stderr by default; if log_file is provided, logs there
    """
    logger = logging.getLogger("dplk")
    # Avoid duplicate handlers if re-configured (e.g., in tests)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler: logging.Handler
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(stream=sys.stderr)

    # Default to WARNING unless verbose so normal runs stay quiet
    handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

