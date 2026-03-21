import sys

from .context import build_context
from .files import list_ac_files
from .session import load_session, get_session_dir
from . import ai


def load_session_data(name):
    session_dir = get_session_dir(name)
    if not session_dir.is_dir():
        return None
    return {
        "session": load_session(name),
        "ac_files": list_ac_files(name),
        "context": build_context(name),
    }


def diff_sessions(name_a, name_b):
    data_a = load_session_data(name_a)
    data_b = load_session_data(name_b)

    if data_a is None:
        sys.exit(f"Session not found: {name_a}")
    if data_b is None:
        sys.exit(f"Session not found: {name_b}")

    prompt = (
        "Compare these two measurement sessions (BEFORE and AFTER) for the same "
        "device. Provide:\n"
        "1. A structured delta of THD/harmonic measurements between sessions\n"
        "2. Interpretation of what changed and whether it indicates improvement "
        "or regression\n"
        "3. Recommended follow-up actions\n\n"
        "--- BEFORE ({name_a}) ---\n{ctx_a}\n--- END BEFORE ---\n\n"
        "--- AFTER ({name_b}) ---\n{ctx_b}\n--- END AFTER ---"
    ).format(
        name_a=name_a,
        name_b=name_b,
        ctx_a=data_a["context"],
        ctx_b=data_b["context"],
    )

    system = (
        "You are an audio equipment diagnostics assistant with deep expertise in "
        "analog and digital audio, THD measurement, frequency response analysis, "
        "and equipment fault diagnosis."
    )
    messages = [{"role": "user", "content": prompt}]
    response = ai.call_claude(system, messages)
    ai.log_interaction(name_b, "diff", prompt, response)
    print(response)
