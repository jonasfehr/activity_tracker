import platform
import subprocess

# Try to import pygetwindow, but be tolerant if it's not available on some systems
try:
    import pygetwindow as gw
except Exception:
    gw = None


def _osascript(cmd: str):
    try:
        out = subprocess.check_output(["osascript", "-e", cmd], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return None


def get_active_target():
    """Return a human-readable active window or application name, or None.

    Strategy:
    - Try pygetwindow's getActiveWindow() and return its title if available.
    - On macOS, fall back to `osascript` to query the frontmost application and window title.
    - Return None if nothing could be determined.
    """
    # Try pygetwindow first
    if gw is not None:
        try:
            win = gw.getActiveWindow()
            if win:
                title = getattr(win, "title", None) or str(win)
                if title and title.strip():
                    return title.strip()
        except Exception:
            # Fall through to platform-specific fallback
            pass

    # macOS fallback using AppleScript (osascript)
    if platform.system() == "Darwin":
        app = _osascript('tell application "System Events" to get name of first process whose frontmost is true')
        if app:
            # Try to get the front window title for that app
            window = _osascript(f'tell application "{app}" to get name of front window')
            if window:
                return f"{app} - {window}"
            return app

    # Other platforms: return None (could add more fallbacks if needed)
    return None
