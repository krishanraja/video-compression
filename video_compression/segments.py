from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .engine import transcode_media, verify_media
from .ffmpeg import VideoCompressionError, probe_media


SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def parse_time(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = value.strip()
    if not text:
        raise VideoCompressionError("A segment timestamp is empty")
    if ":" not in text:
        return float(text)
    parts = text.split(":")
    if len(parts) > 3:
        raise VideoCompressionError(f"Invalid timestamp: {value}")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def _clean_title(title: str, index: int) -> str:
    cleaned = SAFE_NAME.sub("", title).strip(" .")
    return cleaned[:80] or f"segment-{index:02d}"


def load_segments(manifest: str | Path, source: str | Path) -> list[dict[str, Any]]:
    path = Path(manifest).expanduser().resolve()
    if not path.is_file():
        raise VideoCompressionError(f"Segments manifest does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise VideoCompressionError(f"Could not read segments manifest: {path}") from exc
    items = payload.get("segments") if isinstance(payload, dict) else payload
    if not isinstance(items, list) or not items:
        raise VideoCompressionError("Segments manifest must contain a non-empty segments list")

    duration = probe_media(source).duration_seconds
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise VideoCompressionError(f"Segment {index} must be an object")
        start = parse_time(item.get("start", ""))
        end = parse_time(item.get("end", ""))
        if start < 0 or end <= start or end > duration + 0.25:
            raise VideoCompressionError(
                f"Segment {index} has an invalid range: {start:.3f} to {end:.3f}"
            )
        normalized.append(
            {
                "index": index,
                "start": start,
                "end": min(end, duration),
                "duration": min(end, duration) - start,
                "title": _clean_title(str(item.get("title") or ""), index),
                "reason": str(item.get("reason") or ""),
                "confidence": str(item.get("confidence") or "unspecified"),
            }
        )
    return normalized


def render_segments(
    source: str | Path,
    manifest: str | Path,
    output_dir: str | Path,
    *,
    purpose: str,
    codec: str = "auto",
    quality: str = "balanced",
    overwrite: bool = False,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    segments = load_segments(manifest, source)
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    for item in segments:
        output = destination / f"{item['index']:02d} - {item['title']}.mp4"
        path, plan = transcode_media(
            source,
            output,
            purpose,
            codec=codec,
            quality=quality,
            overwrite=overwrite,
            ffmpeg=ffmpeg,
            start=item["start"],
            duration=item["duration"],
        )
        verification = verify_media(
            source,
            path,
            expected_duration=item["duration"],
            require_smaller=False,
            full_decode=True,
            ffmpeg=ffmpeg,
        )
        if not verification.passed:
            raise VideoCompressionError(f"Verification failed for segment: {path}")
        rendered.append(
            {
                **item,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "encoder": plan["encoder"],
                "verified": True,
            }
        )
    report = {
        "source": str(Path(source).expanduser().resolve()),
        "manifest": str(Path(manifest).expanduser().resolve()),
        "output_dir": str(destination),
        "segments": rendered,
    }
    (destination / "segments-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report

