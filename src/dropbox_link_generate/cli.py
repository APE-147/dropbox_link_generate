from __future__ import annotations

import os
import textwrap
import webbrowser
from dataclasses import dataclass
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
from dotenv import load_dotenv

from .core.sharing import DropboxLinkGenerator
from .diagnostics import check_permissions as run_permissions_check
from .diagnostics import run_auth_debug, run_diagnosis_suite
from .diagnostics.common import EnvCheck, validate_env
from .services.dropbox_client import DropboxClient
from .utils.config import Config
from .utils.errors import (
    ConfigError,
    DropboxAuthError,
    DropboxClientError,
    DplkError,
    PathValidationError,
)
from .utils.logging import setup_logging
from .utils.structure import StructureIssue, check_tree as validate_structure, normalize_structure


DEFAULT_SCOPES: tuple[str, ...] = ("sharing.read", "sharing.write", "files.metadata.read")


@dataclass
class AuthResult:
    app_key: str
    app_secret: str
    refresh_token: str
    access_token: Optional[str]
    expires_at: Optional[datetime]
    scopes: list[str]


class DefaultGroup(click.Group):
    """A click.Group that treats bare arguments as a default command."""

    def __init__(self, *args, default_command: str | None = None, **kwargs):
        self.default_command = default_command
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx: click.Context, args: list[str]) -> None:
        if (
            self.default_command
            and args
            and not args[0].startswith("-")
            and self.get_command(ctx, args[0]) is None
        ):
            args.insert(0, self.default_command)
        super().parse_args(ctx, args)


def _run_generate(path: Path, verbose: bool, log_file: Optional[str], no_copy: bool) -> int:
    attempted_auto_auth = False

    while True:
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

        except PathValidationError as e:
            click.echo(str(e), err=True)
            return 1
        except ConfigError as e:
            if not attempted_auto_auth and _should_trigger_auth_for_config_error(e):
                if _attempt_auto_auth(str(e)):
                    attempted_auto_auth = True
                    continue
            click.echo(str(e), err=True)
            return 1
        except DropboxAuthError as e:
            if not attempted_auto_auth and _attempt_auto_auth(str(e)):
                attempted_auto_auth = True
                continue
            click.echo(f"Dropbox API error: {e}", err=True)
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


def _print_structure_issues(issues: list[str]) -> bool:
    if not issues:
        click.echo("✅ Project structure matches specification.")
        return True

    click.echo("❌ Project structure issues detected:")
    for issue in issues:
        click.echo(f"  - {issue}")
    return False


def _print_env_report(status: EnvCheck) -> bool:
    ok = True
    if status.missing:
        click.echo("❌ Missing environment variables:")
        for key in status.missing:
            click.echo(f"  - {key}")
        ok = False
    else:
        click.echo("✅ Required environment variables are configured.")

    if status.dropbox_root:
        if status.dropbox_root.exists() and status.dropbox_root.is_dir():
            click.echo(f"✅ DROPBOX_ROOT: {status.dropbox_root}")
        else:
            click.echo(f"❌ DROPBOX_ROOT does not exist: {status.dropbox_root}")
            ok = False
    else:
        click.echo("❌ DROPBOX_ROOT is not set.")
        ok = False

    return ok


def _scopes_to_list(scopes: Iterable[str]) -> list[str]:
    result = [scope for scope in scopes if scope]
    return result or list(DEFAULT_SCOPES)


def _format_datetime(dt: Optional[datetime]) -> str:
    if not dt:
        return "unknown"
    return dt.isoformat()


def _apply_auth_result_to_env(result: AuthResult) -> None:
    os.environ["DROPBOX_APP_KEY"] = result.app_key
    os.environ["DROPBOX_APP_SECRET"] = result.app_secret
    os.environ["DROPBOX_REFRESH_TOKEN"] = result.refresh_token

    if result.access_token:
        os.environ["DROPBOX_ACCESS_TOKEN"] = result.access_token
    else:
        os.environ.pop("DROPBOX_ACCESS_TOKEN", None)


def _print_auth_success(result: AuthResult) -> None:
    click.echo("\n✅ OAuth 授权成功！")
    click.echo("请将以下变量写入 .env 或环境变量：")
    click.echo(f"DROPBOX_APP_KEY={result.app_key}")
    click.echo(f"DROPBOX_APP_SECRET={result.app_secret}")
    click.echo(f"DROPBOX_REFRESH_TOKEN={result.refresh_token}")

    if result.access_token:
        click.echo("# 可选：短期访问令牌（建议仅作调试使用，SDK 会自动刷新）")
        click.echo(f"DROPBOX_ACCESS_TOKEN={result.access_token}")
        click.echo(f"# 该令牌将在 {_format_datetime(result.expires_at)} 过期")

    click.echo("\n完成后即可运行 `dplk <PATH>` 来生成共享链接。")


