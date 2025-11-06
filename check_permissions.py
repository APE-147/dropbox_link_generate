#!/usr/bin/env python3
"""
Dropbox Permissions Checker Tool
Quick utility to verify Dropbox OAuth credentials and permissions
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import dropbox
from dropbox.exceptions import AuthError, ApiError


def check_dropbox_permissions():
    """Check if the Dropbox OAuth credentials have required permissions."""

    load_dotenv()
    app_key = os.getenv("DROPBOX_APP_KEY", "").strip()
    app_secret = os.getenv("DROPBOX_APP_SECRET", "").strip()
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN", "").strip()
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN", "").strip() or None

    if not app_key or not app_secret or not refresh_token:
        print("❌ Error: Missing OAuth credentials in environment/.env")
        print("   Required variables: DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN")
        return False

    print("=== Dropbox Permissions Checker ===")
    if access_token:
        print(f"Access token length: {len(access_token)}")
        print(f"Access token prefix: {access_token[:30]}...")
    else:
        print("No cached short-lived access token found; SDK will refresh automatically.")

    try:
        dbx = dropbox.Dropbox(
            app_key=app_key,
            app_secret=app_secret,
            oauth2_refresh_token=refresh_token,
            oauth2_access_token=access_token,
            timeout=10.0,
        )

        print("\n1. Testing basic authentication...")
        user_result = dbx.users_get_current_account()
        print(f"✅ Auth successful: {user_result.name.display_name} ({user_result.email})")

        print("\n2. Testing sharing.read permission...")
        try:
            res = dbx.sharing_list_shared_links(path="/README.md", direct_only=True)
            print("✅ sharing.read permission: OK")
        except AuthError as e:
            if hasattr(e, 'error') and hasattr(e.error, 'missing_scope'):
                missing = e.error.missing_scope
                if 'sharing.read' in str(missing):
                    print("❌ sharing.read permission: MISSING")
                    print("   Required for: listing existing shared links")
                else:
                    print(f"❌ sharing.read permission: ERROR - {e}")
            else:
                print(f"❌ sharing.read permission: ERROR - {e}")

        print("\n3. Testing sharing.write permission...")
        try:
            from dropbox.sharing import RequestedVisibility, SharedLinkSettings

            settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
            res = dbx.sharing_create_shared_link_with_settings(path="/README.md", settings=settings)
            print("✅ sharing.write permission: OK")
            print(f"   Created test link: {res.url}")
        except AuthError as e:
            if hasattr(e, 'error') and hasattr(e.error, 'missing_scope'):
                missing = e.error.missing_scope
                if 'sharing.write' in str(missing):
                    print("❌ sharing.write permission: MISSING")
                    print("   Required for: creating new shared links")
                else:
                    print(f"❌ sharing.write permission: ERROR - {e}")
            else:
                print(f"❌ sharing.write permission: ERROR - {e}")
        except ApiError as e:
            if hasattr(e, 'error') and 'path' in str(e.error).lower():
                print("✅ sharing.write permission: OK (file doesn't exist, but permission is present)")
            else:
                print(f"❌ sharing.write permission: UNCLEAR - {e}")

        print("\n=== Summary ===")
        print("If you see any MISSING permissions above:")
        print("1. Go to https://www.dropbox.com/developers/apps")
        print("2. Select your app and go to Permissions")
        print("3. Add the missing permissions:")
        print("   - sharing.read (for listing shared links)")
        print("   - sharing.write (for creating shared links)")
        print("4. Click 'Submit' and re-run your OAuth flow")
        print("5. Update DROPBOX_REFRESH_TOKEN in your .env file")

        return True

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


if __name__ == "__main__":
    check_dropbox_permissions()
