# Macintosh runtime audit and forging path

Status: evidence refreshed 2026-07-31.

This document separates SimAnt-specific evidence from reusable PortForge
runtime behavior. No reference-project source was copied. The references were
used to check application-visible contracts and architecture; their licenses
remain incompatible with copying implementation code into PortForge without a
separate licensing decision.

## Verified SimAnt baseline

The canonical short regression is:

```powershell
python scripts\verify_replay.py
python scripts\verify_snapshot_resume.py
python scripts\analyze.py --no-build
python scripts\lift.py --no-build --snapshot `
    artifacts\snapshots\determinism_30000000\run_a.pfmacsnapshot
```

`verify_replay.py` launches the Qt runtime twice with the same journal and an
exact 30,000,000-instruction stop. Both runs currently end at PC `0x024444`
with seven guest windows, event cursor 4, and timeline tick 849. The compared
artifacts are byte-identical:

- restorable manifest:
  `8f64c2e63d1be5528d3e87da37a8d9c64a80dce4b2505f2b2ce7a36fe70e4c02`
- guest RAM:
  `432e580d210eb90a554a40bf2ff628feb107259155f29e8546ac0dee370868f3`
- executed-byte map:
  `47838ef28fcfaeeb798efb7c427e6d1d4c6b9860f94a4bc3890a036c56e9f3ca`
- persistent manager state:
  `9b1f4e393459a623323ba4d536d610f16683bb6318c06141793cac818ba2f838`

The full machine-readable result is
`artifacts/analysis/determinism_30m.json`. A separate resize/gameplay journal
has reached 130,000,000 instructions, event cursor 99, and PC `0x6FF6D2`
without an unsupported trap. The short replay is the pinned regression because
it is fast enough to run routinely; the longer run remains supporting reach
evidence, not the canonical digest.

This checkpoint includes the shared MC68000 correction that charges 12 cycles,
not 8, for an untaken `Bcc.W` after fetching its extension word. The executed
byte map stayed identical across that correction, while the deterministic
timeline and RAM digest changed as expected.

The snapshot is now a restorable safe-boundary checkpoint. In addition to
authenticated RAM and executed-byte coverage, `state.bin` explicitly encodes
CPU/runtime state, manager Handles and resources, loaded segments and patched
jump tables, events, QuickDraw ports, Toolbox managers, callback queues,
coverage, and the replay cursor. It contains no host pointers or compiler
object layout. The image, application, machine profile, all three regions, and
the replay journal (when present) are authenticated before continuation.

`verify_snapshot_resume.py` checkpoints the resize replay at 10,000,000
instructions, restores it, and executes 2,000,000 more. Its final RAM,
executed map, persistent state, manifest, PC `0x022BEA`, tick 340, and replay
cursor 123 are byte-identical to an uninterrupted 12,000,000-instruction run.

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
  CODE segments and falls back when source bytes change;
- correlation of static MPW export ranges with dynamic executed bytes and trap
  calls;
- correct `ApplZone` and `MemErr` low-memory contracts;
- generic implementations and focused tests for `SetPt`, `TextMode`,
  `PaintRect`, `InsetRect`, `DisposeRgn`, and `ExitToShell`;
- the game-owned two-run deterministic verifier.

All runtime changes are general Macintosh contracts in `port_forge`.
SimAnt’s ISO path, creator/application choice, journals, snapshots, pinned
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
   known reached failure in earlier interactive evidence.
2. **Dialog Manager and TextEdit.** Ten Dialog and nine TextEdit slots account
   for the largest coherent UI gap. They should share guest records and event
   semantics with the existing Window/Control Managers and project only
   standard widgets to Qt.
3. **Macintosh generated semantics and parity machinery.** Stable identities,
   source-authenticated lift plans, movable-segment native block registration,
   and source-change fallback now exist. The Mac path still needs generated
   instruction semantics, function ABI/effect descriptions, and automatic
   original-versus-native entry/return checkpoint comparison.
4. **Remaining graphics contracts.** `SetPortBits`, `ClosePort`, `SetCPortPix`,
   and `SetCPixel` remain fail-loud. The reached `GetFontInfo` and `PaintRgn`
   paths now use the synthetic text metrics and retained region raster.
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
   callbacks, and Qt PCM output work. Extended/compressed headers, MACE,
   double-buffer commands, mixing/polyphony, MIDI/SONG sequencing, and exact
   completion timing do not.
8. **Remaining utilities and explicit failure policy.** `FixMul`,
   `UpperString`, `TEGetOffset`/`TEDispatch`, `Pack2`, and `Debugger` need either
   faithful implementations or tested application-appropriate error behavior.
9. **Trusted-oracle automation.** PortForge has deterministic self-comparison,
    but not automated frame/checkpoint comparison against Mini vMac, Basilisk
    II, or real captured System 7 behavior.

The exact 45-slot frontier and every static caller site are in
`artifacts/analysis/mac_trap_frontier.json`.

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
