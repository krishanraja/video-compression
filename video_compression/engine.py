from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .ffmpeg import VideoCompressionError, find_binary, probe_media, run_command
from .models import CompressionProfile, EncoderChoice, MediaInfo, VerificationResult
from .profiles import choose_encoder, infer_profile, quality_args, quality_for_label


def _scaled_dimensions(info: MediaInfo, max_height: int | None) -> tuple[int, int] | None:
    if not max_height or info.height <= max_height:
        return None
    height = max_height - (max_height % 2)
    width = max(2, round(info.width * height / info.height / 2) * 2)
    return width, height


def default_output_path(source: Path, output_dir: Path) -> Path:
    return output_dir / f"{source.stem} - compressed.mp4"


def build_plan(
    source: str | Path,
    purpose: str,
    *,
    codec: str = "auto",
    quality: str = "balanced",
    target_size_mb: float | None = None,
    output_dir: str | Path | None = None,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    info = probe_media(source)
    profile = infer_profile(purpose)
    selected_codec = profile.codec if codec == "auto" else codec
    choice = choose_encoder(selected_codec, ffmpeg)
    quality_value = quality_for_label(profile.quality, quality)
    target_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else info.path.parent / f"{info.path.stem} - compressed"
    )
    output = default_output_path(info.path, target_dir)
    scaled = _scaled_dimensions(info, profile.max_height)
    return {
        "source": info.to_dict(),
        "purpose": purpose,
        "profile": {
            "name": profile.name,
            "description": profile.description,
            "codec": selected_codec,
            "quality_label": quality,
            "quality_value": quality_value,
            "max_height": profile.max_height,
            "audio_kbps": profile.audio_kbps,
        },
        "encoder": {
            "name": choice.encoder,
            "hardware": choice.hardware,
        },
        "scaled_dimensions": list(scaled) if scaled else None,
        "target_size_mb": target_size_mb,
        "output_dir": str(target_dir),
        "output_path": str(output),
    }


def _video_rate_args(
    choice: EncoderChoice,
    quality_value: int,
    target_size_mb: float | None,
    duration_seconds: float,
    audio_kbps: int,
) -> list[str]:
    if not target_size_mb:
        return quality_args(choice, quality_value)
    if target_size_mb <= 0:
        raise VideoCompressionError("Target size must be greater than zero")
    total_bps = target_size_mb * 8_000_000 * 0.97 / max(duration_seconds, 0.1)
    video_bps = int(total_bps - audio_kbps * 1000)
    if video_bps < 100_000:
        raise VideoCompressionError(
            "The target size is too small for this duration and audio setting"
        )
    return [
        "-b:v",
        str(video_bps),
        "-maxrate",
        str(int(video_bps * 1.25)),
        "-bufsize",
        str(video_bps * 2),
    ]


def _transcode_args(
    info: MediaInfo,
    output: Path,
    profile: CompressionProfile,
    choice: EncoderChoice,
    quality_value: int,
    target_size_mb: float | None,
    ffmpeg_path: Path,
    *,
    start: float | None = None,
    duration: float | None = None,
) -> list[str | Path]:
    effective_duration = duration if duration is not None else info.duration_seconds
    args: list[str | Path] = [ffmpeg_path, "-hide_banner", "-y"]
    if start is not None:
        args.extend(["-ss", f"{start:.3f}"])
    args.extend(["-i", info.path])
    if duration is not None:
        args.extend(["-t", f"{duration:.3f}"])
    args.extend(["-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0", "-sn"])
    scaled = _scaled_dimensions(info, profile.max_height)
    if scaled:
        args.extend(["-vf", f"scale={scaled[0]}:{scaled[1]}"])
    args.extend(["-c:v", choice.encoder, "-pix_fmt", "yuv420p"])
    args.extend(
        _video_rate_args(
            choice,
            quality_value,
            target_size_mb,
            effective_duration,
            profile.audio_kbps,
        )
    )
    if choice.codec == "hevc":
        args.extend(["-tag:v", "hvc1"])
    if info.has_audio:
        args.extend(["-c:a", "aac", "-b:a", f"{profile.audio_kbps}k"])
    else:
        args.append("-an")
    args.extend(["-movflags", "+faststart", output])
    return args


