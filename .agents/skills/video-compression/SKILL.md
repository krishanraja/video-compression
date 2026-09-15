---
name: video-compression
description: Guide and execute local video compression, size estimation, media review, and optional valuable clip extraction. Use when a user says "Need to compress a video" or otherwise asks to shrink, re-encode, review, or cut a video. Do not use for generative video creation.
---

# Video Compression

Turn a source video into a smaller verified local file, with optional purpose-aligned clips. Use the repository CLI for deterministic media work and use the host's media capabilities for semantic judgment.

## Start the conversation

Ask only for information that is still missing, one concise question at a time:

1. Ask where the video is stored. Accept a local path, an attached file, or a share link. For a local path outside the project, let ChatGPT Work request access or ask the user to attach its folder to the local project. For a link, explain the exact download target before downloading.
2. Ask what the result is for. If the user is unsure, offer the relevant examples: messaging or Drive sharing, email, universal playback, social upload, web delivery, archive, or later editing. Ask for a hard file-size limit only when the platform imposes one.
3. Ask whether they want suggested cuts as well as compression. If yes, ask for a preferred clip length only when the purpose does not make it clear.

Do not ask for separate chat confirmation before each routine read, analysis, transcode, or verification step. Platform file and command approvals still apply.

After the output folder is known, create a private session subfolder and pass it to every CLI command with `--session-dir "<output>/.video-compression-session"`. This records sanitized command outcomes locally. Whenever the user reports friction that a command cannot observe, run `feedback note --kind problem --message "..."`. Record a successful workaround with `--kind resolution`.

## Inspect and plan

Run from the repository root with `python -m video_compression` or use the installed `video-compress` command.

1. Run `python -m video_compression doctor` once for the machine.
2. Run `probe` on the exact source and report duration, resolution, codecs, and size.
3. Run `plan --purpose "..."` to choose a working hardware encoder when available, with a software fallback.
4. Run `estimate --purpose "..."` before a long transcode. Tell the user that the range is sample-based, not a guarantee.

Use HEVC for small personal sharing when playback compatibility permits. Use H.264 for broad compatibility, email, social, and web delivery. Use AV1 only when the user values maximum compression over encode time and playback support.

## Review and suggest cuts

When cuts are requested, run `analyze` into an output subfolder. It creates a low-bandwidth review proxy, audio copy, contact sheet, metadata, and black/silence timeline.

Actually render and inspect the review proxy with the host's video and audio capabilities. Use the contact sheet and timeline to navigate. If direct video or audio review is unavailable, say exactly which evidence was inspected. Never say the video was watched or listened to when only metadata, frames, silence, or a transcript was reviewed.

Value is purpose-dependent. Recommend only segments whose spoken or visual content supports the user's stated purpose. For each candidate, provide start, end, title, reason, and confidence. Prefer complete ideas with clean handles over arbitrary high-motion excerpts. Save accepted candidates in a JSON manifest matching `docs/segments.schema.json`, then run `cut`.

## Compress, render, and verify

- Write outputs to the user-named local folder. Otherwise create `<source name> - compressed` beside the source.
- Preserve the source. Never delete it unless the user explicitly requests deletion of that exact file.
- Do not overwrite an existing output unless the user explicitly asked to replace it.
- Use `compress` for the full video and `cut` for accepted segments.
- Keep full verification enabled. It probes the output, checks duration and streams, compares size, and decodes the whole file.
- If a command fails, retain the source, report the specific failure, correct only the smallest safe cause, and rerun the failed and adjacent check.

Finish with absolute paths, input and output sizes, percentage reduction, codec and encoder, verification result, and any segment paths. Distinguish recommendations from rendered clips.

## Capture reusable learning

Before finishing every session, run `feedback draft` to create `session-review.md` in the session folder. Add a concise user-visible summary and the smallest proposed reusable learning. Review it for private paths, credentials, share-link query strings, names, transcript excerpts, or sensitive media details.

If the user has already opted into automatic GitHub feedback, mark the privacy checkbox and run `feedback submit` after the report is safe. Otherwise leave the local review ready to copy and provide the repository's Session feedback issue link. A GitHub submission is an external write and follows the host's approval policy. Do not block delivery of the compressed video on feedback submission.
