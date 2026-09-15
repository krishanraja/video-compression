# Project state

Last verified: 2026-09-15

STATE_ROUTE: `docs/STATE.md`

SOURCE_LAYERS: User product requirement, current repository implementation, official ChatGPT Work project and skill discovery documentation.

PRODUCT_TRUTH: A local-first FFmpeg engine that a ChatGPT Work conversation can discover through repository instructions and use to interview, inspect, estimate, compress, verify, and optionally render purpose-aligned clips.

NON_GOALS: Cloud media hosting, automatic source deletion, generative editing, silent uploads, or claiming semantic review without rendering media evidence.

SURFACE_DEPENDENCIES: Chat interview -> local file access -> probe and encoder check -> sample estimate -> optional review pack -> compression -> optional segment rendering -> full verification.

VERTICAL_SLICE: One local source video becomes one smaller verified MP4, with a sample-based size estimate before the full run.

FIRST_SURFACE: Repository-triggered ChatGPT Work conversation.

CURRENT PHASE: Local implementation verified; initial GitHub publication retry pending.

VERIFICATION: Six tests pass, including a real FFmpeg compression, review-pack, segment, and full-decode flow. Repository skill validation and Python package build pass. A local feedback capture and review-draft canary passes.

NEXT ACTION: Amend the initial commit with inactive workflow templates, push it, then verify the remote revision and repository labels. The first push was rejected because the current OAuth token lacks GitHub workflow scope; no remote files changed.
