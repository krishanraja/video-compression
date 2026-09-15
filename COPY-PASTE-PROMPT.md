# Complete ChatGPT Work opening prompt

Copy the entire prompt below into a new ChatGPT Work task. It covers local setup, the compression conversation, optional content-aware clips, output verification, and the privacy-gated session learning loop.

```text
Use https://github.com/krishanraja/video-compression as the operating repository for this task.

I need to compress a video locally. If this repository is attached as the primary folder of a ChatGPT Work local project, first read AGENTS.md and .agents/skills/video-compression/SKILL.md and follow them. If you only have this GitHub link and cannot access the repository or my source video, tell me once what repository folder, source folder, cloud permission, connector, or platform approval is needed. Do not claim that pasting a GitHub link grants local file access.

Guide me through the missing inputs in chat. Ask only one concise question at a time, and do not ask again for anything I have already supplied:

1. Where is the source video stored? Accept either a cloud-drive share URL or a local file path, as well as an already attached file. For a cloud-drive URL, use it when the link permissions allow access or the correct signed-in account or connector has access. For a local path, use it when the containing folder is attached to the local project or otherwise permitted, and let ChatGPT Work request my approval for local machine access when required. If access fails, identify the single missing permission or attachment precisely instead of restarting the interview.
2. What is the result for? If I am unsure, offer useful choices such as messaging or Drive sharing, email attachment, universal playback, social upload, web delivery, archive, or later editing. Ask for a hard size limit only if the destination requires one.
3. Do I want suggested cuts as well as compression? If yes, ask for a preferred clip length only when the purpose does not already make it clear.

After I answer those questions, carry the job through autonomously. Do not ask me what to do next at routine milestones. Use the host's normal file and command approval system when it must, but do not add repeated chat confirmation around ordinary reads, analysis, encoding, or verification.

Work locally and use the repository's Python CLI around FFmpeg. Do not upload the video. If I supplied a cloud-drive URL, access it through the available authenticated browser or connector, or download it to an agreed local working folder through the normal approval flow before running FFmpeg. Once the output folder is known, create a private session directory at <output-folder>/.video-compression-session and put --session-dir "<session-directory>" before the subcommand on every CLI command. Then:

1. Run doctor to check FFmpeg and test real encoders on this machine.
2. Probe the exact source and report its duration, resolution, codecs, and size.
3. Plan the encode from my purpose, requested compatibility, quality, and any size cap. Prefer a working hardware encoder when appropriate and retain a software fallback.
4. Run the representative-sample estimate before the full encode. Explain that its output-size range is an estimate, not a guarantee.
5. If I requested cut suggestions, run analyze and actually inspect the available review proxy, audio, contact sheet, timeline, or transcript. State exactly which evidence you inspected. Never say you watched or listened to the video if you only inspected metadata, frames, silence, or text. Judge valuable segments against my stated purpose. For each suggestion, give start, end, title, reason, and confidence. Save accepted segments in a manifest matching docs/segments.schema.json and render them with cut.
6. Compress the full video to the chosen local output folder. Preserve the source, never use the source path as the output, and do not overwrite an existing output unless I explicitly asked for that exact replacement.
7. Keep full verification enabled. Probe the result, check its streams and duration, compare its size with the source, and decode the entire output. Treat a failed full decode as a failed deliverable.
8. If a step fails, retain the source, diagnose the narrow cause, record the problem, fix the smallest owning layer, and rerun the failed step plus its adjacent verification.

Session learning is part of completion:

1. Let --session-dir record sanitized command outcomes automatically.
2. Whenever I report friction that commands cannot observe, record it with feedback note --kind problem. When a workaround succeeds, record it with feedback note --kind resolution.
3. Before finishing, run feedback draft and create <session-directory>/session-review.md.
4. Ensure the review includes my goal and purpose, the source environment and chosen profile or encoder without private paths, problems encountered, attempted fixes, the final resolution and result, what worked, the smallest reusable improvement proposed for the engine, and any unverified or residual risks.
5. Privacy-review the report before it leaves the machine. Remove credentials, tokens, private absolute paths, share-link query strings, personal names, transcript excerpts, and sensitive media details. Do not submit raw session logs, the source video, review media, or generated clips.
6. If I have already opted into automatic GitHub feedback in this task and GitHub CLI is authenticated, mark the report's privacy checkbox and submit it with feedback submit. Return the created issue URL. Otherwise leave the review locally ready to copy and give me this issue form: https://github.com/krishanraja/video-compression/issues/new?template=session-feedback.yml
7. GitHub feedback is useful but must never block delivery of the compressed video and clips.

Finish only when you can give me absolute clickable paths to the compressed video, its verification report, any rendered clips, and the local session review. Report input and output sizes, percentage reduction, codec and encoder, full-decode result, segment status, and GitHub feedback status. Clearly distinguish suggested segments from clips that were actually rendered.
```

The GitHub link supplies the public operating instructions. A cloud-drive source also needs valid share or account permissions. A local-path source needs the containing folder to be available to the local project and the user's approval for machine access when ChatGPT Work requests it.
