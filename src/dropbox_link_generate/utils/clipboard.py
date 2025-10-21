import shutil
import subprocess
import sys

try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover - optional dependency failures handled at runtime
    pyperclip = None  # type: ignore


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard.

    Returns True if copying succeeded, False otherwise. Will never raise.
    Strategy:
    - Try pyperclip if available
    - Fallback to pbcopy (macOS)
    - Fallback to xclip/xsel (Linux)
    """
    # Try pyperclip if import succeeded
    if pyperclip is not None:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass

    # macOS fallback
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        try:
            proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return proc.returncode == 0
        except Exception:
            return False

    # Linux fallbacks
    for cmd in ("xclip", "xsel"):
        if shutil.which(cmd):
            try:
                if cmd == "xclip":
                    proc = subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text.encode("utf-8"),
                        check=True,
                    )
                else:
                    proc = subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text.encode("utf-8"),
                        check=True,
                    )
                return proc.returncode == 0
            except Exception:
                continue

    return False

