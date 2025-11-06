from __future__ import annotations

import os
import sys
import textwrap
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import click
from dropbox.oauth import (
    BadStateException,
    CsrfException,
    DropboxOAuth2FlowNoRedirect,
    NotApprovedException,
    ProviderException,
)

from .core.sharing import DropboxLinkGenerator
from .services.dropbox_client import DropboxClient
from .utils.config import Config
from .utils.errors import ConfigError, DropboxClientError, DplkError, PathValidationError
from .utils.logging import setup_logging


DEFAULT_SCOPES: tuple[str, ...] = ("sharing.read", "sharing.write", "files.metadata.read")


def _run_generate(path: Path, verbose: bool, log_file: Optional[str], no_copy: bool) -> int:
    try:
        cfg = Config.from_env()
        if verbose:
            cfg.verbose = True
        if log_file:
            cfg.log_file = log_file

        logger = setup_logging(verbose=cfg.verbose, log_file=cfg.log_file)
        logger.debug("Loaded configuration: root=%s", cfg.dropbox_root)

        client = DropboxClient(credentials=cfg.oauth, timeout=5.0, user_agent="dplk/0.1")
        generator = DropboxLinkGenerator(
            dropbox_root=cfg.dropbox_root,
            client=client,
            logger=logger,
            archive_dir=cfg.archive_dir,
        )

        link = generator.generate(path, copy=not no_copy)
        click.echo(link, err=False)
        return 0

    except (ConfigError, PathValidationError) as e:
        click.echo(str(e), err=True)
        return 1
    except DropboxClientError as e:
        click.echo(f"Dropbox API error: {e}", err=True)
        return 1
    except DplkError as e:
        click.echo(str(e), err=True)
        return 1
    except Exception:  # pragma: no cover
        click.echo("Unexpected error occurred", err=True)
        return 1


def _scopes_to_list(scopes: Iterable[str]) -> list[str]:
    result = [scope for scope in scopes if scope]
    return result or list(DEFAULT_SCOPES)


def _format_datetime(dt: Optional[datetime]) -> str:
    if not dt:
        return "unknown"
    return dt.isoformat()


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", type=click.Path(dir_okay=False, writable=True), help="Log file path")
@click.option("--no-copy", is_flag=True, help="Do not copy link to clipboard")
@click.argument("path", type=click.Path(path_type=Path), required=False)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: str | None, no_copy: bool, path: Path | None) -> None:
    """Generate Dropbox shared links or manage authentication."""

    ctx.ensure_object(dict)
    ctx.obj.update({
        "verbose": verbose,
        "log_file": log_file,
        "no_copy": no_copy,
    })

    if path is not None and ctx.invoked_subcommand is None:
        exit_code = _run_generate(path, verbose, log_file, no_copy)
        ctx.exit(exit_code)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), err=True)
        ctx.exit(1)


@cli.command(help="Run the Dropbox OAuth flow and print refresh token details")
@click.option("--app-key", "app_key", help="Dropbox app key (overrides env)")
@click.option("--app-secret", "app_secret", help="Dropbox app secret (overrides env)")
@click.option(
    "--scope",
    "scopes",
    multiple=True,
    help="OAuth scope to request. Repeat to add more. Defaults to sharing.read, sharing.write, files.metadata.read.",
)
@click.option("--no-browser", is_flag=True, help="Do not attempt to open the authorization URL")
def auth(app_key: Optional[str], app_secret: Optional[str], scopes: tuple[str, ...], no_browser: bool) -> None:
    """Interactive helper to obtain OAuth refresh tokens."""

    app_key = (app_key or os.getenv("DROPBOX_APP_KEY", "")).strip()
    app_secret = (app_secret or os.getenv("DROPBOX_APP_SECRET", "")).strip()

    if not app_key:
        app_key = click.prompt("Dropbox app key", type=str)
    if not app_secret:
        app_secret = click.prompt("Dropbox app secret", type=str, hide_input=True)

    scope_list = _scopes_to_list(scopes)

    click.echo("\n=== Dropbox OAuth Setup ===\n")
    click.echo("Requesting the following scopes:")
    for scope in scope_list:
        click.echo(f"  - {scope}")

    flow = DropboxOAuth2FlowNoRedirect(
        consumer_key=app_key,
        consumer_secret=app_secret,
        token_access_type="offline",
        scope=scope_list,
    )

    authorize_url = flow.start()
    click.echo(
        textwrap.dedent(
            f"""
            1. 打开以下授权链接并登录 Dropbox：
               {authorize_url}
            2. 授权后，复制返回的授权代码。
            """
        ).strip()
    )

    if not no_browser:
        try:
            webbrowser.open(authorize_url)
        except Exception:  # pragma: no cover
            click.echo("无法自动打开浏览器，请手动访问以上链接。")

    auth_code = click.prompt("请输入授权代码", type=str).strip()

    try:
        oauth_result = flow.finish(auth_code)
    except (BadStateException, CsrfException) as exc:
        click.echo(f"授权流程状态无效，请重试。详情: {exc}", err=True)
        sys.exit(1)
    except NotApprovedException:
        click.echo("授权已取消。", err=True)
        sys.exit(1)
    except ProviderException as exc:
        click.echo(f"Dropbox 授权失败: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        click.echo(f"授权失败: {exc}", err=True)
        sys.exit(1)

    refresh_token = getattr(oauth_result, "refresh_token", None)
    if not refresh_token:
        click.echo("未返回 refresh token，请确认应用启用了 offline access。", err=True)
        sys.exit(1)

    click.echo("\n✅ OAuth 授权成功！")
    click.echo("请将以下变量写入 .env 或环境变量：")
    click.echo(f"DROPBOX_APP_KEY={app_key}")
    click.echo(f"DROPBOX_APP_SECRET={app_secret}")
    click.echo(f"DROPBOX_REFRESH_TOKEN={refresh_token}")

    access_token = getattr(oauth_result, "access_token", None)
    expires_at = getattr(oauth_result, "expires_at", None)
    if access_token:
        click.echo("# 可选：短期访问令牌（建议仅作调试使用，SDK 会自动刷新）")
        click.echo(f"DROPBOX_ACCESS_TOKEN={access_token}")
        click.echo(f"# 该令牌将在 {_format_datetime(expires_at)} 过期")

    click.echo("\n完成后即可运行 `dplk <PATH>` 来生成共享链接。")


main = cli


if __name__ == "__main__":  # pragma: no cover
    main()
