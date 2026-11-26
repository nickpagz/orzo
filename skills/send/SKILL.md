---
name: send
description: Send text to the user's Orzo board as a card they can copy exactly as written. Use whenever the user asks to send, put, drop or push something "to Orzo" or "in Orzo": a reply, a message draft, a block of prose, markdown, a file's contents, a command, or anything else they want to copy cleanly without terminal wrapping or indents.
argument-hint: [what to send]
---

# Send to Orzo

The user wants this content on their Orzo board so they can copy it with one click, byte for byte. They are not asking to see it in the chat.

The send script is at `../../scripts/orzo_send.py`, relative to this skill's base directory (shown above as "Base directory for this skill"). Build the absolute path from that, and run it with `python3 -I`.

## An existing file

Send the file itself, so nothing is retyped:

```bash
python3 -I "<base dir>/../../scripts/orzo_send.py" --file "path/to/README.md" --label "README.md"
```

The language tag comes from the file extension. Pass `--lang` to override it.

## Text you write or reuse

Pass it on stdin with a quoted heredoc, so the shell leaves every character alone:

```bash
python3 -I "<base dir>/../../scripts/orzo_send.py" --label "Reply to the client" --lang markdown <<'ORZO_EOF'
...the exact text...
ORZO_EOF
```

- Use `--lang markdown` for markdown, `--lang text` for plain prose, or the language name for code (`bash`, `json`, `php`...).
- Write the content exactly as it should be pasted. Don't indent it to match the command, don't wrap long lines, and don't add code fences unless they are part of the content.
- Keep `--label` short (2-6 words), saying what the item is.
- If the text could contain a line that is exactly `ORZO_EOF`, pick a different delimiter.
- To send several separate items, run the command once per item, in the order the user will use them.

## After sending

Reply with one line naming what you sent, such as "Sent to Orzo: README.md (42 lines)". Don't repeat the content in the chat unless the user asks for it there too: it would show up twice on the board.

If the script says the text was empty or the board couldn't start, tell the user what it printed.
