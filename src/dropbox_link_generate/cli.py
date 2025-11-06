from __future__ import annotations

import sys
from pathlib import Path

import click

from .utils.config import Config
from .utils.errors import DplkError, ConfigError, PathValidationError, DropboxClientError
from .utils.logging import setup_logging
from .services.dropbox_client import DropboxClient
from .core.sharing import DropboxLinkGenerator


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", type=click.Path(dir_okay=False, writable=True), help="Log file path")
@click.option("--no-copy", is_flag=True, help="Do not copy link to clipboard")
@click.argument("path", type=click.Path(path_type=Path))
def main(verbose: bool, log_file: str | None, no_copy: bool, path: Path) -> None:
    """Generate a Dropbox sharing link for a file under your Dropbox root.

    PATH must be a file path inside DROPBOX_ROOT (configured via .env).
    Prints the URL to stdout and exits with code 0 on success; on error, prints
    a concise message to stderr and exits with code 1.
    """
    try:
        cfg = Config.from_env()
        # CLI flags override environment
        if verbose:
            cfg.verbose = True
        if log_file:
            cfg.log_file = log_file

        logger = setup_logging(verbose=cfg.verbose, log_file=cfg.log_file)
        logger.debug("Loaded configuration: root=%s", cfg.dropbox_root)

        client = DropboxClient(token=cfg.token, timeout=5.0, user_agent="dplk/0.1")
        generator = DropboxLinkGenerator(
            dropbox_root=cfg.dropbox_root,
            client=client,
            logger=logger,
            archive_dir=cfg.archive_dir,
        )

        link = generator.generate(path, copy=not no_copy)
        # Per requirements, print only the URL to stdout
        click.echo(link, err=False)
        sys.exit(0)

    except (ConfigError, PathValidationError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except DropboxClientError as e:
        click.echo(f"Dropbox API error: {e}", err=True)
        sys.exit(1)
    except DplkError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except Exception as e:  # Safety net
        click.echo("Unexpected error occurred", err=True)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
