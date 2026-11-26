#!/usr/bin/env python3
"""Open the Orzo board, as a standalone Chrome/Chromium window when one is available."""
import os
import shutil
import subprocess
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orzo_common import PORT, URL, ensure_server  # noqa: E402

CHROMIUM_BINARIES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge")


def open_app_window():
    """Try a chromeless app window. Returns True if one was launched."""
    if sys.platform == "darwin":
        for app in ("Google Chrome", "Chromium", "Microsoft Edge", "Brave Browser"):
            if subprocess.call(["open", "-Ra", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                return subprocess.call(["open", "-na", app, "--args", "--app=" + URL]) == 0
        return False
    for name in CHROMIUM_BINARIES + ("chrome", "msedge"):
        path = shutil.which(name)
        if path:
            subprocess.Popen([path, "--app=" + URL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    return False


def main():
    if not ensure_server():
        print("Orzo could not start: port %d is in use by another program. Set ORZO_PORT to use a different port." % PORT)
        return 1
    if not open_app_window():
        webbrowser.open(URL)
    print("Orzo is open at %s" % URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
