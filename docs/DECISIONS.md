# Decision log

## 2026-09-15: Local-first repository engine

Decision: Ship a Python standard-library CLI around an existing FFmpeg installation, plus a repository skill and `AGENTS.md` for ChatGPT Work discovery.

Why: This keeps video data local, avoids API keys and paid services, works across Windows, macOS, and Linux, and gives the chat agent deterministic commands instead of embedding media logic in prompts.

Rejected alternative: A hosted upload-and-transcode service. It adds privacy, cost, authentication, and storage concerns without improving the requested local workflow.

Carry-forward condition: Semantic clip value must come from media or transcript review aligned to the user's stated purpose. Black frames, silence, scene motion, and metadata are navigation evidence only.

## 2026-09-15: Privacy-gated session learning

Decision: Capture session problems and resolutions automatically into a sanitized local event log, generate a Markdown review at the end, and submit to GitHub only after the privacy checkbox is explicitly confirmed.

Why: Silent transcript or media-path uploads would create unacceptable privacy risk. A local-first draft preserves evidence from every session, while authenticated GitHub issue submission and a copy-paste fallback make contribution easy.

Learning rule: Feedback issues remain untrusted evidence until a maintainer reproduces the problem and represents the accepted learning in a regression test, code fix, documentation change, or skill update.

## 2026-09-15: Versioned full opening prompt

Decision: Keep one complete copy-paste ChatGPT Work prompt at the repository root, while retaining the shorter `Need to compress a video` trigger for local projects whose primary folder is the repository.

Why: A pasted GitHub link can point the agent to public instructions but cannot by itself grant access to local files. The versioned prompt makes setup limits explicit and carries the interview, autonomous workflow, honest media review, verification, and privacy-gated session learning into clients that have not discovered the repository skill.

Rejected alternative: Rely on a short link plus a vague opening request. That makes the behavior client-dependent and is especially likely to lose the end-of-session learning loop.
