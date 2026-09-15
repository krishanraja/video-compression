from __future__ import annotations

from .ffmpeg import VideoCompressionError, encoder_works, listed_encoders
from .models import CompressionProfile, EncoderChoice


PROFILES: dict[str, CompressionProfile] = {
    "share": CompressionProfile(
        "share", "hevc", 27, 1080, 96, "Small file for Drive, messaging, or personal sharing"
    ),
    "email": CompressionProfile(
        "email", "h264", 29, 720, 64, "Very small, broadly playable attachment"
    ),
    "universal": CompressionProfile(
        "universal", "h264", 23, 1080, 128, "Broad playback compatibility"
    ),
    "social": CompressionProfile(
        "social", "h264", 22, 1080, 128, "Upload-ready social video"
    ),
    "web": CompressionProfile(
        "web", "h264", 24, 1080, 96, "Fast-start video for a website"
    ),
    "archive": CompressionProfile(
        "archive", "hevc", 24, None, 128, "Smaller master with conservative quality loss"
    ),
    "editing": CompressionProfile(
        "editing", "h264", 18, None, 192, "High-quality working copy for later edits"
    ),
}


def infer_profile(purpose: str) -> CompressionProfile:
    normalized = purpose.strip().lower()
    aliases = {
        "message": "share",
        "messaging": "share",
        "drive": "share",
        "cloud": "share",
        "family": "share",
        "whatsapp": "share",
        "email": "email",
        "attachment": "email",
        "youtube": "social",
        "instagram": "social",
        "tiktok": "social",
        "linkedin": "social",
        "social": "social",
        "website": "web",
        "web": "web",
        "archive": "archive",
        "backup": "archive",
        "edit": "editing",
        "editing": "editing",
        "compatible": "universal",
        "universal": "universal",
    }
    if normalized in PROFILES:
        return PROFILES[normalized]
    for term, profile_name in aliases.items():
        if term in normalized:
            return PROFILES[profile_name]
    return PROFILES["universal"]


ENCODER_CANDIDATES: dict[str, list[tuple[str, bool]]] = {
    "h264": [
        ("h264_nvenc", True),
        ("h264_qsv", True),
        ("h264_videotoolbox", True),
        ("libx264", False),
    ],
    "hevc": [
        ("hevc_nvenc", True),
        ("hevc_qsv", True),
        ("hevc_videotoolbox", True),
        ("libx265", False),
    ],
    "av1": [
        ("av1_nvenc", True),
        ("av1_qsv", True),
        ("libsvtav1", False),
        ("libaom-av1", False),
    ],
}


def choose_encoder(codec: str, ffmpeg: str | None = None) -> EncoderChoice:
    normalized = codec.lower()
    if normalized not in ENCODER_CANDIDATES:
        raise VideoCompressionError(f"Unsupported codec: {codec}")
    available = listed_encoders(ffmpeg)
    for encoder, hardware in ENCODER_CANDIDATES[normalized]:
        if encoder in available and encoder_works(encoder, ffmpeg):
            return EncoderChoice(normalized, encoder, hardware)
    raise VideoCompressionError(
        f"No working {normalized} encoder was found in this FFmpeg installation"
    )


def quality_args(choice: EncoderChoice, quality: int) -> list[str]:
    encoder = choice.encoder
    if encoder.endswith("_qsv"):
        return ["-global_quality", str(quality), "-preset", "medium"]
    if encoder.endswith("_nvenc"):
        return ["-preset", "p5", "-rc", "vbr", "-cq", str(quality), "-b:v", "0"]
    if encoder.endswith("_videotoolbox"):
        value = max(1, min(100, 100 - quality * 2))
        return ["-q:v", str(value)]
    if encoder == "libsvtav1":
        return ["-preset", "8", "-crf", str(quality)]
    if encoder == "libaom-av1":
        return ["-cpu-used", "6", "-crf", str(quality), "-b:v", "0"]
    return ["-preset", "medium", "-crf", str(quality)]


def quality_for_label(base: int, label: str) -> int:
    offsets = {"high": -3, "balanced": 0, "small": 3}
    if label not in offsets:
        raise VideoCompressionError(f"Unknown quality: {label}")
    return max(14, min(40, base + offsets[label]))
