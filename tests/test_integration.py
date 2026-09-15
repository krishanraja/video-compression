from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_compression.analysis import create_review_pack
from video_compression.engine import compress_and_verify
from video_compression.ffmpeg import probe_media
from video_compression.segments import render_segments


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="video-compression-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mp4"
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=640x360:rate=24",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=700:sample_rate=48000",
                "-t",
                "4",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                self.source,
            ],
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_full_compression_review_and_cut_flow(self) -> None:
        info = probe_media(self.source)
        self.assertAlmostEqual(info.duration_seconds, 4.0, delta=0.2)
        self.assertTrue(info.has_audio)

        output = self.root / "compressed.mp4"
        destination, plan, verification = compress_and_verify(
            self.source,
            output,
            "universal playback",
        )
        self.assertEqual(destination, output)
        self.assertEqual(plan["codec"], "h264")
        self.assertTrue(verification.passed)
        self.assertTrue(output.with_suffix(".verification.json").is_file())

        review = create_review_pack(
            self.source,
            self.root / "review",
            purpose="find useful clips",
            frame_count=8,
        )
        self.assertTrue(Path(review["review_proxy"]).is_file())
        self.assertTrue(Path(review["contact_sheet"]).is_file())
        self.assertTrue(Path(review["review_audio"]).is_file())

        manifest = self.root / "segments.json"
        manifest.write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "start": 0.5,
                            "end": 2.5,
                            "title": "Useful moment",
                            "reason": "Synthetic integration fixture",
                            "confidence": "high",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        report = render_segments(
            self.source,
            manifest,
            self.root / "segments",
            purpose="social clip",
        )
        self.assertEqual(len(report["segments"]), 1)
        self.assertTrue(Path(report["segments"][0]["path"]).is_file())
        self.assertTrue(report["segments"][0]["verified"])


if __name__ == "__main__":
    unittest.main()

