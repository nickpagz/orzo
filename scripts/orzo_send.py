#!/usr/bin/env python3
"""Send text or a file to the Orzo board as a card, exactly as given.

    orzo_send.py --label "README.md" --file README.md
    orzo_send.py --label "Reply to Sam" --lang text <<'ORZO_EOF'
    ...text...
    ORZO_EOF

When run from a Claude Code session, the card joins that session's current
reply on the board.
"""
import argparse
import glob
import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orzo_common import DATA_DIR, STORE, ensure_server  # noqa: E402
from orzo_hook import project_name, prompt_text, read_turn  # noqa: E402

PROSE_LANGS = {"", "text", "txt", "markdown", "md"}


def find_transcript(session_id):
    config = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    matches = glob.glob(os.path.join(config, "projects", "*", session_id + ".jsonl"))
    return Path(matches[0]) if matches else None


def main():
    parser = argparse.ArgumentParser(description="Send text or a file to the Orzo board.")
    parser.add_argument("--label", default="", help="short title shown on the card")
    parser.add_argument("--file", help="send this file's contents (otherwise read stdin)")
    parser.add_argument("--lang", help="language tag, e.g. markdown, text, bash (default: from file extension)")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file).expanduser()
        text = path.read_text(encoding="utf-8")
        label = args.label or path.name
        lang = args.lang if args.lang is not None else path.suffix.lstrip(".").lower()
    else:
        text = sys.stdin.read()
        label = args.label
        lang = args.lang or "text"
        # A heredoc always ends with one newline the sender didn't mean to include.
        if text.endswith("\n"):
            text = text[:-1]
    if not text.strip():
        print("Nothing sent: the text was empty.")
        return 1

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    prompt, title = None, ""
    transcript = find_transcript(session_id) if session_id else None
    if transcript:
        try:
            prompt, _, title = read_turn(transcript)
        except OSError:
            pass

    cwd = os.getcwd()
    entry = {
        "id": (prompt or {}).get("uuid") or "sent-" + uuid.uuid4().hex,
        "source": "sent",
        "session_id": session_id,
        "session_title": title or "",
        "cwd": cwd,
        "project": project_name(cwd),
        "prompt": prompt_text(prompt).strip()[:300] if prompt else "",
        "ts": time.time(),
        "snippets": [{
            "lang": lang,
            "label": label,
            "code": text,
            "sent": True,
            "wrap": lang in PROSE_LANGS,
        }],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(STORE), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    ensure_server()
    lines = text.count("\n") + 1
    print("Sent to Orzo: %s (%d line%s)" % (label or "untitled", lines, "" if lines == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
