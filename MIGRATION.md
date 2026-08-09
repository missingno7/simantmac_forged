# Replay consolidation result

Macintosh SimAnt now uses cross-platform `ReplayArtifactV2` and
`LiveReplaySession` over a Mac-owned `EventPollReplayDriver` for direct play,
recording, playback, and resumed session publications. The before boundary
is intercepted after A-line fetch but before instruction, coverage, trap,
cycle, or manager mutation. The after boundary is emitted only after the trap
and scheduler step commits.

The old `portforge-mac68k-replay-v1` tick journal and pinned golden were
retired, not relabelled. Replay environment identity encodes the HFS path as
portable ASCII escapes, so artifacts are valid UTF-8 while preserving original
MacRoman bytes. The implementation plan and actual running tool image form the
per-execution identity.

Activation and deactivation are explicit typed events. Completed window moves
and resizes are replayed through the Window Manager rather than rejected or
reduced to host geometry.

F11 creates a content-bound exact snapshot base before a new mid-game
recording and finalizes only at a returned semantic seam. F12 defers out of
nested Qt/event-poll execution, then publishes one execution-bound live-session
envelope with byte-identical machine, recording-base, or playback attachments.
Recording drafts resume through `ReplayArtifactBuilder::from_draft_json`; no
journal, frontend cursor, or viewer scheduler is involved.
The shared runner accepts a semantic boundary limit on a resumed recording,
so headless conformance finishes the same draft that interactive F11 stops at
a returned event-poll seam.

Mac continuation identity is now `pf-continuation-mac68k-v3`. The cursor-free
restorable-state v3 binary stores only `Machine::event_cursor`; diagnostic
manifests name it `machine_event_cursor`. Retired restorable state v1/v2 and
continuation v2 fail closed.

Real-project evidence covers two full artifact playbacks and direct-versus-
resumed raw machine-state equivalence. Shared focused tests additionally cover
live recording-draft continuation and equal final ArtifactV2 output. Canonical
PCM/video commit streams and live identity-resolved Atlas remain deliberately
unclaimed until their platform contracts exist.

The canonical playback now publishes exact-identity `ReplayEvidenceV3`, and
the tracked Atlas is a non-authoritative projection rebuilt atomically from
that file. Mac Toolbox service interiors remain declared as partial transfer-
graph coverage rather than being inferred as guest code.
