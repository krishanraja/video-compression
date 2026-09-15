from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .ffmpeg import VideoCompressionError, find_binary, probe_media, run_command
from .profiles import choose_encoder, quality_args


SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")
BLACK_SEGMENT = re.compile(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)")


def _atomic_media_command(args: list[str | Path], destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_handle = tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=destination.suffix,
        dir=destination.parent,
        delete=False,
    )
    partial = Path(file_handle.name)
    file_handle.close()
    command = [partial if item == "__OUTPUT__" else item for item in args]
    try:
        result = run_command(command)
        if not partial.exists() or partial.stat().st_size == 0:
            raise VideoCompressionError(f"No usable output was created for {destination.name}")
        os.replace(partial, destination)
        return result.stderr or ""
    finally:
        if partial.exists():
            partial.unlink()


def _parse_timeline(log: str) -> dict[str, list[dict[str, float]]]:
    silence_ranges: list[dict[str, float]] = []
    current_start: float | None = None
    for line in log.splitlines():
        start_match = SILENCE_START.search(line)
        if start_match:
            current_start = float(start_match.group(1))
        end_match = SILENCE_END.search(line)
        if end_match:
            end = float(end_match.group(1))
            if current_start is not None:
                silence_ranges.append(
                    {
                        "start": current_start,
                        "end": end,
                        "duration": round(end - current_start, 3),
                    }
                )
            current_start = None

    black_ranges = [
        {
            "start": float(match.group(1)),
            "end": float(match.group(2)),
            "duration": round(float(match.group(2)) - float(match.group(1)), 3),
        }
        for match in BLACK_SEGMENT.finditer(log)
    ]
    return {"silence_ranges": silence_ranges, "black_ranges": black_ranges}


def create_review_pack(
    source: str | Path,
    output_dir: str | Path,
    *,
    purpose: str,
    frame_count: int = 20,
    make_proxy: bool = True,
    overwrite: bool = False,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    info = probe_media(source)
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()) and not overwrite:
        raise VideoCompressionError(
            f"Review pack directory is not empty: {destination}. Use --overwrite to refresh it."
        )
    destination.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = find_binary("ffmpeg", ffmpeg)
    frame_count = max(4, min(100, frame_count))

    metadata_path = destination / "metadata.json"
    contact_sheet_path = destination / "contact-sheet.jpg"
    proxy_path = destination / "review-proxy.mp4"
    audio_path = destination / "review-audio.mp3"
    timeline_path = destination / "timeline.json"
    review_path = destination / "REVIEW.md"

    metadata_path.write_text(json.dumps(info.to_dict(), indent=2), encoding="utf-8")

    interval = max(0.25, info.duration_seconds / frame_count)
    columns = 5
    rows = (frame_count + columns - 1) // columns
    contact_args: list[str | Path] = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        info.path,
        "-vf",
        f"fps=1/{interval:.6f},scale=320:-2,tile={columns}x{rows}:padding=4:margin=4",
        "-frames:v",
        "1",
        "__OUTPUT__",
    ]
    _atomic_media_command(contact_args, contact_sheet_path)

    analysis_log = ""
    if make_proxy:
        max_height = min(540, info.height)
        scaled_height = max_height - (max_height % 2)
        scaled_width = max(2, round(info.width * scaled_height / info.height / 2) * 2)
        choice = choose_encoder("h264", ffmpeg)
        proxy_args: list[str | Path] = [
            ffmpeg_path,
            "-hide_banner",
            "-nostats",
            "-y",
            "-i",
            info.path,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            f"blackdetect=d=0.5:pix_th=0.10,scale={scaled_width}:{scaled_height}",
        ]
        if info.has_audio:
            proxy_args.extend(["-af", "silencedetect=n=-35dB:d=1.2"])
        proxy_args.extend(["-c:v", choice.encoder, "-pix_fmt", "yuv420p"])
        proxy_args.extend(quality_args(choice, 31))
        if info.has_audio:
            proxy_args.extend(["-c:a", "aac", "-b:a", "64k"])
        proxy_args.extend(["-movflags", "+faststart", "__OUTPUT__"])
        analysis_log = _atomic_media_command(proxy_args, proxy_path)
    else:
        scan_args: list[str | Path] = [
            ffmpeg_path,
            "-hide_banner",
            "-nostats",
            "-i",
            info.path,
            "-vf",
            "blackdetect=d=0.5:pix_th=0.10",
        ]
        if info.has_audio:
            scan_args.extend(["-af", "silencedetect=n=-35dB:d=1.2"])
        scan_args.extend(["-f", "null", "-"])
        result = run_command(scan_args)
        analysis_log = result.stderr or ""

    if info.has_audio:
        audio_args: list[str | Path] = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            info.path,
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            "__OUTPUT__",
        ]
        _atomic_media_command(audio_args, audio_path)

    timeline = _parse_timeline(analysis_log)
    timeline_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    review_path.write_text(
        "# Video review pack\n\n"
        f"Purpose: {purpose}\n\n"
        "Inspect `review-proxy.mp4` with the host's video and audio tools. Use "
        "`contact-sheet.jpg` for orientation and `timeline.json` for long silent or "
        "black passages. Motion and silence alone do not establish semantic value. "
        "Only recommend a segment after reviewing its spoken or visual content.\n\n"
        "For every suggested segment, record start, end, title, purpose-aligned reason, "
        "and a confidence level. Do not claim to have watched or listened unless the "
        "media was actually rendered and reviewed. Save accepted suggestions in "
        "`segments.json` using the repository schema.\n",
        encoding="utf-8",
    )

    return {
        "source": str(info.path),
        "purpose": purpose,
        "directory": str(destination),
        "metadata": str(metadata_path),
        "contact_sheet": str(contact_sheet_path),
        "review_proxy": str(proxy_path) if make_proxy else None,
        "review_audio": str(audio_path) if info.has_audio else None,
        "timeline": str(timeline_path),
        "review_instructions": str(review_path),
        "silence_count": len(timeline["silence_ranges"]),
        "black_count": len(timeline["black_ranges"]),
    }

