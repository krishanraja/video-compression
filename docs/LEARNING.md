# Session learning loop

The repository can collect evidence from every user session without silently publishing private data.

## Default behavior

ChatGPT Work records sanitized command successes, failures, user-reported friction, and resolutions in a local `session-events.jsonl` file inside the chosen output folder. At the end of the session it generates `session-review.md`.

The report replaces user home paths, strips URL query strings, and redacts common secret patterns. Sanitization reduces risk but does not replace human or agent review. The privacy checkbox must be marked before the CLI will submit anything to GitHub.

## Automatic GitHub submission

A user can tell ChatGPT Work once:

> Submit sanitized session reviews to GitHub automatically after I approve the privacy check.

The project can retain that preference in its instructions or memory. When GitHub CLI is authenticated, the agent runs:

```sh
python -m video_compression --session-dir "/path/to/session" feedback submit "/path/to/session-review.md"
```

This creates an issue labelled `session-feedback`. The issue template also adds `needs-triage`. The repository does not silently change its own code from untrusted feedback.

Repository owners with workflow-scoped GitHub access can copy `examples/github-workflows/learning-intake.yml` to `.github/workflows/` to add an automatic privacy reminder and acknowledgement. The template is optional because the engine and issue intake do not require Actions.

## Manual fallback

If GitHub access is unavailable, open:

https://github.com/krishanraja/video-compression/issues/new?template=session-feedback.yml

Then copy and paste `session-review.md`. The report is ordinary Markdown and remains useful without any GitHub tooling.

## Turning feedback into learning

An issue is evidence, not automatically a rule. During maintenance, inspect open `session-feedback` issues and group recurring problems by root cause. For an accepted learning:

1. Reproduce the failure with a minimal safe fixture.
2. Add a regression test or deterministic check when possible.
3. Fix the smallest owning layer: code, test, documentation, or repository skill.
4. Run the full verification suite.
5. Link the change to the issue and close it only after the new behavior is proven.

This protects the engine from learning private, contradictory, or one-off behavior while still making every session easy to contribute.
