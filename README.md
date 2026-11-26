# Orzo

**Clean copies of the code blocks Claude writes.**

Copying a command out of a terminal often brings junk with it: line breaks where the text wrapped, indents from the layout, hidden characters you only find when the command fails. That's because Claude Code wraps and indents its replies to fit your window, so what's on screen isn't quite what Claude wrote.

Orzo skips the screen. Every time Claude finishes a reply, Orzo pulls out the code blocks exactly as written and shows them as cards on a small local board. Click **Copy**, and you get the real text.

![The Orzo board, showing two replies with numbered snippet cards and copy buttons](docs/screenshot.png)

- **In order.** Each reply's snippets are numbered in the order Claude gave them, labelled with the sentence just above each one. Newest reply on top.
- **Tracks your place.** A snippet's header is lightly tinted until you copy it, so in a multi-step reply you can see which ones you've run.
- **Every session, every project.** Filter by project when you have several sessions going.
- **Nothing to remember.** It's automatic: no special prompts, no copying from the terminal.

## Install

In Claude Code:

```
/plugin marketplace add nickpagz/orzo
/plugin install orzo@orzo
```

Then restart Claude Code. Orzo starts its board when a session starts, and captures snippets from then on.

**Requirements:** Python 3.8 or later available as `python3`. Nothing else to install: Orzo uses only the Python standard library.

## Use

Open the board with:

```
/orzo:open
```

It opens as its own window when Chrome, Chromium, Edge or Brave is installed, and in your default browser otherwise. You can also bookmark http://127.0.0.1:4977.

**Tip for macOS:** to get a Dock or Spotlight launcher, run this once:

```bash
osacompile -o ~/Applications/Orzo.app -e 'do shell script "open -na \"Google Chrome\" --args --app=http://127.0.0.1:4977"'
```

## How it works

- A `Stop` hook runs when each reply finishes. It reads the reply from the session transcript, extracts the fenced code blocks in order, and appends them to a local file.
- A `SessionStart` hook makes sure the board server is running. The server listens on `127.0.0.1` only and serves a single page that checks for new snippets every couple of seconds.
- Both hooks exit quietly on any error, so Orzo can never block or break a session.

## Your data

Snippets often contain things like hostnames, paths or tokens, so Orzo keeps everything on your machine:

- Snippets are stored only on your computer, in a file readable only by you:
  - macOS: `~/Library/Application Support/orzo/`
  - Linux: `~/.local/share/orzo/` (or `$XDG_DATA_HOME/orzo/`)
  - Windows: `%APPDATA%\orzo\`
- The board is reachable only from your own machine (`127.0.0.1`), and it rejects requests from other websites, including DNS-rebinding tricks.
- Nothing is sent anywhere. Orzo has no network code beyond the local board.
- **Clear board** archives the current snippets to a dated file in the same folder. Delete those files whenever you like.

## Settings

| Environment variable | Default | What it does |
|---|---|---|
| `ORZO_PORT` | `4977` | Port for the local board |
| `ORZO_DIR` | see [Your data](#your-data) | Where snippets are stored |

## Uninstall

```
/plugin uninstall orzo@orzo
```

The board server stops at your next restart or logout. To remove your saved snippets as well, delete the data folder listed above.

## License

MIT
