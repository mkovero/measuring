import csv

from .files import list_ac_files, list_ds_files
from .session import load_session


def _sig_figs(val, figs=3):
    """Format a float to N significant figures."""
    if val == 0:
        return "0"
    from math import log10, floor
    magnitude = floor(log10(abs(val)))
    precision = figs - 1 - magnitude
    if precision < 0:
        precision = 0
    return f"{val:.{precision}f}"


def summarise_ac_files(name):
    """Read all .csv files from list_ac_files(), return a compact text summary."""
    csv_paths = [p for p in list_ac_files(name) if p.suffix.lower() == ".csv"]
    if not csv_paths:
        return "No CSV measurement files."

    parts = []
    budget_per_file = max(200, 1800 // len(csv_paths))

    for path in csv_paths:
        try:
            with open(path, newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    parts.append(f"[{path.name}] (empty)")
                    continue
                rows = list(reader)
        except Exception as e:
            parts.append(f"[{path.name}] error: {e}")
            continue

        n_rows = len(rows)
        lines = [f"[{path.name}] {n_rows} rows, cols: {', '.join(header)}"]

        # compute numeric stats per column
        for i, col in enumerate(header):
            vals = []
            for row in rows:
                if i < len(row):
                    try:
                        vals.append(float(row[i]))
                    except (ValueError, TypeError):
                        pass
            if vals:
                lo = min(vals)
                hi = max(vals)
                mean = sum(vals) / len(vals)
                lines.append(f"  {col}: min={_sig_figs(lo)} max={_sig_figs(hi)} mean={_sig_figs(mean)}")

        entry = "\n".join(lines)
        if len(entry) > budget_per_file:
            entry = entry[:budget_per_file - 3] + "..."
        parts.append(entry)

    result = "\n".join(parts)
    if len(result) > 2000:
        result = result[:1997] + "..."
    return result


def build_context(name):
    """Assemble full session context as a single string."""
    data = load_session(name)

    sections = []

    # Device and creation date
    device = data.get("device", name)
    created = data.get("created", "unknown")
    sections.append(f"Device: {device}\nSession created: {created}")

    # Notes
    notes = data.get("notes", [])
    if notes:
        note_lines = []
        for n in notes:
            ts = n.get("timestamp", "")
            text = n.get("text", "")
            note_lines.append(f"  [{ts}] {text}")
        sections.append("Notes:\n" + "\n".join(note_lines))

    # AC measurement summary
    ac_summary = summarise_ac_files(name)
    sections.append("AC measurements:\n" + ac_summary)

    # DS files
    ds_files = list_ds_files(name)
    if ds_files:
        file_data = data.get("files", [])
        type_map = {f["name"]: f.get("type", "other") for f in file_data}
        file_lines = []
        for p in ds_files:
            ftype = type_map.get(p.name, "other")
            file_lines.append(f"  {p.name} ({ftype})")
        sections.append("Attached files:\n" + "\n".join(file_lines))

    return "\n\n".join(sections)
