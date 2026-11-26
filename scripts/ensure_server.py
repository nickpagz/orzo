#!/usr/bin/env python3
"""Orzo SessionStart hook: make sure the board server is running.

Prints nothing (SessionStart output would be added to Claude's context) and
always exits 0 so a problem here never gets in the way of a session.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from orzo_common import ensure_server
        ensure_server()
    except Exception:
        pass
    sys.exit(0)
