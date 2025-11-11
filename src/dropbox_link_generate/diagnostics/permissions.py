"""Diagnose Dropbox permission scopes."""

from __future__ import annotations

from typing import Optional

from dropbox.exceptions import ApiError, AuthError

from .common import build_client, load_credentials


def _default_target() -> str:
    return "/README.md"


def check_permissions(target_path: Optional[str] = None) -> bool:
    """Replicate the legacy `check_permissions.py` script as a callable."""

    creds = load_credentials()

    if not creds.app_key or not creds.app_secret or not creds.refresh_token:
        print("❌ Error: Missing OAuth credentials in environment/.env")
        print("   Required variables: DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN")
        return False

    print("=== Dropbox Permissions Checker ===")
    if creds.access_token:
        print(f"Access token length: {len(creds.access_token)}")
        print(f"Access token prefix: {creds.access_token[:30]}...")
    else:
        print("No cached short-lived access token found; SDK will refresh automatically.")

    target = target_path or _default_target()

    try:
        dbx = build_client(creds)

        print("\n1. Testing basic authentication...")
        user_result = dbx.users_get_current_account()
        print(f"✅ Auth successful: {user_result.name.display_name} ({user_result.email})")

        print("\n2. Testing sharing.read permission...")
        try:
            dbx.sharing_list_shared_links(path=target, direct_only=True)
            print("✅ sharing.read permission: OK")
        except AuthError as err:
            _explain_permission_error(err, "sharing.read")

        print("\n3. Testing sharing.write permission...")
        try:
            from dropbox.sharing import RequestedVisibility, SharedLinkSettings

            settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
            res = dbx.sharing_create_shared_link_with_settings(path=target, settings=settings)
            print("✅ sharing.write permission: OK")
            print(f"   Created test link: {res.url}")
        except AuthError as err:
            _explain_permission_error(err, "sharing.write")
        except ApiError as err:
            if hasattr(err, "error") and "path" in str(err.error).lower():
                print("✅ sharing.write permission: OK (file doesn't exist, but permission is present)")
            else:
                print(f"❌ sharing.write permission: UNCLEAR - {err}")

        print("\n=== Summary ===")
        print("If you see any MISSING permissions above:")
        print("1. Go to https://www.dropbox.com/developers/apps")
        print("2. Select your app and go to Permissions")
        print("3. Add the missing permissions:")
        print("   - sharing.read (for listing existing shared links)")
        print("   - sharing.write (for creating shared links)")
        print("4. Click 'Submit' and re-run your OAuth flow")
        print("5. Update DROPBOX_REFRESH_TOKEN in your .env file")

        return True

    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        print(f"❌ Authentication failed: {exc}")
        print(f"Error type: {type(exc).__name__}")
        return False


def _explain_permission_error(error: AuthError, scope: str) -> None:
    if hasattr(error, "error") and hasattr(error.error, "missing_scope"):
        missing = error.error.missing_scope
        if scope in str(missing):
            print(f"❌ {scope} permission: MISSING")
            print(f"   Required for: {'listing' if scope == 'sharing.read' else 'creating'} shared links")
            return
    print(f"❌ {scope} permission: ERROR - {error}")
