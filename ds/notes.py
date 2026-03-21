from datetime import datetime, timezone

from .session import load_session, save_session


def add_note(session_name, text):
    data = load_session(session_name)
    notes = data.setdefault("notes", [])
    ts = datetime.now(timezone.utc).isoformat()
    notes.append({"text": text, "timestamp": ts})
    save_session(session_name, data)
    print(f"Note added [{ts}]")


def list_notes(session_name):
    data = load_session(session_name)
    notes = data.get("notes", [])
    if not notes:
        print("No notes yet.")
        return
    for n in notes:
        ts = n.get("timestamp", "?")
        text = n.get("text", "")
        print(f"  [{ts}] {text}")
