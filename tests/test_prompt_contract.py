from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "COPY-PASTE-PROMPT.md"


class OpeningPromptContractTests(unittest.TestCase):
    def test_prompt_covers_the_complete_local_workflow(self) -> None:
        text = PROMPT.read_text(encoding="utf-8")

        required_contract = (
            "https://github.com/krishanraja/video-compression",
            "AGENTS.md",
            ".agents/skills/video-compression/SKILL.md",
            "--session-dir",
            "doctor",
            "Probe the exact source",
            "representative-sample estimate",
            "run analyze",
            "render them with cut",
            "Compress the full video",
            "decode the entire output",
            "feedback note --kind problem",
            "feedback note --kind resolution",
            "feedback draft",
            "feedback submit",
            "Privacy-review the report",
            "Preserve the source",
            "cloud-drive share URL",
            "local file path",
            "correct signed-in account or connector",
            "containing folder is attached",
            "approval for local machine access",
        )

        for requirement in required_contract:
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_prompt_does_not_overpromise_access_or_delete_the_source(self) -> None:
        text = PROMPT.read_text(encoding="utf-8")

        self.assertIn(
            "Do not claim that pasting a GitHub link grants local file access", text
        )
        self.assertIn("Do not upload the video", text)
        self.assertIn("do not overwrite an existing output", text)
        self.assertNotIn("delete the source", text.lower())


if __name__ == "__main__":
    unittest.main()
