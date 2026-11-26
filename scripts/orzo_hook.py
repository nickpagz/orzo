#!/usr/bin/env python3
"""Orzo Stop hook: save the code blocks from the reply that just finished.

Reads the hook payload on stdin, collects every assistant text block written
since the last real user prompt, extracts the fenced code blocks in order and
appends them as one "turn" to the snippet store. Never blocks or fails the
session: any error is swallowed and the hook exits 0.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orzo_common import DATA_DIR, STORE  # noqa: E402

MAX_STORE_BYTES = 5_000_000
KEEP_TURNS = 300

OPEN_FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def is_prompt(entry):
    """True for a user entry the person typed, not a tool result or meta note."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        kinds = {block.get("type") for block in content if isinstance(block, dict)}
        return "tool_result" not in kinds and "text" in kinds
    return False


def prompt_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return "\n".join(
        block.get("text", "") for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def load_entries(raw, partial_first_line):
    lines = raw.split(b"\n")
    if partial_first_line:
        lines = lines[1:]
    entries = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def read_turn(transcript):
    """Return (prompt_entry, [assistant texts in order], session title)."""
    size = transcript.stat().st_size
    # Read progressively larger tails so long sessions stay cheap.
    for tail in (1 << 21, 1 << 24, size):
        start = max(0, size - tail)
        with open(transcript, "rb") as handle:
            handle.seek(start)
            entries = load_entries(handle.read(), partial_first_line=start > 0)

        title = None
        texts = []
        prompt = None
        for entry in reversed(entries):
            kind = entry.get("type")
            if kind == "ai-title" and title is None:
                title = entry.get("aiTitle")
            if prompt is not None:
                if title is not None:
                    break
                continue
            if entry.get("isSidechain"):
                continue
            if kind == "assistant":
                content = (entry.get("message") or {}).get("content") or []
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                for block in reversed(content):
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
            elif is_prompt(entry):
                prompt = entry
        if prompt is not None or start == 0:
            texts.reverse()
            return prompt, texts, title
    return None, [], None


def clean_label(line):
    line = LIST_MARKER.sub("", line.strip())
    line = line.lstrip("#> ").strip()
    line = line.replace("**", "").replace("__", "").replace("`", "")
    if len(line) > 200:
        line = line[:197].rstrip() + "..."
    return line


def extract_blocks(text):
    """Fenced code blocks in order, each with the prose line just above it."""
    blocks = []
    lines = text.split("\n")
    last_prose = ""
    i = 0
    while i < len(lines):
        match = OPEN_FENCE.match(lines[i])
        if not match or ("`" in match.group("info") and match.group("fence")[0] == "`"):
            if lines[i].strip():
                last_prose = lines[i]
            i += 1
            continue

        indent = len(match.group("indent").expandtabs(4))
        fence = match.group("fence")
        close = re.compile(r"^[ \t]*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$")
        body = []
        i += 1
        while i < len(lines) and not close.match(lines[i]):
            line = lines[i]
            # Drop the fence's own indentation (fences nested inside lists).
            strip = 0
            while strip < indent and strip < len(line) and line[strip] == " ":
                strip += 1
            body.append(line[strip:])
            i += 1
        i += 1  # skip closing fence (or run off the end of an unclosed block)

        code = "\n".join(body).strip("\n")
        if code.strip():
            info = match.group("info").strip().split()
            blocks.append({
                "lang": info[0] if info else "",
                "label": clean_label(last_prose),
                "code": code,
            })
        last_prose = ""
    return blocks


def trim_store():
    if not STORE.exists() or STORE.stat().st_size <= MAX_STORE_BYTES:
        return
    lines = STORE.read_text(encoding="utf-8").splitlines()[-KEEP_TURNS:]
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, STORE)


def main():
    payload = json.load(sys.stdin)
    transcript = Path(payload.get("transcript_path") or "")
    if not transcript.is_file():
        return

    prompt, texts, title = read_turn(transcript)
    last = (payload.get("last_assistant_message") or "").strip()
    # The final message can land after the hook reads the transcript.
    if last and not any(last in text or text.strip() in last for text in texts if text.strip()):
        texts.append(last)

    snippets = []
    for text in texts:
        snippets.extend(extract_blocks(text))
    if not snippets:
        return

    cwd = payload.get("cwd") or ""
    project = "~" if cwd.rstrip("/") == str(Path.home()) else os.path.basename(cwd.rstrip("/")) or cwd
    turn = {
        "id": (prompt or {}).get("uuid") or "%s-%d" % (payload.get("session_id", ""), time.time()),
        "session_id": payload.get("session_id", ""),
        "session_title": title or "",
        "cwd": cwd,
        "project": project,
        "prompt": prompt_text(prompt).strip()[:300] if prompt else "",
        "ts": time.time(),
        "snippets": snippets,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(STORE), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(turn, ensure_ascii=False) + "\n")
    trim_store()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