def _perform_auth_flow(
    app_key: Optional[str],
    app_secret: Optional[str],
    scopes: Iterable[str],
    no_browser: bool,
) -> AuthResult:
    load_dotenv()

    resolved_app_key = (app_key or os.getenv("DROPBOX_APP_KEY", "")).strip()
    resolved_app_secret = (app_secret or os.getenv("DROPBOX_APP_SECRET", "")).strip()

    if not resolved_app_key:
        resolved_app_key = click.prompt("Dropbox app key", type=str)
    if not resolved_app_secret:
        resolved_app_secret = click.prompt("Dropbox app secret", type=str, hide_input=True)

    scope_list = _scopes_to_list(scopes)

    click.echo("\n=== Dropbox OAuth Setup ===\n")
    click.echo("Requesting the following scopes:")
    for scope in scope_list:
        click.echo(f"  - {scope}")

    flow = DropboxOAuth2FlowNoRedirect(
        consumer_key=resolved_app_key,
        consumer_secret=resolved_app_secret,
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
        raise click.ClickException(f"授权流程状态无效，请重试。详情: {exc}") from exc
    except NotApprovedException as exc:
        raise click.ClickException("授权已取消。") from exc
    except ProviderException as exc:
        raise click.ClickException(f"Dropbox 授权失败: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(f"授权失败: {exc}") from exc

    refresh_token = getattr(oauth_result, "refresh_token", None)
    if not refresh_token:
        raise click.ClickException("未返回 refresh token，请确认应用启用了 offline access。")

    access_token = getattr(oauth_result, "access_token", None)
    expires_at = getattr(oauth_result, "expires_at", None)

    return AuthResult(
        app_key=resolved_app_key,
        app_secret=resolved_app_secret,
        refresh_token=refresh_token,
        access_token=access_token,
        expires_at=expires_at,
        scopes=scope_list,
    )


def _should_trigger_auth_for_config_error(error: ConfigError) -> bool:
    message = str(error)
    credential_markers = (
        "Missing DROPBOX_APP_KEY",
        "Missing DROPBOX_APP_SECRET",
        "Missing DROPBOX_REFRESH_TOKEN",
    )
    return any(marker in message for marker in credential_markers)


def _attempt_auto_auth(reason: str) -> bool:
    click.echo("\n⚠️ 检测到 Dropbox 凭据不可用，自动触发 `dplk auth` 流程。", err=True)
    click.echo(f"原因：{reason}", err=True)

    try:
        result = _perform_auth_flow(app_key=None, app_secret=None, scopes=(), no_browser=False)
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        return False
    except Exception as exc:  # pragma: no cover
        click.echo(f"自动触发 OAuth 流程失败：{exc}", err=True)
        return False

    _apply_auth_result_to_env(result)
    _print_auth_success(result)
    click.echo("\n已更新当前会话中的 OAuth 凭据，正在重新尝试生成链接…\n", err=True)
    return True


@click.group(
    cls=DefaultGroup,
    default_command="link",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", type=click.Path(dir_okay=False, writable=True), help="Log file path")
@click.option("--no-copy", is_flag=True, help="Do not copy link to clipboard")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: str | None, no_copy: bool) -> None:
    """Generate Dropbox shared links or manage authentication."""

    ctx.ensure_object(dict)
    ctx.obj.update({"verbose": verbose, "log_file": log_file, "no_copy": no_copy})


@cli.command("link", hidden=True)
@click.argument("path", type=click.Path(path_type=Path))
@click.pass_context
def link_cmd(ctx: click.Context, path: Path) -> None:
    opts = ctx.obj or {}
    exit_code = _run_generate(path, opts.get("verbose", False), opts.get("log_file"), opts.get("no_copy", False))
    ctx.exit(exit_code)


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
    try:
        result = _perform_auth_flow(app_key=app_key, app_secret=app_secret, scopes=scopes, no_browser=no_browser)
    except click.ClickException as exc:
        raise exc
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(f"授权失败: {exc}") from exc

    _apply_auth_result_to_env(result)
    _print_auth_success(result)


@cli.command(name="check-tree", help="Validate the repository against the project-structure contract.")
def check_tree_cmd() -> None:
    issues = validate_structure()
    if not _print_structure_issues(issues):
        raise click.ClickException("项目结构存在问题，请运行 `dplk normalize` 后再试。")


@cli.command(help="Create missing folders and normalize the repository layout.")
def normalize() -> None:
    try:
        changes = normalize_structure()
    except StructureIssue as exc:  # pragma: no cover - manual intervention
        raise click.ClickException(str(exc)) from exc

    if not changes:
        click.echo("✅ 项目结构已符合要求，无需修改。")
    else:
        click.echo("✅ 已应用以下修复：")
        for change in changes:
            click.echo(f"  - {change}")


@cli.command(name="check-env", help="Verify mandatory Dropbox environment variables.")
def check_env_cmd() -> None:
    status = validate_env()
    if not _print_env_report(status):
        raise click.ClickException("环境变量配置不完整。")


@cli.command(help="Run structure and environment diagnostics in one go.")
def doctor() -> None:
    issues = validate_structure()
    status = validate_env()

    structure_ok = _print_structure_issues(issues)
    env_ok = _print_env_report(status)

    if not (structure_ok and env_ok):
        raise click.ClickException("诊断失败，请按照提示修复问题。")

    click.echo("🎉 所有检查均通过，可放心使用。")


@cli.group(help="Legacy diagnostic helpers.")
def diagnostics() -> None:
    """Run the legacy diagnostics bundled with the project."""


@diagnostics.command("permissions", help="Check Dropbox sharing permissions.")
@click.option("--path", "target_path", help="Dropbox path to test. Defaults to /README.md.")
def diagnostics_permissions(target_path: Optional[str]) -> None:
    success = run_permissions_check(target_path=target_path)
    if not success:
        raise click.ClickException("权限检查失败。")


@diagnostics.command("suite", help="Run the full diagnosis suite.")
@click.option("--path", "target_path", help="Dropbox path to test.")
def diagnostics_suite(target_path: Optional[str]) -> None:
    success = run_diagnosis_suite(target_path=target_path)
    if not success:
        raise click.ClickException("诊断套件检测到问题。")


@diagnostics.command("auth-debug", help="Run advanced authentication debug steps.")
@click.option("--path", "target_path", help="Dropbox path to test.")
def diagnostics_auth_debug(target_path: Optional[str]) -> None:
    success = run_auth_debug(test_path=target_path)
    if not success:
        raise click.ClickException("认证调试失败，请检查输出。")


main = cli


if __name__ == "__main__":  # pragma: no cover
    main()
