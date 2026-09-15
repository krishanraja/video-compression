from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from video_compression.feedback import append_event, draft_review, sanitize_text


class FeedbackTests(unittest.TestCase):
    def test_sanitizes_home_queries_and_secrets(self) -> None:
        text = f"{Path.home()} https://example.com/file?token=abc api_key=topsecret"
        cleaned = sanitize_text(text)
        self.assertNotIn(str(Path.home()), cleaned)
        self.assertNotIn("token=abc", cleaned)
        self.assertNotIn("topsecret", cleaned)

    def test_drafts_review_from_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            append_event(root, kind="problem", status="failed", message="Encoder failed")
            append_event(root, kind="resolution", status="ok", message="Used software fallback")
            report = draft_review(
                root,
                root / "session-review.md",
                title="Fallback test",
                purpose="Drive sharing",
                outcome="Compressed successfully",
            )
            content = report.read_text(encoding="utf-8")
            self.assertIn("Encoder failed", content)
            self.assertIn("Used software fallback", content)
            self.assertIn("Privacy check", content)


if __name__ == "__main__":
    unittest.main()

