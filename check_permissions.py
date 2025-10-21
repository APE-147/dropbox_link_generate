#!/usr/bin/env python3
"""
Dropbox Permissions Checker Tool
Quick utility to verify Dropbox API token permissions
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import dropbox
from dropbox.exceptions import AuthError, ApiError

def check_dropbox_permissions():
    """Check if the Dropbox token has required permissions."""

    # Load configuration
    load_dotenv()
    token = os.getenv("DROPBOX_TOKEN")

    if not token:
        print("❌ Error: DROPBOX_TOKEN not found in environment/.env")
        return False

    print("=== Dropbox Permissions Checker ===")
    print(f"Token length: {len(token)}")
    print(f"Token prefix: {token[:30]}...")

    try:
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(oauth2_access_token=token, timeout=10.0)

        # Test 1: Basic authentication
        print("\n1. Testing basic authentication...")
        user_result = dbx.users_get_current_account()
        print(f"✅ Auth successful: {user_result.name.display_name} ({user_result.email})")

        # Test 2: sharing.read permission (list shared links)
        print("\n2. Testing sharing.read permission...")
        try:
            # Try to list shared links for a common file
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

        # Test 3: sharing.write permission (create shared links)
        print("\n3. Testing sharing.write permission...")
        try:
            # Try to create a shared link for a test file (this might fail if file doesn't exist)
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
            # File doesn't exist, but we have the permission
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
        print("4. Click 'Submit' and regenerate your access token")
        print("5. Update DROPBOX_TOKEN in your .env file")

        return True

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    check_dropbox_permissions()