def transcode_media(
    source: str | Path,
    output: str | Path,
    purpose: str,
    *,
    codec: str = "auto",
    quality: str = "balanced",
    target_size_mb: float | None = None,
    overwrite: bool = False,
    ffmpeg: str | None = None,
    start: float | None = None,
    duration: float | None = None,
) -> tuple[Path, dict[str, Any]]:
    info = probe_media(source)
    destination = Path(output).expanduser().resolve()
    if destination == info.path:
        raise VideoCompressionError("Output path must not replace the source video")
    if destination.exists() and not overwrite:
        raise VideoCompressionError(
            f"Output already exists: {destination}. Use --overwrite to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)

    profile = infer_profile(purpose)
    selected_codec = profile.codec if codec == "auto" else codec
    choice = choose_encoder(selected_codec, ffmpeg)
    quality_value = quality_for_label(profile.quality, quality)
    ffmpeg_path = find_binary("ffmpeg", ffmpeg)

    file_handle = tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=destination.suffix or ".mp4",
        dir=destination.parent,
        delete=False,
    )
    partial = Path(file_handle.name)
    file_handle.close()
    try:
        args = _transcode_args(
            info,
            partial,
            profile,
            choice,
            quality_value,
            target_size_mb,
            ffmpeg_path,
            start=start,
            duration=duration,
        )
        run_command(args, capture=False)
        if not partial.is_file() or partial.stat().st_size == 0:
            raise VideoCompressionError("FFmpeg completed without producing a usable file")
        os.replace(partial, destination)
    finally:
        if partial.exists():
            partial.unlink()

    plan = {
        "source": info.to_dict(),
        "output_path": str(destination),
        "purpose": purpose,
        "profile": profile.name,
        "codec": selected_codec,
        "encoder": choice.encoder,
        "hardware_encoder": choice.hardware,
        "quality": quality,
        "quality_value": quality_value,
        "target_size_mb": target_size_mb,
        "start_seconds": start,
        "duration_seconds": duration,
    }
    return destination, plan


def verify_media(
    source: str | Path,
    output: str | Path,
    *,
    expected_duration: float | None = None,
    require_smaller: bool = True,
    max_output_bytes: int | None = None,
    full_decode: bool = True,
    ffmpeg: str | None = None,
) -> VerificationResult:
    source_info = probe_media(source)
    output_info = probe_media(output)
    expected = expected_duration if expected_duration is not None else source_info.duration_seconds
    duration_delta = abs(output_info.duration_seconds - expected)
    tolerance = max(0.75, expected * 0.002)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    add("output_exists", output_info.size_bytes > 0, f"{output_info.size_bytes} bytes")
    add(
        "duration",
        duration_delta <= tolerance,
        f"delta {duration_delta:.3f}s, tolerance {tolerance:.3f}s",
    )
    add("video_stream", output_info.width > 0 and output_info.height > 0, output_info.video_codec)
    add(
        "audio_stream",
        (not source_info.has_audio) or output_info.has_audio,
        output_info.audio_codec or "none",
    )
    smaller = output_info.size_bytes < source_info.size_bytes
    add(
        "smaller_than_source",
        smaller or not require_smaller,
        f"{output_info.size_bytes} vs {source_info.size_bytes} bytes",
    )
    if max_output_bytes is not None:
        add(
            "target_size",
            output_info.size_bytes <= max_output_bytes,
            f"{output_info.size_bytes} bytes, maximum {max_output_bytes} bytes",
        )

    decode_passed = True
    if full_decode:
        ffmpeg_path = find_binary("ffmpeg", ffmpeg)
        result = run_command(
            [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                output_info.path,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        decode_passed = result.returncode == 0
        add("full_decode", decode_passed, (result.stderr or "clean decode").strip())

    passed = all(check["passed"] for check in checks)
    return VerificationResult(
        passed=passed,
        input_path=source_info.path,
        output_path=output_info.path,
        input_size_bytes=source_info.size_bytes,
        output_size_bytes=output_info.size_bytes,
        input_duration_seconds=source_info.duration_seconds,
        output_duration_seconds=output_info.duration_seconds,
        duration_delta_seconds=duration_delta,
        full_decode_passed=decode_passed,
        checks=checks,
    )


def compress_and_verify(
    source: str | Path,
    output: str | Path,
    purpose: str,
    **kwargs: Any,
) -> tuple[Path, dict[str, Any], VerificationResult]:
    verify = bool(kwargs.pop("verify", True))
    target_size_mb = kwargs.get("target_size_mb")
    destination, plan = transcode_media(source, output, purpose, **kwargs)
    result = verify_media(
        source,
        destination,
        max_output_bytes=(int(target_size_mb * 1_000_000) if target_size_mb else None),
        full_decode=verify,
    )
    report_path = destination.with_suffix(".verification.json")
    report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    if not result.passed:
        raise VideoCompressionError(
            f"Compression finished, but verification failed. See {report_path}"
        )
    return destination, plan, result
