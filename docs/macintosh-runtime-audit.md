# Macintosh runtime audit and forging path

Status: architecture refreshed 2026-08-12; the tracked canonical corpus remains
the previously recorded conformance evidence until deliberately re-frozen.

This document separates SimAnt-specific evidence from reusable PortForge
runtime behavior. No reference-project source was copied. The references were
used to check application-visible contracts and architecture; their licenses
remain incompatible with copying implementation code into PortForge without a
separate licensing decision.

## Verified baseline and current session architecture

The canonical tracked regression remains `ReplayArtifactV2` at
`artifacts/replays/canonical-event-poll-v2.pfreplay.json`. Validate its content
bindings and execute its declared playback passes with:

```powershell
python scripts\verify_replay.py --build
python scripts\play.py --verify-replay canonical-event-poll-v2
python scripts\verify_snapshot_resume.py --build
```

The current Qt runtime no longer has separate direct and artifact loops. Every
mode uses `EventPollReplayDriver`, `Mac68kReplayRuntimeAdapter`,
`LiveReplaySession`, and `SinglePointLiveCycle`. The driver step alone composes
M68K execution, VBL, Sound Manager callbacks, and Event Manager time.
Presentation is observational. The Qt runner uses non-transactional semantic
advances and the event-poll driver pumps Qt internally every 20,000 guest
instructions so long work remains responsive without a per-boundary durable
rollback.

F11 can begin recording mid-game. Before replacing the direct session, the
runner writes an authenticated exact machine base beside the future replay and
binds its directory digest, canonical state, image, application, profile, and
execution plan into ArtifactV2 identity. F11 stop finalizes at the next
returned semantic seam; no timestamp journal or viewer cursor exists.

F12 is a deferred host command. A key received during nested Qt processing
only sets a flag. After the live cycle returns, the runner captures a
`LiveSessionContinuationEnvelope` and exact machine directory without further
guest execution, byte-compares all three machine payloads with the envelope,
and publishes their content-bound attachment graph. Recording publications
retain the builder draft and recording base; playback publications retain the
immutable artifact. Resumption restores the same execution mode and semantic
occurrence.

The v4 continuation removes the old duplicate cursor from `state.bin`.
`Machine::event_cursor` is the sole platform input-delivery cursor and is
reported as `machine_event_cursor`; ReplaySession position remains solely in
the live envelope. Restorable state v1/v2 and Mac continuation v2 fail closed.

`verify_snapshot_resume.py` remains the raw machine-only equivalence gate. Raw
`.pfmacsnapshot` directories authenticate RAM, executed coverage, and portable
manager state, but they are now explicitly diagnostic compatibility rather
than replay/session authority.

The tracked conformance evidence predates the new live-session publication
workflow. Focused shared tests prove record-draft continuation restore,
canonical-state equality, equal final ArtifactV2 output, and terminal playback;
a refreshed real F12 corpus should be frozen only after the platform gaps below
are closed.

## What the audit found

The application contains 13 `CODE` resources and 835 resources in total,
including 49 `snd `, 30 `MIDI`, 33 `SONG`, and 14 `INST` resources. The static
analyzer recursively decodes 123,172 of 182,266 CODE bytes (67.58%), proves
1,587 direct A-line sites across 219 canonical trap slots, and reports exact
resource offsets and stable `mac.code.<id>.<offset>` identities for each site.

The 30-million-instruction replay reaches:

- 610 distinct trap/caller sites covering 153 trap names;
- 247 distinct resource queries;
- 29 distinct guest low-memory access/caller sites;
- 205 MPW export ranges with at least one executed byte.

Resource lookups are intentionally type-agnostic. The replay successfully
loads `CODE`, `PICT`, `STR#`, `snd `, `WIND`, `MENU`, `CNTL`, `MIDI`, `TILE`,
`ZHEX`, `DATA`, `DREL`, `CARD`, `MDRV`, and `clut` resources. Misses for
optional `INST`, `SONG`, `SMOD`, `cctb`, `CURS`, and `Jnth` resources are now
visible in evidence rather than mistaken for unsupported resource formats.

