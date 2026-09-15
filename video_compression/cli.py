from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .analysis import create_review_pack
from .engine import build_plan, compress_and_verify, default_output_path, verify_media
from .estimate import estimate_output_size
from .feedback import append_event, draft_review, record_cli_result, submit_review
from .ffmpeg import VideoCompressionError, find_binary, probe_media, run_command
from .profiles import ENCODER_CANDIDATES, choose_encoder
from .segments import render_segments


def _json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def _add_common_media_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--purpose", required=True, help="What the output will be used for")
    parser.add_argument("--codec", choices=["auto", "h264", "hevc", "av1"], default="auto")
    parser.add_argument("--quality", choices=["high", "balanced", "small"], default="balanced")
    parser.add_argument("--ffmpeg", help="Explicit path to ffmpeg")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-compress",
        description="Local-first video compression with review and segment tooling",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--session-dir",
        help="Record sanitized command events for a local session review",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="Check FFmpeg and working encoders")

    probe = subparsers.add_parser("probe", help="Inspect a video without changing it")
    probe.add_argument("input")

    plan = subparsers.add_parser("plan", help="Choose a profile and working encoder")
    plan.add_argument("input")
    _add_common_media_options(plan)
    plan.add_argument("--output-dir")
    plan.add_argument("--target-size-mb", type=float)

    estimate = subparsers.add_parser("estimate", help="Sample the video and estimate output size")
    estimate.add_argument("input")
    _add_common_media_options(estimate)
    estimate.add_argument("--sample-seconds", type=float, default=12.0)

    analyze = subparsers.add_parser("analyze", help="Create a local review pack for cut selection")
    analyze.add_argument("input")
    analyze.add_argument("--purpose", required=True)
    analyze.add_argument("--output-dir", required=True)
    analyze.add_argument("--frames", type=int, default=20)
    analyze.add_argument("--no-proxy", action="store_true")
    analyze.add_argument("--overwrite", action="store_true")
    analyze.add_argument("--ffmpeg")

    compress = subparsers.add_parser("compress", help="Compress and verify a video")
    compress.add_argument("input")
    compress.add_argument("--output", required=True)
    _add_common_media_options(compress)
    compress.add_argument("--target-size-mb", type=float)
    compress.add_argument("--overwrite", action="store_true")
    compress.add_argument("--quick-verify", action="store_true", help="Skip the full decode check")

    cut = subparsers.add_parser("cut", help="Render and verify a segments manifest")
    cut.add_argument("input")
    cut.add_argument("--segments", required=True)
    cut.add_argument("--output-dir", required=True)
    _add_common_media_options(cut)
    cut.add_argument("--overwrite", action="store_true")

    verify = subparsers.add_parser("verify", help="Fully decode and compare an output")
    verify.add_argument("input")
    verify.add_argument("output")
    verify.add_argument("--quick", action="store_true")
    verify.add_argument("--allow-larger", action="store_true")
    verify.add_argument("--ffmpeg")

    feedback = subparsers.add_parser("feedback", help="Record, draft, or submit session learning")
    feedback_commands = feedback.add_subparsers(dest="feedback_command", required=True)
    note = feedback_commands.add_parser("note", help="Record user-visible friction or a resolution")
    note.add_argument("--kind", choices=["problem", "resolution", "observation"], required=True)
    note.add_argument("--message", required=True)
    draft = feedback_commands.add_parser("draft", help="Create a sanitized Markdown session review")
    draft.add_argument("--output", required=True)
    draft.add_argument("--title", required=True)
    draft.add_argument("--purpose", required=True)
    draft.add_argument("--outcome", required=True)
    draft.add_argument("--summary-file")
    submit = feedback_commands.add_parser("submit", help="Submit an approved review as a GitHub issue")
    submit.add_argument("report")
    submit.add_argument("--repo", default="krishanraja/video-compression")
    return parser


def doctor() -> dict[str, Any]:
    ffmpeg = find_binary("ffmpeg")
    ffprobe = find_binary("ffprobe")
    version = run_command([ffmpeg, "-version"]).stdout.splitlines()[0]
    codecs: dict[str, Any] = {}
    for codec in ENCODER_CANDIDATES:
        try:
            choice = choose_encoder(codec, str(ffmpeg))
            codecs[codec] = {
                "available": True,
                "encoder": choice.encoder,
                "hardware": choice.hardware,
            }
        except VideoCompressionError as exc:
            codecs[codec] = {"available": False, "error": str(exc)}
    return {
        "ready": codecs["h264"]["available"],
        "ffmpeg": str(ffmpeg),
        "ffprobe": str(ffprobe),
        "version": version,
        "codecs": codecs,
    }


