"""Shared settings and server management for Orzo."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
PORT = int(os.environ.get("ORZO_PORT", "4977"))
URL = "http://127.0.0.1:%d/" % PORT
SCRIPTS = Path(__file__).resolve().parent


def data_dir():
    if os.environ.get("ORZO_DIR"):
        return Path(os.environ["ORZO_DIR"]).expanduser()
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "orzo"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", str(home))) / "orzo"
    return Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))) / "orzo"


DATA_DIR = data_dir()
STORE = DATA_DIR / "turns.jsonl"


def _request(path, method="GET", timeout=0.5):
    req = urllib.request.Request(URL.rstrip("/") + path, method=method, headers={"X-Orzo": "1"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def running_version():
    """Orzo version on the port, "foreign" if something else holds it, None if free."""
    try:
        return json.loads(_request("/api/version")).get("version") or "foreign"
    except urllib.error.HTTPError:
        return "foreign"
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _wait_for(check, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check():
            return True
        time.sleep(0.1)
    return False


def ensure_server():
    """Start the board server unless this version is already running. Returns True if up."""
    current = running_version()
    if current == VERSION:
        return True
    if current == "foreign":
        return False
    if current is not None:
        # An older Orzo from before a plugin update: swap it for this one.
        try:
            _request("/api/shutdown", method="POST")
        except (urllib.error.URLError, OSError):
            pass
        _wait_for(lambda: running_version() is None, 3)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = open(str(DATA_DIR / "server.log"), "ab")
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True  # outlive the hook that started it
    subprocess.Popen([sys.executable, "-I", str(SCRIPTS / "server.py")], **kwargs)
    log.close()
    return _wait_for(lambda: running_version() == VERSION, 3)