Guest low-memory tracing exposed a real contract error: PortForge published
`ApplZone` at `0x012C`, while SimAnt reads the classic `ApplZone` global at
`0x02AA`. The runtime now uses `0x02AA` and mirrors every Memory Manager result
into `MemErr` at `0x0220`. Other reached globals include `ApplLimit` (`0x0130`),
`SysEvtMask` (`0x0144`), `RndSeed` (`0x0156`), `Time` (`0x020C`), `ROM85`
(`0x028E`), `AppParmHandle` (`0x0AEC`), and floating-point state at `0x0A4A`.
Unknown or less confidently named accesses stay in the evidence report rather
than receiving guessed semantics.

The executed-code write counter is 66 bytes across 22 grouped writes. Every
write is runtime-authored, never guest-authored. They form 11 pairs of a
two-byte and four-byte write to the six-byte MPW unloaded-segment stubs after
the stub reaches `LoadSeg`. This is expected jump-table patching, not
unexplained self-modifying SimAnt logic.

## Implemented high-value fixes

The current slice adds:

- stable cumulative trap coverage, including incomplete calls when a trap
  fails;
- Resource Manager hit/miss coverage for both ID and name queries;
- guest-only low-memory tracing that excludes Toolbox mirror accesses;
- executed-code-write attribution distinguishing guest and runtime writes;
- diagnostic snapshot v2 with strict UTF-8-safe Macintosh path serialization,
  CODE ranges, code-generation state, and all coverage collections;
- versioned restorable snapshot state with authenticated replay continuation,
  strict corruption checks, QuickDraw surface reconstruction, and audio
  presenter adoption;
- exact site/range output from the static trap analyzer;
- `pf_mac_lift` instruction/CFG plans with source hashes, stable CODE
  identities, branch targets, MPW edges, and explicit decode frontiers;
- a stable exact-source-guarded native block registry that follows movable
  CODE segments, dispatches from the shared executor, and falls back before
  native effects when source bytes change;
- a generated-with-fallback Qt composition whose first SimAnt instruction
  (`mac.code.1.4`) passes 8,192 exhaustive register/flag parity cases and the
  complete canonical ArtifactV2 playback;
- host-time display pacing, exact QuickDraw source caching, and a bounded Qt
  paint flush so long simulation/recording advances cannot leave a responsive
  Quick Game frame visually stale or repeatedly reproject unchanged bitmaps;
- correlation of static MPW export ranges with dynamic executed bytes and trap
  calls;
- correct `ApplZone` and `MemErr` low-memory contracts;
- generic implementations and focused tests for `SetPt`, `TextMode`,
  `PaintRect`, `InsetRect`, `DisposeRgn`, and `ExitToShell`;
- correct `OpenRgn` recording of the outside `FrameRoundRect` boundary, so a
  closed region contains the rounded interior independently of pen width;
- native shell maximize/resize presentation and host-completed guest resize
  delivery that honors the application's complete Macintosh limit Rect and
  reasserts accepted geometry after repeated out-of-range native drags;
- reached styled TextEdit contracts for selection, deletion, insertion and
  update redraw, including deterministic guest Handle state, clipping,
  metrics, carriage returns and word wrapping;
- a shared PICT v1/v2 decoder path with byte-opcode state, patterned rectangle
  and relative-text records, and one-bit BitMap transfers in classic modes;
- the game-owned two-run deterministic verifier.

All runtime changes are general Macintosh contracts in `port_forge`.
SimAnt’s ISO path, creator/application choice, replay corpus, snapshots, pinned
digest, and candidate ranking remain in this project.

## Reference comparison

### systemless

