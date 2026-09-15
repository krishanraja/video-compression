from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Iterable

from .models import MediaInfo


class VideoCompressionError(RuntimeError):
    """Raised when a media command cannot complete safely."""


def _winget_candidates(binary: str) -> Iterable[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return []
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not packages.exists():
        return []
    suffix = f"{binary}.exe"
    return packages.glob(f"*FFmpeg*/**/bin/{suffix}")


def find_binary(binary: str, explicit: str | Path | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise VideoCompressionError(f"{binary} was not found at {path}")

    env_name = f"VIDEO_COMPRESSION_{binary.upper()}"
    env_path = os.environ.get(env_name)
    if env_path and Path(env_path).is_file():
        return Path(env_path).resolve()

    found = shutil.which(binary)
    if found:
        return Path(found).resolve()

    candidates = sorted(_winget_candidates(binary), reverse=True)
    if candidates:
        return candidates[0].resolve()

    raise VideoCompressionError(
        f"{binary} is required but was not found. Install FFmpeg and make sure "
        f"{binary} is on PATH."
    )


def run_command(
    args: list[str | Path],
    *,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [str(item) for item in args]
    if capture:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    else:
        process = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        tail: deque[str] = deque(maxlen=40)
        assert process.stderr is not None
        for line in process.stderr:
            print(line, end="", file=sys.stderr)
            tail.append(line)
        process.stderr.close()
        return_code = process.wait()
        result = subprocess.CompletedProcess(
            command,
            return_code,
            stdout="",
            stderr="".join(tail),
        )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown media error").strip()
        tail = "\n".join(detail.splitlines()[-30:])
        raise VideoCompressionError(
            f"Command failed with exit code {result.returncode}: {tail}"
        )
    return result


def _parse_rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    numerator, separator, denominator = value.partition("/")
    if separator:
        den = float(denominator)
        return float(numerator) / den if den else 0.0
    return float(value)


def probe_media(path: str | Path, ffprobe: str | Path | None = None) -> MediaInfo:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise VideoCompressionError(f"Video file does not exist: {source}")
    ffprobe_path = find_binary("ffprobe", ffprobe)
    result = run_command(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,bit_rate,channels,sample_rate",
            "-of",
            "json",
            source,
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoCompressionError("ffprobe returned invalid JSON") from exc

    streams = payload.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video:
        raise VideoCompressionError(f"No video stream was found in {source}")
    media_format = payload.get("format", {})

    def optional_int(value: object) -> int | None:
        try:
            return int(str(value)) if value not in (None, "N/A") else None
        except ValueError:
            return None

    return MediaInfo(
        path=source,
        size_bytes=int(media_format.get("size") or source.stat().st_size),
        duration_seconds=float(media_format.get("duration") or 0),
        format_name=str(media_format.get("format_name") or "unknown"),
        video_codec=str(video.get("codec_name") or "unknown"),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        fps=_parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        video_bitrate=optional_int(video.get("bit_rate")),
        audio_codec=str(audio.get("codec_name")) if audio else None,
        audio_bitrate=optional_int(audio.get("bit_rate")) if audio else None,
        audio_channels=optional_int(audio.get("channels")) if audio else None,
        has_audio=audio is not None,
    )


def listed_encoders(ffmpeg: str | Path | None = None) -> set[str]:
    ffmpeg_path = find_binary("ffmpeg", ffmpeg)
    result = run_command([ffmpeg_path, "-hide_banner", "-encoders"])
    encoders: set[str] = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) >= 2 and columns[0].startswith("V"):
            encoders.add(columns[1])
    return encoders


def encoder_works(encoder: str, ffmpeg: str | Path | None = None) -> bool:
    ffmpeg_path = find_binary("ffmpeg", ffmpeg)
    args: list[str | Path] = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x180:rate=24",
        "-t",
        "0.25",
        "-an",
        "-c:v",
        encoder,
    ]
    if encoder.endswith("_qsv"):
        args.extend(["-global_quality", "28"])
    elif encoder.endswith("_nvenc"):
        args.extend(["-preset", "p4", "-cq", "28", "-b:v", "0"])
    elif encoder == "libsvtav1":
        args.extend(["-preset", "12", "-crf", "35"])
    elif encoder.startswith("libx") or encoder == "libaom-av1":
        args.extend(["-preset", "ultrafast", "-crf", "28"])
    args.extend(["-f", "null", "-"])
    return run_command(args, check=False).returncode == 0
