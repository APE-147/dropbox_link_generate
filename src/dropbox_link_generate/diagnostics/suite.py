"""Interactive diagnosis suite used by CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

import os
from pathlib import Path

from dropbox.exceptions import BadInputError

from .common import build_client, load_credentials


DEFAULT_TARGET = "/-Code-/Scripts/system/data-storage/dropbox_link_generate/docs/REQUIRES.md"


@dataclass
class DiagnosisStep:
    name: str
    handler: Callable[[], bool]


class DiagnosisSuite:
    """Port of the legacy `test_diagnosis.py` script."""

    def __init__(self, target_path: str | None = None) -> None:
        self.target_path = target_path or DEFAULT_TARGET
        self.creds = load_credentials()
        self.steps: List[DiagnosisStep] = [
            DiagnosisStep("文件元数据权限", self.test_file_metadata),
            DiagnosisStep("共享读取权限", self.test_sharing_read),
            DiagnosisStep("共享写入权限", self.test_sharing_write),
        ]

    def run(self) -> bool:
        print("Dropbox API 诊断工具")
        print("=" * 50)

        if not self.test_app_configuration():
            print("\n❌ 应用配置有问题，请先修复配置")
            return False

        if not self.test_basic_auth():
            print("\n❌ 认证失败，请检查 OAuth 凭据或重新运行 dplk auth")
            return False

        results: List[Tuple[str, bool]] = []
        for step in self.steps:
            results.append((step.name, step.handler()))

        print("\n" + "=" * 50)
        print("诊断总结：")

        all_passed = all(result for _, result in results)
        if all_passed:
            print("✅ 所有测试通过！应用配置正确")
        else:
            print("❌ 发现权限问题：")
            for name, passed in results:
                status = "✅ 通过" if passed else "❌ 失败"
                print(f"  {name}: {status}")

            print("\n💡 解决步骤：")
            print("1. 访问 https://www.dropbox.com/developers/apps")
            print("2. 找到您的应用并检查权限设置")
            print("3. 确认已启用 files.metadata.read / sharing.read / sharing.write")
            print("4. 重新运行 `dplk auth` 生成新的 refresh token")
            print("5. 更新 .env 文件中的 DROPBOX_REFRESH_TOKEN 并重试")

        return all_passed

    def test_app_configuration(self) -> bool:
        print("\n=== 应用配置检查 ===")
        required_vars = ["DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN", "DROPBOX_ROOT"]
        missing_vars: list[str] = []

        for var in required_vars:
            value = os.getenv(var, "").strip()
            if value:
                print(f"✅ {var}: 已配置")
            else:
                print(f"❌ 缺少环境变量：{var}")
                missing_vars.append(var)

        if missing_vars:
            return False

        dropbox_root = Path(os.getenv("DROPBOX_ROOT", "")).expanduser()
        if dropbox_root.exists() and dropbox_root.is_dir():
            print(f"✅ Dropbox根目录：{dropbox_root}")
            return True

        print(f"❌ Dropbox根目录不存在：{dropbox_root}")
        return False

    def test_basic_auth(self) -> bool:
        print("=== 测试基本认证 ===")
        try:
            client = build_client(self.creds)
            result = client.users_get_current_account()
            print(f"✅ 认证成功：{result.name.display_name} ({result.email})")
            self.client = client
            return True
        except Exception as exc:  # pragma: no cover
            print(f"❌ 认证失败：{type(exc).__name__}: {exc}")
            return False

    def _ensure_client(self):
        if not hasattr(self, "client"):
            self.client = build_client(self.creds)
        return self.client

    def test_file_metadata(self) -> bool:
        print("\n=== 测试文件元数据访问 ===")
        target_file = self.target_path

        try:
            client = self._ensure_client()
            metadata = client.files_get_metadata(target_file)
            print(f"✅ 文件元数据访问成功：{metadata.name}")
            return True
        except BadInputError as exc:
            if "not permitted to access this endpoint" in str(exc):
                print("❌ 权限不足：缺少 files.metadata.read 权限")
                print("💡 解决方案：在Dropbox App Console中启用 files.metadata.read 权限")
            else:
                print(f"❌ 输入错误：{exc}")
            return False
        except Exception as exc:  # pragma: no cover
            print(f"❌ 其他错误：{type(exc).__name__}: {exc}")
            return False

    def test_sharing_read(self) -> bool:
        print("\n=== 测试共享链接读取 ===")
        target_file = self.target_path

        try:
            client = self._ensure_client()
            result = client.sharing_list_shared_links(path=target_file, direct_only=True)
            print(f"✅ 共享链接读取成功：找到 {len(result.links) if result.links else 0} 个现有链接")
            return True
        except BadInputError as exc:
            if "not permitted to access this endpoint" in str(exc):
                print("❌ 权限不足：缺少 sharing.read 权限")
                print("💡 解决方案：在Dropbox App Console中启用 sharing.read 权限")
            else:
                print(f"❌ 输入错误：{exc}")
            return False
        except Exception as exc:  # pragma: no cover
            print(f"❌ 其他错误：{type(exc).__name__}: {exc}")
            return False

    def test_sharing_write(self) -> bool:
        print("\n=== 测试共享链接创建 ===")
        target_file = self.target_path

        try:
            client = self._ensure_client()
            from dropbox.sharing import RequestedVisibility, SharedLinkSettings

            settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
            result = client.sharing_create_shared_link_with_settings(path=target_file, settings=settings)
            print(f"✅ 共享链接创建成功：{result.url}")
            return True
        except BadInputError as exc:
            if "not permitted to access this endpoint" in str(exc):
                print("❌ 权限不足：缺少 sharing.write 权限")
                print("💡 解决方案：在Dropbox App Console中启用 sharing.write 权限")
            else:
                print(f"❌ 输入错误：{exc}")
            return False
        except Exception as exc:  # pragma: no cover
            print(f"❌ 其他错误：{type(exc).__name__}: {exc}")
            return False


def run_diagnosis_suite(target_path: str | None = None) -> bool:
    """Convenience wrapper used by the CLI."""

    suite = DiagnosisSuite(target_path=target_path)
    return suite.run()