The most useful concepts are application-facing high-level emulation, a
virtual filesystem that preserves data/resource forks and Finder metadata,
explicit trace sinks, authoritative host-side SoundChannel queues, and
deterministic trap tests. PortForge now has comparable trace identities,
resource/low-memory evidence, and restorable application-runtime checkpoints,
but still lacks a writable fork-aware filesystem and complete Sound Manager
formats.

### Mini vMac

Mini vMac is the low-level oracle for event/tick ordering, low-memory layout,
QuickDraw corner cases, audio scheduling, and real ROM/System side effects.
PortForge intentionally does not adopt its hardware architecture. A repeatable
external-oracle capture and checkpoint comparison is still missing.

### Basilisk II

Basilisk II demonstrates practical System 7 host integration, especially
extended filesystem metadata, input/ADB translation, graphics, and host audio.
PortForge’s native Qt widgets remain projections of authoritative guest
objects, which is the correct boundary, but filesystem metadata and multi-voice
audio are substantially behind.

### Executor

Executor is the most useful permissively licensed ROM-free behavioral
reference. Its segment patch/unpatch and lock/purge behavior, Event Manager
peek/dequeue distinction, Memory Manager zones, and Resource Manager semantics
are directly relevant. PortForge’s observed MPW patching is deterministic, but
segment unloading/purging and full zone behavior remain approximate.

## Remaining blockers, ordered by impact

1. **Writable File Manager and Standard File behavior.** `Open`, `Close`,
   `Read`, `Write`, positioning, metadata, create/delete, EOF and volume flush
   are still in the static frontier. Save games require a deterministic
   writable overlay preserving forks and Finder metadata. `Pack3` is also a
   reached as `SFGetFile` (selector 2) in the 2026-07-31 interactive evidence.
   It remains explicit until the host picker can return an HFS/File Manager
   identity rather than only a host path.
2. **Remaining Dialog Manager and TextEdit selectors.** Resource-backed
   `GetNewDialog`/`DITL` records, item get/set, update drawing, dialog-event
   routing, selection, and disposal now cover SimAnt's real save-on-quit
   prompt. Dialog item text mutation, editable fields, and the remaining
   TextEdit editing, measurement, and scrolling selectors still form the
   largest coherent UI gap. They should continue sharing guest records and
   event semantics with the existing Window/Control Managers and project only
   standard widgets to Qt.
3. **Macintosh generated semantics and parity machinery.** Stable identities,
   source-authenticated lift plans, movable-segment native block registration,
   source-change fallback, and exhaustive parity for the first generated
   instruction now exist. The Mac path still needs a general generator,
   function ABI/effect descriptions, and automatic original-versus-native
   entry/return checkpoint comparison for wider blocks.
4. **Remaining graphics contracts.** `SetPortBits`, `ClosePort`, and
   `SetCPortPix` remain fail-loud. The reached `SetCPixel`, `GetFontInfo`,
   `PaintRgn`, and `FillCRgn` paths now use indexed pixel writes, synthetic
   text metrics, retained regions, and validated PixPat graphs. The
   2026-07-31 `$AA12` snapshot resumes through
   one million further instructions after its `ditherPat` requested RGB is
   mapped to the active indexed palette.
   Region, PixMap, color-table, and `CopyBits` behavior should continue to be
   expanded only from reached tests and oracle comparisons.
5. **Timing/event completeness.** `Delay` and `FlushEvents` need deterministic
   timeline semantics. VBL callbacks work, but tick/VBL/audio ordering needs
   checkpoint comparison against a trusted Mac.
6. **Resource mutation and purge behavior.** `SetResAttrs`, `ChangedResource`,
   and `WriteResource` need the writable overlay. Handle zones, relocation,
   purge, lock, resource detachment, and segment unpatching need stronger
   behavioral tests.
