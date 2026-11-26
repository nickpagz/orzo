#!/usr/bin/env python3
"""Orzo board server. Binds to 127.0.0.1 only.

GET  /                -> the board page
GET  /api/turns       -> saved turns, newest first (ETag'd so polling is cheap)
GET  /api/version     -> {"version": ...}, used to detect an already-running server
POST /api/clear       -> archive the current store and start empty
POST /api/shutdown    -> stop (used to swap in a newer version after a plugin update)
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orzo_common import DATA_DIR, PORT, STORE, VERSION  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent / "web" / "index.html"
ALLOWED_HOSTS = {"127.0.0.1:%d" % PORT, "localhost:%d" % PORT}


def load_turns():
    """One entry per reply: cards sent during it first, then its code blocks."""
    if not STORE.exists():
        return []
    merged = {}
    for line in STORE.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        turn = merged.setdefault(entry.get("id"), {"meta": entry, "sent": [], "reply": []})
        if entry.get("source") == "sent":
            turn["sent"].extend(entry.get("snippets", []))
        else:
            # A reply saved twice (hook fired again) keeps its latest version.
            turn["reply"] = entry.get("snippets", [])
            turn["meta"] = entry
    turns = [dict(t["meta"], snippets=t["sent"] + t["reply"]) for t in merged.values()]
    return sorted(turns, key=lambda t: t.get("ts", 0), reverse=True)


def store_etag():
    try:
        stat = STORE.stat()
    except FileNotFoundError:
        return '"empty"'
    return '"%d-%d"' % (stat.st_mtime_ns, stat.st_size)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def host_ok(self):
        # Rejects DNS-rebinding requests from web pages posing as localhost.
        if self.headers.get("Host") in ALLOWED_HOSTS:
            return True
        self.send_error(403)
        return False

    def send_body(self, status, body, content_type, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.host_ok():
            return
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.send_body(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/turns":
            etag = store_etag()
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            body = json.dumps({"turns": load_turns()}).encode("utf-8")
            self.send_body(200, body, "application/json", {"ETag": etag})
        elif path == "/api/version":
            self.send_body(200, json.dumps({"version": VERSION}).encode("utf-8"), "application/json")
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.host_ok():
            return
        # Custom header forces a CORS preflight, which we never approve.
        if self.headers.get("X-Orzo") != "1":
            self.send_error(403)
            return
        if self.path == "/api/clear":
            if STORE.exists():
                archive = DATA_DIR / ("turns-%s.jsonl" % time.strftime("%Y%m%d-%H%M%S"))
                os.replace(STORE, archive)
            self.send_body(200, b'{"ok":true}', "application/json")
        elif self.path == "/api/shutdown":
            self.send_body(200, b'{"ok":true}', "application/json")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
