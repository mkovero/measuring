import json
import sys
from datetime import datetime, timezone

from .config import AC_CONFIG, SESSION_BASE, DS_DIR_NAME


def get_active_session_name():
    try:
        with open(AC_CONFIG) as f:
            cfg = json.load(f)
        return cfg.get("session")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_session_dir(name):
    return SESSION_BASE / name


def get_ds_dir(name):
    return SESSION_BASE / name / DS_DIR_NAME


def get_session_json(name):
    return get_ds_dir(name) / "session.json"


def load_session(name):
    path = get_session_json(name)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "device": name,
            "created": datetime.now(timezone.utc).isoformat(),
            "notes": [],
            "files": [],
        }


def save_session(name, data):
    path = get_session_json(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def require_active_session():
    name = get_active_session_name()
    if not name:
        sys.exit("No active session — run: ac new <name>")
    return name
