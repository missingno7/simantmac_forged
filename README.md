# SimAnt Macintosh forged project

This project boots the original Macintosh SimAnt application directly from
its HFS CD image through PortForge. Proprietary media remains ignored; exact
ISO, HFS application, Finder metadata, and resource-fork identities are pinned
in `game.json` and `docs/asset-inventory.md`.

## Run

```powershell
python scripts\play.py
```

The Qt frontend is a host presentation/input adapter. CPU cycles, Event
Manager ticks, VBL tasks, Toolbox callbacks, QuickDraw state, and Sound Manager
state advance under the deterministic Mac runtime.

## Semantic replay

```powershell
python scripts\play.py --record-artifact canonical-event-poll-v2 `
  --replay-boundary-limit 8 --exit-after-replay `
  --no-snapshot-on-crash --unthrottled

python scripts\play.py --no-build `
  --play-artifact canonical-event-poll-v2 --exit-after-replay `
  --no-snapshot-on-crash --unthrottled
```

The common artifact uses `mac.event.poll` + point-local occurrence + phase.
Mac ticks and A-line addresses are evidence, not durable replay coordinates.
Host input becomes a typed guest-platform event only at a poll-before boundary.
Playback disables live host input and fails closed on identity, plan, boundary,
checkpoint, cursor, or terminal mismatch.

The selected corpus is
`artifacts/replays/canonical-event-poll-v2.pfreplay.json`. Its profile,
implementation plan, detachment report, and evidence are tracked in
`profiles/`, `regressions/`, and `recovery/`.

The complete oracle playback also publishes
`artifacts/evidence/canonical-event-poll-oracle-v3.json`. It binds real Mac
function visits, transfers, semantic regions, address coverage, and checkpoint
verification to the artifact and exact execution identity. The derived
`artifacts/atlas.pfatlas` tree is deletable and non-authoritative.

## Verification

```powershell
python scripts\verify_replay.py
python scripts\verify_snapshot_resume.py
python scripts\play.py --no-build --play-artifact canonical-event-poll-v2 `
  --evidence-out artifacts/evidence/canonical-event-poll-oracle-v3.json `
  --exit-after-replay --no-snapshot-on-crash --unthrottled
python port_forge\tools\pf_project.py atlas . rebuild-evidence `
  artifacts/evidence/canonical-event-poll-oracle-v3.json
python ..\port_forge\tools\pf_project.py validate .
python ..\port_forge\tools\pf_project.py platform conformance . --platform mac68k
```

The snapshot proof runs a real cold start to a checkpoint, resumes for a
second interval, runs the same total interval uninterrupted, authenticates all
snapshot regions, and requires byte-identical final memory, executed coverage,
and complete restorable state.

Current evidence proves semantic recording/playback, normalized observation,
deterministic Atlas rematerialization, and exact machine-state resume. Toolbox
service interiors keep the transfer graph explicitly partial.
Replay-session-exact continuation is not claimed because ArtifactV2
sessions are still cold-start-only in the Qt runner. Canonical audio/video
stream equivalence and generated/native/detached execution also remain open.

Timestamp-addressed `.pfmacreplay.json` journals and their pinned goldens are
retired development artifacts. They have no compatibility reader or active
workflow.
