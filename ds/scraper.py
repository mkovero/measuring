import json
import re
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .ai import get_api_key, ANTHROPIC_API_URL
from .files import add_file
from .session import load_session, get_ds_dir


def _slugify(text, max_len=60):
    """Turn text into a safe filename slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text).strip('-')
    return text[:max_len]


def _call_claude_with_tools(system, messages, tools, max_tokens=4096):
    """Like ai.call_claude but passes tools and returns raw content blocks."""
    key = get_api_key()
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "tools": tools,
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
        with urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        error_body = e.read().decode(errors="replace")
        raise RuntimeError(f"API error {e.code}: {error_body}")

    return data.get("content", [])


_SEARCH_SYSTEM = """\
You are a research assistant finding technical documentation for audio equipment.
Search the web for service manuals, schematics, datasheets, and repair forum threads.
For each useful document you find, report:
- The URL
- The title/description
- Whether it's a PDF or text/forum content
- For text content, include the most relevant excerpts

Focus on the most authoritative and relevant results. Prefer official service manuals \
and schematics over generic forum posts."""


def search_and_fetch(device_name, query_suffix, session_name):
    """Search web for device documentation and return list of results.

    Returns list of dicts: {url, title, type (pdf/markdown), content}
    """
    query = f"{device_name} {query_suffix}"
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    messages = [{"role": "user", "content": (
        f"Search for: {query}\n\n"
        "Find the most relevant service manuals, schematics, datasheets, "
        "or repair forum threads. For each result, give me the URL, title, "
        "and indicate if it's a PDF or text content. For text/forum content, "
        "include the key relevant excerpts. Return results as a structured list."
    )}]

    print(f"Searching: {query}")
    content_blocks = _call_claude_with_tools(_SEARCH_SYSTEM, messages, tools)

    results = []
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "")
            # extract URLs and classify
            urls_found = re.findall(r'(https?://[^\s\)\"\']+)', text)
            pdf_urls = [u for u in urls_found if u.lower().endswith('.pdf')]

            for url in pdf_urls:
                # derive title from URL
                title = Path(url.split('?')[0]).stem
                results.append({
                    "url": url,
                    "title": title,
                    "type": "pdf",
                    "content": None,
                })

            # the text block itself is useful as markdown
            if text.strip() and len(text.strip()) > 100:
                results.append({
                    "url": None,
                    "title": f"{device_name} - search results",
                    "type": "markdown",
                    "content": text,
                })

    return results


def save_result(session_name, result):
    """Save a search result to ds/files/. Returns filename or None on skip."""
    files_dir = get_ds_dir(session_name) / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    if result["type"] == "pdf" and result.get("url"):
        filename = _slugify(result["title"]) + ".pdf"

        # check if already present
        if (files_dir / filename).exists():
            return None

        # fetch PDF binary
        print(f"  Fetching PDF: {result['url']}")
        try:
            req = Request(result["url"], headers={
                "User-Agent": "Mozilla/5.0 (compatible; ds-tool/1.0)",
            })
            with urlopen(req, timeout=60) as resp:
                pdf_data = resp.read()
        except Exception as e:
            print(f"  Failed to fetch PDF: {e}")
            return None

        # write to temp, then add_file
        with tempfile.NamedTemporaryFile(suffix=".pdf", prefix=filename.replace(".pdf", "_"),
                                         delete=False) as tmp:
            tmp.write(pdf_data)
            tmp_path = tmp.name

        try:
            entry = add_file(session_name, tmp_path)
            # rename if add_file used the temp name
            actual = files_dir / Path(tmp_path).name
            desired = files_dir / filename
            if actual.exists() and actual != desired and not desired.exists():
                actual.rename(desired)
                # update session.json entry name
                from .session import load_session, save_session
                data = load_session(session_name)
                for f in data.get("files", []):
                    if f["name"] == Path(tmp_path).name:
                        f["name"] = filename
                        break
                save_session(session_name, data)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return filename

    elif result["type"] == "markdown" and result.get("content"):
        filename = _slugify(result["title"]) + ".md"

        if (files_dir / filename).exists():
            return None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         prefix=filename.replace(".md", "_"),
                                         delete=False) as tmp:
            tmp.write(result["content"])
            tmp_path = tmp.name

        try:
            entry = add_file(session_name, tmp_path)
            actual = files_dir / Path(tmp_path).name
            desired = files_dir / filename
            if actual.exists() and actual != desired and not desired.exists():
                actual.rename(desired)
                from .session import load_session, save_session
                data = load_session(session_name)
                for f in data.get("files", []):
                    if f["name"] == Path(tmp_path).name:
                        f["name"] = filename
                        break
                save_session(session_name, data)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return filename

    return None


def fetch(session_name, query_suffix="service manual schematic"):
    """Orchestrate: search, fetch, save, summarize."""
    data = load_session(session_name)
    device_name = data.get("device", session_name)

    results = search_and_fetch(device_name, query_suffix, session_name)

    if not results:
        print("No results found.")
        return

    saved = []
    skipped = []
    for result in results:
        filename = save_result(session_name, result)
        if filename is None:
            skipped.append(result.get("title", "?"))
        else:
            saved.append(filename)

    print(f"\nSaved {len(saved)} file(s):")
    for f in saved:
        print(f"  {f}")
    if skipped:
        print(f"Skipped {len(skipped)} (already present or failed)")
