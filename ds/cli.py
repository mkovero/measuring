import json
import sys
from datetime import datetime, timezone

from .session import (
    require_active_session,
    get_active_session_name,
    get_session_dir,
    get_ds_dir,
    load_session,
)
from .files import list_ac_files, list_ds_files, add_file, remove_file


def _fmt_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} K"
    else:
        return f"{size / (1024 * 1024):.1f} M"


def _fmt_mtime(path):
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def cmd_status():
    name = require_active_session()
    session_dir = get_session_dir(name)
    ds_dir = get_ds_dir(name)

    print(f"Session:   {name}")
    print(f"Directory: {session_dir}")

    csvs = sorted(session_dir.glob("*.csv"))
    pngs = sorted(session_dir.glob("*.png"))
    if csvs or pngs:
        print(f"\nAC files:")
        for p in csvs + pngs:
            print(f"  {p.name}")
    else:
        print(f"\nNo .csv/.png files in session directory.")

    files_dir = ds_dir / "files"
    if files_dir.is_dir():
        ds_files = sorted(files_dir.iterdir())
        if ds_files:
            print(f"\nDS files:")
            for p in ds_files:
                print(f"  {p.name}")

    data = load_session(name)
    notes = data.get("notes", [])
    print(f"\nNotes: {len(notes)}")


def cmd_ls():
    name = get_active_session_name()
    if not name:
        print("No active session.")
        return

    ac_files = list_ac_files(name)
    ds_files = list_ds_files(name)

    print(f"Session: {name}\n")

    print("ac/")
    if ac_files:
        for p in ac_files:
            print(f"  {p.name:<40s} {_fmt_size(p.stat().st_size):>8s}  {_fmt_mtime(p)}")
    else:
        print("  (empty)")

    print("\nds/files/")
    if ds_files:
        for p in ds_files:
            print(f"  {p.name:<40s} {_fmt_size(p.stat().st_size):>8s}  {_fmt_mtime(p)}")
    else:
        print("  (empty)")


def cmd_add(args):
    if not args:
        sys.exit("Usage: ds add <path>")
    name = require_active_session()
    path = args[0]
    entry = add_file(name, path)
    if entry is None:
        print(f"Already present: {path}")
    else:
        print(f"Added: {entry['name']} ({entry['type']})")


def cmd_rm(args):
    if not args:
        sys.exit("Usage: ds rm <filename>")
    name = require_active_session()
    filename = args[0]
    remove_file(name, filename)
    print(f"Removed: {filename}")


def cmd_fetch(args):
    from .scraper import fetch
    name = require_active_session()
    query_suffix = " ".join(args) if args else "service manual schematic"
    fetch(name, query_suffix)


def cmd_note(args):
    if not args:
        sys.exit("Usage: ds note \"<text>\"")
    from .notes import add_note
    name = require_active_session()
    add_note(name, " ".join(args))


def cmd_notes():
    from .notes import list_notes
    name = require_active_session()
    list_notes(name)


def cmd_diff(args):
    if len(args) < 2:
        sys.exit("Usage: ds diff <session_a> <session_b>")
    from .diff import diff_sessions
    diff_sessions(args[0], args[1])


def cmd_analyze():
    from .ai import analyze
    name = require_active_session()
    analyze(name)


def cmd_ask(args):
    if not args:
        sys.exit("Usage: ds ask \"<question>\"")
    from .ai import ask
    name = require_active_session()
    ask(name, " ".join(args))


def cmd_log(args):
    from .ai import _load_log
    name = require_active_session()
    log = _load_log(name)
    if not log:
        print("No AI interactions logged.")
        return

    # parse --last N
    last_n = 5
    i = 0
    while i < len(args):
        if args[i] == "--last" and i + 1 < len(args):
            try:
                last_n = int(args[i + 1])
            except ValueError:
                sys.exit(f"Invalid number: {args[i + 1]}")
            i += 2
        else:
            i += 1

    entries = log[-last_n:]
    for entry in entries:
        ts = entry.get("timestamp", "?")
        cmd = entry.get("command", "?")
        resp = entry.get("response", "")
        print(f"[{ts}] {cmd}")
        print(resp)
        print()


_HELP = """\
usage: ds <command> [args]

commands:
  status               active session, file counts
  ls                   list ac files and ds files
  note "<text>"        add timestamped note
  notes                list all notes
  add <path>           add local file into session
  rm <filename>        remove file from session
  fetch [query]        scrape web for manuals/datasheets/forums
  analyze              full AI analysis of session
  ask "<question>"     ad-hoc AI query with session context
  diff <a> <b>         compare two sessions, AI interprets delta
  log [--last N]       show AI interaction history
  help                 show this message"""


def main():
    args = sys.argv[1:]
    if not args or args[0] == "status":
        cmd_status()
    elif args[0] in ("help", "-h", "--help"):
        print(_HELP)
    elif args[0] == "ls":
        cmd_ls()
    elif args[0] == "add":
        cmd_add(args[1:])
    elif args[0] == "rm":
        cmd_rm(args[1:])
    elif args[0] == "fetch":
        cmd_fetch(args[1:])
    elif args[0] == "analyze":
        cmd_analyze()
    elif args[0] == "ask":
        cmd_ask(args[1:])
    elif args[0] == "note":
        cmd_note(args[1:])
    elif args[0] == "notes":
        cmd_notes()
    elif args[0] == "diff":
        cmd_diff(args[1:])
    elif args[0] == "log":
        cmd_log(args[1:])
    else:
        sys.exit(f"Unknown command: {args[0]}")
