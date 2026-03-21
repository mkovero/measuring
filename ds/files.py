import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import SESSION_BASE, DS_DIR_NAME
from .session import load_session, save_session


def list_ac_files(name):
    """Return sorted list of .csv and .png paths in the session dir (non-recursive, excludes ds/)."""
    session_dir = SESSION_BASE / name
    if not session_dir.is_dir():
        return []
    files = []
    for p in session_dir.iterdir():
        if p.is_file() and p.suffix.lower() in (".csv", ".png"):
            files.append(p)
    return sorted(files)


def list_ds_files(name):
    """Return sorted list of all files in ds/files/."""
    files_dir = SESSION_BASE / name / DS_DIR_NAME / "files"
    if not files_dir.is_dir():
        return []
    return sorted(p for p in files_dir.iterdir() if p.is_file())


_EXT_TYPE = {
    ".pdf": "manual",
    ".md": "note",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".csv": "data",
    ".tsv": "data",
}


def _infer_type(filename):
    return _EXT_TYPE.get(Path(filename).suffix.lower(), "other")


def add_file(name, src_path):
    """Copy src_path into ds/files/, record in session.json. Skips if already present."""
    src = Path(src_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")

    files_dir = SESSION_BASE / name / DS_DIR_NAME / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    dest = files_dir / src.name
    data = load_session(name)
    file_list = data.setdefault("files", [])

    # skip if already present by name
    if any(f["name"] == src.name for f in file_list):
        return None

    shutil.copy2(src, dest)

    entry = {
        "name": src.name,
        "type": _infer_type(src.name),
        "added": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
    }
    file_list.append(entry)
    save_session(name, data)
    return entry


def remove_file(name, filename):
    """Remove file from ds/files/ and from session.json."""
    files_dir = SESSION_BASE / name / DS_DIR_NAME / "files"
    target = files_dir / filename

    if target.is_file():
        target.unlink()

    data = load_session(name)
    file_list = data.get("files", [])
    data["files"] = [f for f in file_list if f["name"] != filename]
    save_session(name, data)
