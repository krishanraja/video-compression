from __future__ import annotations

import json
import os
import platform
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .ffmpeg import VideoCompressionError, run_command


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{16,}"),
]
URL_QUERY = re.compile(r"(https?://[^\s?]+)\?[^\s]+")
WINDOWS_HOME = re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+")
POSIX_HOME = re.compile(r"/(?:Users|home)/[^/\s]+")


def sanitize_text(value: str) -> str:
    text = str(value)
    home = str(Path.home())
    if home:
        text = text.replace(home, "<HOME>")
        text = text.replace(home.replace("\\", "/"), "<HOME>")
    text = WINDOWS_HOME.sub("<HOME>", text)
    text = POSIX_HOME.sub("<HOME>", text)
    text = URL_QUERY.sub(r"\1?<redacted-query>", text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}=<redacted>" if match.lastindex else "<redacted-secret>", text)
    return text


def _events_path(session_dir: str | Path) -> Path:
    directory = Path(session_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "session-events.jsonl"


def append_event(
    session_dir: str | Path,
    *,
    kind: str,
    status: str,
    message: str,
    command: Iterable[str] | None = None,
) -> Path:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_version": __version__,
        "kind": kind,
        "status": status,
        "message": sanitize_text(message),
        "command": sanitize_text(" ".join(command or [])),
    }
    path = _events_path(session_dir)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def read_events(session_dir: str | Path) -> list[dict[str, Any]]:
    path = _events_path(session_dir)
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def draft_review(
    session_dir: str | Path,
    output: str | Path,
    *,
    title: str,
    purpose: str,
    outcome: str,
    summary_file: str | Path | None = None,
) -> Path:
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    events = read_events(session_dir)
    supplied_summary = ""
    if summary_file:
        supplied_summary = sanitize_text(
            Path(summary_file).expanduser().resolve().read_text(encoding="utf-8")
        ).strip()

    problems = [event for event in events if event.get("kind") == "problem" or event.get("status") == "failed"]
    resolutions = [event for event in events if event.get("kind") == "resolution"]
    evidence = [event for event in events if event.get("kind") not in {"problem", "resolution"}]

    def lines(items: list[dict[str, Any]], empty: str) -> str:
        if not items:
            return f"- {empty}"
        return "\n".join(
            f"- {item.get('message', 'No message')}"
            + (f" (`{item.get('command')}`)" if item.get("command") else "")
            for item in items
        )

    body = (
        f"# {sanitize_text(title)}\n\n"
        "## Session context\n\n"
        f"- Purpose: {sanitize_text(purpose)}\n"
        f"- Outcome: {sanitize_text(outcome)}\n"
        f"- Engine: {__version__}\n"
        f"- OS: {sanitize_text(platform.platform())}\n"
        f"- Python: {platform.python_version()}\n\n"
        "## User session summary\n\n"
        f"{supplied_summary or 'Add the user-visible story here before submission.'}\n\n"
        "## Problems and friction\n\n"
        f"{lines(problems, 'No problem was recorded.')}\n\n"
        "## Resolution or workaround\n\n"
        f"{lines(resolutions, 'No resolution was recorded.')}\n\n"
        "## Technical evidence\n\n"
        f"{lines(evidence, 'No additional command evidence was recorded.')}\n\n"
        "## Proposed reusable learning\n\n"
        "State the smallest code, test, documentation, or skill change that would prevent this problem for another user.\n\n"
        "## Privacy check\n\n"
        "- [ ] I reviewed this report and it contains no private media content, private paths, credentials, or sensitive personal information.\n"
    )
    destination.write_text(body, encoding="utf-8")
    return destination


def submit_review(
    report: str | Path,
    *,
    repository: str = "krishanraja/video-compression",
) -> str:
    report_path = Path(report).expanduser().resolve()
    if not report_path.is_file():
        raise VideoCompressionError(f"Session review does not exist: {report_path}")
    gh = shutil.which("gh")
    if not gh:
        raise VideoCompressionError(
            "GitHub CLI is not installed. Copy the review into the repository's session feedback form."
        )
    auth = run_command([gh, "auth", "status"], check=False)
    if auth.returncode != 0:
        raise VideoCompressionError(
            "GitHub CLI is not authenticated. Copy the review into the session feedback form."
        )

    content = sanitize_text(report_path.read_text(encoding="utf-8"))
    if "- [x] i reviewed this report" not in content.lower():
        raise VideoCompressionError(
            "Privacy check is not confirmed. Review the report and mark its privacy checkbox before submission."
        )
    heading = next(
        (line.removeprefix("# ").strip() for line in content.splitlines() if line.startswith("# ")),
        "Video compression session feedback",
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as handle:
        handle.write(content)
        sanitized_path = Path(handle.name)
    try:
        result = run_command(
            [
                gh,
                "issue",
                "create",
                "--repo",
                repository,
                "--title",
                f"Session feedback: {heading[:120]}",
                "--body-file",
                sanitized_path,
                "--label",
                "session-feedback",
            ]
        )
    finally:
        sanitized_path.unlink(missing_ok=True)
    url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if not url.startswith("http"):
        raise VideoCompressionError("GitHub did not return an issue URL")
    return url


def record_cli_result(status: str, message: str) -> None:
    session_dir = os.environ.get("VIDEO_COMPRESSION_SESSION_DIR")
    if not session_dir:
        return
    append_event(
        session_dir,
        kind="command",
        status=status,
        message=message,
        command=sys.argv,
    )
