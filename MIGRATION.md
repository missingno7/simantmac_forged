# Replay consolidation result

Macintosh SimAnt now uses the cross-platform `ReplayArtifactV2` and common
`ReplaySession` over a Mac-owned `EventPollReplayDriver`. The before boundary
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

Real-project evidence covers two full artifact playbacks and direct-versus-
resumed machine-state equivalence. Replay-session continuation and canonical
audio/video stream claims remain deliberately unclaimed.

The canonical playback now publishes exact-identity `ReplayEvidenceV3`, and
the tracked Atlas is a non-authoritative projection rebuilt atomically from
that file. Mac Toolbox service interiors remain declared as partial transfer-
graph coverage rather than being inferred as guest code.