7. **Sound and music breadth.** Standard 8-bit sampled buffers, looping,
   callbacks, queued same-channel host output, and Qt PCM output work.
   Disposed channel use returns `badChannel`; restoring the complete pre-trap
   stack from the 2026-07-31 `SndDoCommand` stop continues through one million
   further instructions. Snapshot restore also preserves a queued buffer that
   was canceled before its scheduled start tick. Extended/compressed headers, MACE,
   double-buffer commands, mixing/polyphony, MIDI/SONG sequencing, and exact
   completion timing do not.
8. **Remaining utilities and explicit failure policy.** `FixMul`,
   `UpperString`, `TEGetOffset`, unimplemented `TEDispatch` selectors, `Pack2`,
   and `Debugger` need either faithful implementations or tested
   application-appropriate error behavior.
9. **Trusted-oracle automation.** PortForge has deterministic self-comparison,
    but not automated frame/checkpoint comparison against Mini vMac, Basilisk
    II, or real captured System 7 behavior.

The exact 40-slot frontier and every static caller site are in
`artifacts/analysis/mac_trap_frontier.json`.

Historical 2026-07-31 development-trace evidence reached `SetCPixel` at instruction
432,751,354. The old checkpoint is repaired from its authenticated incomplete
trap trace, re-enters `$AA16` at `mac.code.5.13210`, executes five pixel writes,
and continues for one million instructions. New unresolved A-line stops retain
the failing PC directly, so future trap snapshots need no legacy repair.

## First native replacement candidates

The lift plan contains 40,160 decoded instructions and overlays the canonical
checkpoint onto 205 executed MPW export ranges. Its stricter first pass finds
49 ranges with no direct static trap, unresolved indirect transfer, or
dynamically attributed trap call. The best initial parity experiments are
small, completely executed ranges:

| Stable identity | Span | Executed | Coverage |
|---|---:|---:|---:|
| `mac.code.7.3372` | 206 | 206 | 100% |
| `mac.code.12.7810` | 188 | 188 | 100% |
| `mac.code.10.10840` | 110 | 110 | 100% |
| `mac.code.5.9802` | 90 | 90 | 100% |
| `mac.code.8.17138` | 80 | 80 | 100% |
| `mac.code.12.1938` | 60 | 60 | 100% |
| `mac.code.1.218` | 54 | 54 | 100% |
| `mac.code.1.272` | 32 | 32 | 100% |
| `mac.code.1.338` | 32 | 32 | 100% |

These are candidates, not yet claims of platform-independent logic. MPW export
ranges extend to the next export and may contain local routines or data.
Before replacement, each needs control-flow recovery, indirect-call tracing,
read/write-set capture, ABI reconstruction, and original/native parity at
entry and return. Large low-coverage trap-free ranges are lower priority even
when they have more executed bytes.

Functions with direct trap sites are mapped separately in the same report.
They form the Macintosh compatibility edge and should generally remain 68k
until the relevant manager behavior is faithful, then be replaced by thin
adapters rather than folded into platform-neutral game logic.

## Can the runtime be detached?

Yes, the current direction can lead to a ROM/System-free final release.
PortForge already loads the application and resource fork without a ROM, runs
CODE resources through the shared 68k core, dispatches application-visible
Toolbox contracts, retains deterministic QuickDraw surfaces, and projects
native UI/audio/input at a backend boundary.

Detachment is not achieved yet. The required sequence is:

1. keep extending the faithful, restorable replay oracle;
2. generate native semantics behind the exact-byte-guarded hooks and add
   entry/return parity tapes;
3. replace small trap-free functions while preserving fallback;
4. identify and materialize a platform-neutral SimAnt state model;
5. replace Macintosh-facing orchestration with narrow native adapters;
6. prove the standalone native runtime against the same checkpoints;
7. exclude CODE resources, the 68k interpreter, Toolbox runtime, and original
   assets from the final product dependency graph.

This keeps Macintosh state out of the eventual game core while avoiding a
premature renderer or game-loop rewrite.
