#!/usr/bin/env python3
"""
诊断Dropbox API错误的测试脚本
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import dropbox
from dropbox.exceptions import ApiError, AuthError, BadInputError, HttpError

# 加载环境变量
load_dotenv()


def _load_oauth_credentials():
    app_key = os.getenv('DROPBOX_APP_KEY', '').strip()
    app_secret = os.getenv('DROPBOX_APP_SECRET', '').strip()
    refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN', '').strip()
    access_token = os.getenv('DROPBOX_ACCESS_TOKEN', '').strip() or None
    return app_key, app_secret, refresh_token, access_token


def _build_client():
    app_key, app_secret, refresh_token, access_token = _load_oauth_credentials()
    missing = []
    if not app_key:
        missing.append('DROPBOX_APP_KEY')
    if not app_secret:
        missing.append('DROPBOX_APP_SECRET')
    if not refresh_token:
        missing.append('DROPBOX_REFRESH_TOKEN')

    if missing:
        print(f"❌ 错误：未找到 {'、'.join(missing)}")
        print("💡 解决方案：运行 `dplk auth` 或将 OAuth 凭据添加到 .env")
        return None

    return dropbox.Dropbox(
        app_key=app_key,
        app_secret=app_secret,
        oauth2_refresh_token=refresh_token,
        oauth2_access_token=access_token,
        timeout=10.0,
    )


def test_basic_auth():
    """测试基本认证"""
    print("=== 测试基本认证 ===")

    try:
        dbx = _build_client()
        if dbx is None:
            return False
        result = dbx.users_get_current_account()
        print(f"✅ 认证成功：{result.name.display_name} ({result.email})")
        return True
    except Exception as e:
        print(f"❌ 认证失败：{type(e).__name__}: {e}")
        return False


def test_file_metadata():
    """测试文件元数据访问"""
    print("\n=== 测试文件元数据访问 ===")
    target_file = "/-Code-/Scripts/system/data-storage/dropbox_link_generate/docs/REQUIRES.md"

    try:
        dbx = _build_client()
        if dbx is None:
            return False
        metadata = dbx.files_get_metadata(target_file)
        print(f"✅ 文件元数据访问成功：{metadata.name}")
        return True
    except BadInputError as e:
        if "not permitted to access this endpoint" in str(e):
            print("❌ 权限不足：缺少 files.metadata.read 权限")
            print("💡 解决方案：在Dropbox App Console中启用 files.metadata.read 权限")
        else:
            print(f"❌ 输入错误：{e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误：{type(e).__name__}: {e}")
        return False


def test_sharing_read():
    """测试共享链接读取"""
    print("\n=== 测试共享链接读取 ===")
    target_file = "/-Code-/Scripts/system/data-storage/dropbox_link_generate/docs/REQUIRES.md"

    try:
        dbx = _build_client()
        if dbx is None:
            return False
        result = dbx.sharing_list_shared_links(path=target_file, direct_only=True)
        print(f"✅ 共享链接读取成功：找到 {len(result.links) if result.links else 0} 个现有链接")
        return True
    except BadInputError as e:
        if "not permitted to access this endpoint" in str(e):
            print("❌ 权限不足：缺少 sharing.read 权限")
            print("💡 解决方案：在Dropbox App Console中启用 sharing.read 权限")
        else:
            print(f"❌ 输入错误：{e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误：{type(e).__name__}: {e}")
        return False


def test_sharing_write():
    """测试共享链接创建"""
    print("\n=== 测试共享链接创建 ===")
    target_file = "/-Code-/Scripts/system/data-storage/dropbox_link_generate/docs/REQUIRES.md"

    try:
        dbx = _build_client()
        if dbx is None:
            return False
        from dropbox.sharing import RequestedVisibility, SharedLinkSettings

        settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
        result = dbx.sharing_create_shared_link_with_settings(path=target_file, settings=settings)
        print(f"✅ 共享链接创建成功：{result.url}")
        return True
    except BadInputError as e:
        if "not permitted to access this endpoint" in str(e):
            print("❌ 权限不足：缺少 sharing.write 权限")
            print("💡 解决方案：在Dropbox App Console中启用 sharing.write 权限")
        else:
            print(f"❌ 输入错误：{e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误：{type(e).__name__}: {e}")
        return False


def test_app_configuration():
    """测试应用配置"""
    print("\n=== 应用配置检查 ===")

    required_vars = ['DROPBOX_APP_KEY', 'DROPBOX_APP_SECRET', 'DROPBOX_REFRESH_TOKEN', 'DROPBOX_ROOT']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var, '').strip()
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 已配置")

    if missing_vars:
        print(f"❌ 缺少环境变量：{', '.join(missing_vars)}")
        return False

    dropbox_root = Path(os.getenv('DROPBOX_ROOT')).expanduser()
    if dropbox_root.exists() and dropbox_root.is_dir():
        print(f"✅ Dropbox根目录：{dropbox_root}")
    else:
        print(f"❌ Dropbox根目录不存在：{dropbox_root}")
        return False

    return True


def main():
    """主函数"""
    print("Dropbox API 诊断工具")
    print("=" * 50)

    config_ok = test_app_configuration()
    if not config_ok:
        print("\n❌ 应用配置有问题，请先修复配置")
        return

    auth_ok = test_basic_auth()
    if not auth_ok:
        print("\n❌ 认证失败，请检查 OAuth 凭据或重新运行 dplk auth")
        return

    tests = [
        ("文件元数据权限", test_file_metadata),
        ("共享读取权限", test_sharing_read),
        ("共享写入权限", test_sharing_write),
    ]

    results = []
    for test_name, test_func in tests:
        results.append((test_name, test_func()))

    print("\n" + "=" * 50)
    print("诊断总结：")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("✅ 所有测试通过！应用配置正确")
    else:
        print("❌ 发现权限问题：")
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")

        print("\n💡 解决步骤：")
        print("1. 访问 https://www.dropbox.com/developers/apps")
        print("2. 找到您的应用并检查权限设置")
        print("3. 确认已启用 files.metadata.read / sharing.read / sharing.write")
        print("4. 重新运行 `dplk auth` 生成新的 refresh token")
        print("5. 更新 .env 文件中的 DROPBOX_REFRESH_TOKEN 并重试")


if __name__ == "__main__":
    main()
