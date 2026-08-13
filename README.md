# SimAnt Macintosh forged project

This project boots the original Macintosh SimAnt application directly from
its HFS CD image through PortForge. Proprietary media remains ignored; exact
ISO, HFS application, Finder metadata, and resource-fork identities are pinned
in `game.json` and `docs/asset-inventory.md`.

## Player and development interface

```powershell
python scripts\play.py
python scripts\play.py --runtime generated
python scripts\play.py --help
```

Plain invocation selects the declared `oracle` stage. `--runtime generated`
builds the project-owned Qt composition, executes the source-guarded
`mac.code.1.4` instruction and linear leaf `mac.code.2.2906` natively, and
retains observable interpreter fallback everywhere else. It is a
generated-with-fallback proof, not a
detached port, and still requires the exact original ISO. The Qt frontend only
presents pixels/audio and collects host intent. Direct play, ArtifactV2
recording, playback, and resumed sessions all traverse the same
`EventPollReplayDriver`, `Mac68kReplayRuntimeAdapter`, `LiveReplaySession`, and
semantic cycle. CPU cycles, Event Manager ticks, VBL tasks, Toolbox callbacks,
QuickDraw state, and Sound Manager source state remain guest/runtime authority.
The oracle runtime's ArtifactV2 capability is declared in
`portforge.project.json`, including the authoritative event-poll boundary
profile and immutable oracle implementation plan used for replay preflight.

Interactive controls:

- F11 starts ArtifactV2 recording from an exact current machine snapshot, or
  stops the active recording at the returned semantic seam.
- F12 publishes a `.pfsession.json` continuation plus an authenticated exact
  machine attachment. During recording it also binds the recording base;
  during playback it binds the immutable replay.

Host input is encoded into typed Macintosh channels. Ordinary transactions
become visible at `mac.event.poll:before`; input observed while a poll is
already pending is session-owned and timestamped in deterministic `mac.tick`
time. This lets classic modal button tracking observe mouse-up without
fabricating a semantic boundary or depending on host wall time.
Long simulation work between polls stays inside one semantic advance, but the
event-poll driver pumps Qt every 20,000 guest instructions for input,
presentation, and realtime pacing. The Qt runner deliberately uses the
non-transactional callback path so it does not serialize a full rollback image
at every high-frequency poll; a guest failure is therefore fail-stop for that
process. None of these host pumps invents an extra replay boundary.

## Replay workflows

```powershell
# Interactive: press F11 whenever the desired scenario begins/ends.
python scripts\play.py

# Start recording immediately and finish after eight completed polls.
python scripts\play.py --record-replay canonical-event-poll-v2 `
  --replay-boundary-limit 8 --exit-after-replay --auto-click-splash `
  --unthrottled

# Interactive playback.
python scripts\play.py --play-replay canonical-event-poll-v2

# Bounded offscreen verification with ReplayEvidenceV3.
python scripts\play.py --verify-replay canonical-event-poll-v2

# Structural ArtifactV2 inspection through the shared artifact tool.
python scripts\play.py --inspect-replay canonical-event-poll-v2
```

Playback disables live host input and fails closed on replay/environment,
execution plan, boundary, event cursor, checkpoint, continuation, or terminal
mismatch. `--headless` uses Qt's offscreen sink and requires a bounded replay,
recording boundary limit, session-snapshot boundary, or diagnostic instruction
limit. A recording or playback publication retains its mode when resumed.
Advanced runner arguments remain available only after an explicit `--`
delimiter.

## Session snapshots

```powershell
# F12 writes the target announced at launch.
python scripts\play.py --session-snapshot artifacts\snapshots\manual.pfsession.json

# Resume direct, recording-draft, or playback mode from its publication.
python scripts\play.py --snapshot artifacts\snapshots\manual.pfsession.json

# Deterministically finish a resumed recording draft after eight more polls.
python scripts\play.py --snapshot artifacts\snapshots\draft.pfsession.json `
  --headless --replay-boundary-limit 8

# Exercise the exact F12 path without a visible host window.
python scripts\play.py --headless --snapshot-after-polls 8 `
  --session-snapshot artifacts\snapshots\smoke.pfsession.json

python scripts\play.py --inspect-session manual
python scripts\play.py --verify-session manual
```

The F12 callback only defers a request. Publication happens after the shared
semantic cycle returns; the `LiveSessionContinuationEnvelope` and machine
attachment are captured without intervening guest execution and are required
to contain byte-identical memory, executed-map, and manager-state payloads.

Raw `.pfmacsnapshot` directories remain available through
`--snapshot-on-crash` and `--snapshot` for diagnostic compatibility and the
older machine-only equivalence gate. They are not replay authority and do not
contain a recording draft or playback cursor.

The current raw directory format is
`portforge-mac68k-restorable-snapshot-v2`. Its state v3 payload serializes
`Machine::event_cursor` once and reports it as `machine_event_cursor`.
Restorable state v1/v2 and Mac continuation v2 are rejected, not migrated.

## Evidence, Atlas, and current blockers

The complete oracle playback can publish execution-bound ReplayEvidenceV3.
The tracked `artifacts/atlas.pfatlas` is a deletable, regeneratable projection
of that evidence, never runtime or replay authority.

```powershell
python scripts\verify_replay.py --build
python scripts\play.py --runtime generated --verify-replay `
  canonical-event-poll-v2
python scripts\verify_native_entry.py
python scripts\build_function_census.py
python scripts\verify_snapshot_resume.py --build
python port_forge\tools\pf_project.py atlas . rebuild-evidence `
  artifacts\evidence\canonical-event-poll-oracle-v3.json
python ..\port_forge\tools\pf_project.py validate .
```

Live Atlas is deliberately reported as unavailable by `scripts/play.py` until
stable M68K identity telemetry can fan out beside ReplaySessionEvidence without
installing a second observer or address-only identity authority. Offline Atlas
rebuild is supported from the oracle trace. Generated execution is retained as
separate cross-representation evidence so the Atlas does not duplicate every
interpreted occurrence in the same canonical trace.

Mac ArtifactV2 currently publishes canonical state only. QuickDraw and Sound
Manager deterministic source state are resumable, but canonical PCM and video
commit streams are not implemented, so artifacts do not claim
`canonical-audio`, `canonical-video`, `audio-continuing`, or
`video-continuing`. Generated/native execution is partial: one entry
instruction and one complete linear function are cross-representation verified
and the rest is explicit interpreter fallback. The stable function census
keeps all 359 MPW exports queryable through `pf_project status`, `frontier`,
and `context`. Detached execution remains open.
The exact gap between the current oracle, a Win16-style packaged
generated-with-fallback runtime, and a genuinely detached product is recorded
in `docs/standalone-readiness-audit.md`.

The retired `portforge-mac68k-replay-v1` timestamp journal has no compatibility
reader, alias, or active workflow.

## Generated Windows bundle

```powershell
python scripts\package_release.py
python scripts\verify_release.py
```

The package contains `SimAntMac.exe`, the generated-with-fallback Qt runtime,
and its required Qt/MinGW libraries. It deliberately excludes the original
CD image. Copy the exact `SimAnt_CD.iso` identified by `game.json` beside
`SimAntMac.exe`; the launcher and runtime reject a different image SHA-256.
This is the Macintosh analogue of the current Win16 bundle, not a detached
source port.
