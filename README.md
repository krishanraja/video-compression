# Video Compression Engine

Compress large videos locally, estimate the result before a long encode, and optionally let ChatGPT Work review the content and extract useful clips.

No video is uploaded by this engine. The source is preserved. FFmpeg does the media work on the user's machine, while ChatGPT Work can guide the conversation and make purpose-aware cut suggestions from a local review pack.

## Fastest start in ChatGPT Work

1. Clone this repository.
2. Create a local project in the ChatGPT desktop app with this repository as the primary folder.
3. Add the folder containing the source video as another project folder when it is outside the repository.
4. Start ChatGPT Work and say:

> Need to compress a video

The repository's `AGENTS.md` and `.agents/skills/video-compression` skill are discovered automatically from the primary folder. The agent asks where the video is stored, what it is for, and whether you want suggested cuts. It then probes the file, estimates output size from representative samples, creates an optional review pack, compresses locally, and fully verifies the output.

A remote GitHub project can read the repository, but local media access requires a local project or another local execution environment with the video folder attached. ChatGPT Work's sandbox controls the actual file-access approval.

## Simple terminal command

Requirements:

- Python 3.10 or newer
- FFmpeg and ffprobe on `PATH`

Run directly from the cloned repository:

```sh
python -m video_compression
```

The interactive command asks the same three questions and saves the compressed video beside the source in a new folder.

Every ChatGPT Work session can also produce a sanitized local review of problems, workarounds, and outcomes. With the user's opt-in and an authenticated GitHub CLI, the agent can submit that review directly as a labelled issue. Without GitHub access, the same Markdown report is ready to copy and paste. See [the session learning loop](docs/LEARNING.md).

Install the reusable command with pipx:

```sh
pipx install git+https://github.com/krishanraja/video-compression.git
video-compress
```

### Install FFmpeg

Windows:

```powershell
winget install Gyan.FFmpeg
```

macOS:

```sh
brew install ffmpeg
```

Ubuntu or Debian:

```sh
sudo apt-get update
sudo apt-get install ffmpeg
```

## Composable commands

```sh
# Check the machine and test real encoders
python -m video_compression doctor

# Read metadata without changing the file
python -m video_compression probe "/path/to/input.mp4"

# Select a profile and working encoder
python -m video_compression plan "/path/to/input.mp4" --purpose "Drive sharing"

# Encode three representative samples and estimate the final size
python -m video_compression estimate "/path/to/input.mp4" --purpose "Drive sharing"

# Create a proxy, audio copy, contact sheet, and black/silence timeline
python -m video_compression analyze "/path/to/input.mp4" \
  --purpose "Find complete educational clips" \
  --output-dir "/path/to/output/review-pack"

# Compress atomically, then probe and fully decode the result
python -m video_compression compress "/path/to/input.mp4" \
  --purpose "Drive sharing" \
  --output "/path/to/output/compressed.mp4"

# Render purpose-aware segments selected in ChatGPT Work
python -m video_compression cut "/path/to/input.mp4" \
  --segments "/path/to/segments.json" \
  --purpose "Short social clips" \
  --output-dir "/path/to/output/segments"

# Record a problem that the user noticed
python -m video_compression --session-dir "/path/to/session" feedback note \
  --kind problem --message "The estimated size was too optimistic"

# Draft the sanitized end-of-session review
python -m video_compression --session-dir "/path/to/session" feedback draft \
  --output "/path/to/session/session-review.md" \
  --title "Estimate missed on screen recording" \
  --purpose "Email attachment" \
  --outcome "Compressed after lowering the target"
```

On PowerShell, put the command on one line or use PowerShell's backtick continuation instead of the shell backslashes shown above.

## Profiles and encoders

The purpose selects a sensible default profile:

| Purpose | Default | Typical use |
| --- | --- | --- |
| share | HEVC | Drive, messaging, family sharing |
| email | H.264 at 720p | Small, broadly playable attachment |
| universal | H.264 | Maximum playback compatibility |
| social | H.264 at 1080p | Social platform upload |
| web | H.264 fast-start | Website delivery |
| archive | HEVC | Smaller high-quality master |
| editing | High-quality H.264 | Later editing |

The engine tests encoders instead of trusting that a listed hardware encoder works. It prefers NVIDIA NVENC, Intel Quick Sync, or Apple VideoToolbox when available, then falls back to libx264, libx265, SVT-AV1, or libaom.

Use `--codec h264`, `--codec hevc`, or `--codec av1` to override the profile. AV1 is usually slow without recent hardware and is not the safest compatibility default.

Use `--quality high`, `--quality balanced`, or `--quality small`. A hard size cap can be requested with `--target-size-mb`, though content complexity means a small margin should be allowed.

## What "watching" means

The engine does not pretend motion statistics understand meaning. `analyze` creates evidence that a capable host can actually review:

- `review-proxy.mp4` for visual and audio review
- `review-audio.mp3` for audio-first material such as podcasts
- `contact-sheet.jpg` for quick navigation
- `timeline.json` for black and silent ranges
- `metadata.json` for technical facts

The ChatGPT Work skill requires the agent to say what it actually inspected. Suggested clips must be based on spoken or visual content and the user's purpose, not merely scene changes or silence. Accepted suggestions use [the segment schema](docs/segments.schema.json).

## Safety and output guarantees

- The source is never deleted by the engine.
- Output cannot equal the source path.
- Existing outputs are not replaced unless `--overwrite` is explicit.
- FFmpeg writes to a temporary file and the engine moves it into place only after a successful encode.
- Full verification checks streams, duration, size, and a complete decode.
- A JSON verification report is saved beside each compressed full video.

## Development

```sh
python -m unittest discover -s tests -v
```

The test suite includes a real synthetic-video flow when FFmpeg is installed.

Optional GitHub Actions templates for CI and feedback acknowledgement live in `examples/github-workflows`. They can be enabled by a repository owner whose GitHub token has workflow scope.
