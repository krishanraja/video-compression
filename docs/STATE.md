# Project state

Last verified: 2026-09-15

STATE_ROUTE: `docs/STATE.md`

SOURCE_LAYERS: User product requirement, current repository implementation, official ChatGPT Work project and skill discovery documentation.

PRODUCT_TRUTH: A local-first FFmpeg engine that a ChatGPT Work conversation can discover through repository instructions and use to interview, inspect, estimate, compress, verify, and optionally render purpose-aligned clips.

NON_GOALS: Cloud media hosting, automatic source deletion, generative editing, silent uploads, or claiming semantic review without rendering media evidence.

SURFACE_DEPENDENCIES: Chat interview -> local file access -> probe and encoder check -> sample estimate -> optional review pack -> compression -> optional segment rendering -> full verification.

VERTICAL_SLICE: One local source video becomes one smaller verified MP4, with a sample-based size estimate before the full run.

FIRST_SURFACE: Repository-triggered ChatGPT Work conversation.

CURRENT PHASE: Published and remotely verified.

VERIFICATION: Six tests pass, including a real FFmpeg compression, review-pack, segment, and full-decode flow. Repository skill validation and Python package build pass. A local feedback capture and review-draft canary passes.

REMOTE READBACK: Public repository `krishanraja/video-compression`, default branch `main`, implementation commit `e5ae0d54acb61898225290e2906f03a005055ced`, with `session-feedback` and `needs-triage` labels present.

NOT VERIFIED: Fresh ChatGPT Work discovery on a separate user's local project. Static discovery paths, the repository skill, and local behavior are verified. The read-only fresh-client canary was not authorized by the host because it would transmit repository content to an external model service.

NEXT ACTION: Run the first real user compression session in a ChatGPT Work local project and submit any observed friction through the session learning loop.
