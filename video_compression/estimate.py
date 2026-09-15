from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .engine import transcode_media
from .ffmpeg import VideoCompressionError, probe_media


def estimate_output_size(
    source: str | Path,
    purpose: str,
    *,
    codec: str = "auto",
    quality: str = "balanced",
    sample_seconds: float = 12.0,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    info = probe_media(source)
    if info.duration_seconds <= 0:
        raise VideoCompressionError("Cannot estimate a video with no measurable duration")
    clip_duration = min(max(3.0, sample_seconds), info.duration_seconds)
    if info.duration_seconds <= clip_duration * 1.5:
        starts = [0.0]
        clip_duration = info.duration_seconds
    else:
        starts = [
            max(
                0.0,
                min(
                    info.duration_seconds - clip_duration,
                    info.duration_seconds * ratio - clip_duration / 2,
                ),
            )
            for ratio in (0.15, 0.5, 0.85)
        ]

    total_bytes = 0
    total_seconds = 0.0
    encoders: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="video-compression-samples-") as temp_dir:
        for index, start in enumerate(starts, start=1):
            sample_path = Path(temp_dir) / f"sample-{index}.mp4"
            output, plan = transcode_media(
                info.path,
                sample_path,
                purpose,
                codec=codec,
                quality=quality,
                overwrite=False,
                ffmpeg=ffmpeg,
                start=start,
                duration=clip_duration,
            )
            total_bytes += output.stat().st_size
            total_seconds += clip_duration
            encoders.add(str(plan["encoder"]))

    bytes_per_second = total_bytes / max(total_seconds, 0.1)
    estimate_bytes = int(bytes_per_second * info.duration_seconds)
    return {
        "source": str(info.path),
        "source_size_bytes": info.size_bytes,
        "sample_count": len(starts),
        "sample_seconds_each": round(clip_duration, 3),
        "sampled_bytes": total_bytes,
        "estimated_output_bytes": estimate_bytes,
        "estimated_output_mb": round(estimate_bytes / 1_000_000, 1),
        "estimated_range_mb": [
            round(estimate_bytes * 0.75 / 1_000_000, 1),
            round(estimate_bytes * 1.25 / 1_000_000, 1),
        ],
        "estimated_reduction_percent": round(
            100 * (1 - estimate_bytes / info.size_bytes), 1
        ),
        "encoders": sorted(encoders),
        "note": "Estimate uses representative samples and may vary with scene complexity.",
    }

