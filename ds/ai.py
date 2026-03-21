import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .context import build_context
from .session import get_ds_dir

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY not set.\n  export ANTHROPIC_API_KEY=sk-ant-...")
    return key


def call_claude(system, messages, max_tokens=2048):
    key = get_api_key()
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }).encode()

    req = Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        error_body = e.read().decode(errors="replace")
        sys.exit(f"API error {e.code}:\n{error_body}")

    # extract text from content blocks
    content = data.get("content", [])
    return "".join(b.get("text", "") for b in content)


def _log_path(name):
    return get_ds_dir(name) / "ai_log.json"


def _load_log(name):
    path = _log_path(name)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def log_interaction(name, command, prompt, response):
    log = _load_log(name)
    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "prompt": prompt,
        "response": response,
    })
    path = _log_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(log, f, indent=2)


_SYSTEM_PROMPT = """\
You are an audio equipment diagnostics assistant. You have deep expertise in \
analog and digital audio, THD measurement, frequency response analysis, and \
equipment fault diagnosis.

You are given the full context of a measurement session below. Use it to \
provide precise, actionable analysis.

--- SESSION CONTEXT ---
{context}
--- END CONTEXT ---"""


def analyze(name):
    context = build_context(name)
    system = _SYSTEM_PROMPT.format(context=context)
    user_msg = (
        "Analyze this measurement session. Provide:\n"
        "1. Fault candidates ranked by likelihood\n"
        "2. Measurement anomalies\n"
        "3. Recommended next steps"
    )
    messages = [{"role": "user", "content": user_msg}]
    response = call_claude(system, messages)
    log_interaction(name, "analyze", user_msg, response)
    print(response)


def ask(name, question):
    context = build_context(name)
    system = _SYSTEM_PROMPT.format(context=context)
    messages = [{"role": "user", "content": question}]
    response = call_claude(system, messages)
    log_interaction(name, "ask", question, response)
    print(response)
