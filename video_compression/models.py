from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    size_bytes: int
    duration_seconds: float
    format_name: str
    video_codec: str
    width: int
    height: int
    fps: float
    video_bitrate: int | None
    audio_codec: str | None
    audio_bitrate: int | None
    audio_channels: int | None
    has_audio: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = str(self.path)
        data["size_mb"] = round(self.size_bytes / 1_000_000, 2)
        return data


@dataclass(frozen=True)
class CompressionProfile:
    name: str
    codec: str
    quality: int
    max_height: int | None
    audio_kbps: int
    description: str


@dataclass(frozen=True)
class EncoderChoice:
    codec: str
    encoder: str
    hardware: bool


@dataclass
class VerificationResult:
    passed: bool
    input_path: Path
    output_path: Path
    input_size_bytes: int
    output_size_bytes: int
    input_duration_seconds: float
    output_duration_seconds: float
    duration_delta_seconds: float
    full_decode_passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["input_path"] = str(self.input_path)
        data["output_path"] = str(self.output_path)
        if self.input_size_bytes:
            data["size_reduction_percent"] = round(
                100 * (1 - self.output_size_bytes / self.input_size_bytes), 2
            )
        return data