def _prompt(label: str) -> str:
    while True:
        value = input(label).strip().strip('"')
        if value:
            return value


def interactive_wizard() -> int:
    print("Video Compression Engine")
    print("Files stay on this machine. The source is never deleted.")
    source_text = _prompt("Where is the video currently stored? Enter its local path: ")
    source = Path(source_text).expanduser().resolve()
    purpose = _prompt("What is the compressed video for? ")
    cuts_answer = _prompt("Do you want suggested valuable cuts as well? [y/N]: ").lower()
    wants_cuts = cuts_answer in {"y", "yes"}
    info = probe_media(source)
    output_dir = info.path.parent / f"{info.path.stem} - compressed"
    output = default_output_path(info.path, output_dir)

    _json(build_plan(source, purpose, output_dir=output_dir))
    _json(estimate_output_size(source, purpose))
    if wants_cuts:
        review_dir = output_dir / "review-pack"
        _json(create_review_pack(source, review_dir, purpose=purpose))
        print(
            f"Review pack created at {review_dir}. In ChatGPT Work, the agent will inspect "
            "it and create a segments manifest before rendering clips."
        )

    destination, plan, verification = compress_and_verify(
        source,
        output,
        purpose,
        verify=True,
    )
    _json({"output": str(destination), "plan": plan, "verification": verification.to_dict()})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_dir:
        os.environ["VIDEO_COMPRESSION_SESSION_DIR"] = str(
            Path(args.session_dir).expanduser().resolve()
        )
    if args.command is None:
        return interactive_wizard()
    if args.command == "doctor":
        _json(doctor())
    elif args.command == "probe":
        _json(probe_media(args.input).to_dict())
    elif args.command == "plan":
        _json(build_plan(args.input, args.purpose, codec=args.codec, quality=args.quality, target_size_mb=args.target_size_mb, output_dir=args.output_dir, ffmpeg=args.ffmpeg))
    elif args.command == "estimate":
        _json(estimate_output_size(args.input, args.purpose, codec=args.codec, quality=args.quality, sample_seconds=args.sample_seconds, ffmpeg=args.ffmpeg))
    elif args.command == "analyze":
        _json(create_review_pack(args.input, args.output_dir, purpose=args.purpose, frame_count=args.frames, make_proxy=not args.no_proxy, overwrite=args.overwrite, ffmpeg=args.ffmpeg))
    elif args.command == "compress":
        destination, plan, verification = compress_and_verify(args.input, args.output, args.purpose, codec=args.codec, quality=args.quality, target_size_mb=args.target_size_mb, overwrite=args.overwrite, ffmpeg=args.ffmpeg, verify=not args.quick_verify)
        _json({"output": str(destination), "plan": plan, "verification": verification.to_dict()})
    elif args.command == "cut":
        _json(render_segments(args.input, args.segments, args.output_dir, purpose=args.purpose, codec=args.codec, quality=args.quality, overwrite=args.overwrite, ffmpeg=args.ffmpeg))
    elif args.command == "verify":
        result = verify_media(args.input, args.output, require_smaller=not args.allow_larger, full_decode=not args.quick, ffmpeg=args.ffmpeg)
        _json(result.to_dict())
        return 0 if result.passed else 1
    elif args.command == "feedback":
        session_dir = os.environ.get("VIDEO_COMPRESSION_SESSION_DIR")
        if args.feedback_command in {"note", "draft"} and not session_dir:
            raise VideoCompressionError("--session-dir is required for feedback notes and drafts")
        if args.feedback_command == "note":
            path = append_event(
                session_dir or "",
                kind=args.kind,
                status="recorded",
                message=args.message,
            )
            _json({"recorded": True, "events": str(path)})
        elif args.feedback_command == "draft":
            path = draft_review(
                session_dir or "",
                args.output,
                title=args.title,
                purpose=args.purpose,
                outcome=args.outcome,
                summary_file=args.summary_file,
            )
            _json({"review": str(path), "submitted": False})
        elif args.feedback_command == "submit":
            _json({"submitted": True, "url": submit_review(args.report, repository=args.repo)})
    return 0


def entrypoint() -> None:
    try:
        code = main()
        record_cli_result("ok", "Command completed")
        raise SystemExit(code)
    except (VideoCompressionError, OSError, ValueError, KeyboardInterrupt) as exc:
        record_cli_result("failed", str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
