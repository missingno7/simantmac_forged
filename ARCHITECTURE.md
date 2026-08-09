# SimAnt Macintosh PortForge architecture

Status: living architecture map, updated 2026-08-02. The checked-out
`port_forge` gitlink and the project validator are the revision authority;
the earlier `e26eb0f4d96aaa4f9affce417ca7da9d18233ae2` baseline is historical.

## Existing execution layers

```text
game project
  assets, profiles, replays, snapshots, evidence, generated code
                         |
                         v
PortForge platform
  executable loading, OS/API services, deterministic events, canonical state
                         |
                         v
PortForge architecture + shared mechanisms
  CPU, formats, replay, observation, software surfaces
                         |
                         v
host presenter
  Qt windows, pixels, input collection, audio
```

The Win16 SimAnt path is:

```text
NE image -> x86_16 -> win16 KERNEL/USER/GDI -> ui::Surface -> Qt
```

Its reusable mechanisms are the checked loader/platform split, canonical
state, semantic ArtifactV2 sessions, continuation barriers,
exact-byte-guarded native execution, interpreter fallback, retained software
surfaces, and a host presenter that owns no guest semantics.

Its NE selectors, Pascal imports, KERNEL/USER/GDI objects, HWND/HDC values,
Windows messages, virtual-key codes, and Win16 runtime tables are not reusable
Macintosh abstractions.

The Amiga path is:

```text
ADF/HUNK -> shared m68k -> amiga machine/services/chipset
```

`src/arch/m68k` is the one shared Motorola 68000 implementation. The Macintosh
backend must extend it rather than create a second interpreter. Amiga
ADF/HUNK loading, Exec/DOS services, OCS/CIA/Paula devices, and Intuition
objects remain Amiga-only.

## Macintosh boundary

```text
Mac container/resource fork
        |
        v
formats/mac_*              immutable parsed facts
        |
        v
platform/mac68k
  CODE/A5 loader
  low-memory state
  Memory Manager
  Resource/Segment Managers
  Event Manager
  QuickDraw and Toolbox managers
  trap registry and diagnostics
  canonical state/snapshot/replay
        |
        v
ui::Surface + neutral host events
        |
        v
Qt backend
```

Toolbox pointers, handles, windows, menus, controls, regions, and graphics
ports remain guest-visible Macintosh objects. Qt only presents the resulting
logical windows and software pixels.

Native host widgets are semantic projections, not replacement guest state.
`WindowDesc::surface_insets` hides raster strips that are occupied by native
chrome without deleting those pixels. `WindowDesc::menu_bar` and
`native_scrollbars` carry live, backend-neutral menu/control descriptions;
`native_size_grip` identifies the guest grow-box rectangle. The Qt backend
projects `QMenuBar`/`QScrollBar`/`QSizeGrip` children, translates input back to
full-width semantic identities, and leaves QuickDraw surfaces canonical. It
clips those replacement rectangles from host raster painting so translucent
Qt styles cannot expose old guest-drawn chrome underneath.

Macintosh UI input then passes through the deterministic platform boundary:

```text
QAction/QScrollBar/QSizeGrip
        |
        v
ui::InputEvent (full semantic ID)
        |
        v
typed mac68k replay channel transaction
        |
        v
LiveReplaySession at mac.event.poll:before
        |
        v
Event/Control/Window Manager guest semantics
```

The viewer never delivers `HostInput` directly. It retains host intent until
`LiveReplaySession::queue_live_input` owns the encoded transaction. Ordinary
event-loop input becomes visible at the next supported before seam. If the
guest is already between polls, the session anchors the transaction to the
preceding stamp and records its exact deterministic `mac.tick` coordinate;
the Event Manager then exposes due mouse/key hardware state to modal
`Button`, `StillDown`, `GetKeys`, and `GetMouse` loops.

The driver-owned instruction step is the sole scheduler composition:
vertical-retrace prepare, sound-callback prepare, M68K execution, sound/VBL
completion, then Event Manager time admission. Qt pumping and presentation are
observational. Direct, record, and playback modes do not have separate loops
or cursors.

Seeking either side of an Event Manager poll is cooperatively partitioned at
20,000 guest instructions. Each incomplete partition returns to the outer Qt
timer for presentation and realtime pacing, so simulation work between polls
cannot monopolize the host event loop. Because Macintosh has no stable
instruction coordinate, sub-poll intent uses the shared emulated `mac.tick`
domain. In particular, mouse-up cannot be postponed to a poll that a modal
button tracker needs that same release in order to reach.

F11 replaces the live-session mode at a returned semantic safe seam. A
recording binds an exact restorable base directory into its environment
identity. F12 only sets a deferred host request while nested Qt events are
serviced; after any continuation-safe cooperative slice returns, the runner
captures the live envelope (including a pending semantic target when present)
and exact machine attachment without intervening guest execution and proves
their three state blobs are byte-identical before publication.

The Mac continuation contract is `pf-continuation-mac68k-v4`. Its
restorable-state v3 binary has no extra replay cursor: the platform's one
input-delivery cursor is `Machine::event_cursor`, while ReplaySession boundary,
event, checkpoint, recording-draft, and playback positions remain solely in
the live-session envelope. Diagnostic manifests expose the platform value as
`machine_event_cursor`.

Menu selection is event-causal: a completed native choice is metadata on its
synthetic `mouseDown`, `EventAvail` cannot expose it, and consuming the event
arms one `MenuSelect`. Standard scrollbar hit testing and `FindControl` remain
guest Control Manager behavior. Completed native scrollbar gestures use the
same one-shot event metadata: NIL-action `TrackControl` returns the classic
CDEF part and commits only a completed thumb position. Custom callbacks await
a general guest-callback continuation mechanism.

Completed native frame growth is also event-causal. The requested size remains
private during `EventAvail`, a consuming event arms one grow result,
`FindWindow` reports the targeted grow box, and `GrowWindow` consumes and
clamps it. The application remains responsible for calling `SizeWindow` and
laying out controls; the host runner never mutates guest size directly.

Native geometry feedback is accepted only for presenter-owned guest
WindowRecords. Moving the desktop shell remains a host operation. Visible
guest moves translate global Window Manager regions, rebuild the local
visibility region, and leave each independently retained QuickDraw raster
intact. Once guest code accepts a completed grow, visible guest resizes
preserve overlapping pixels while repacking rowBytes, synchronize the guest
BitMap/PixMap and WindowRecord geometry, and rebuild standard WDEF regions and
update damage. Qt callbacks never propagate runtime exceptions; the backend
defers the first failure to the runner's guarded execution slice.

## Shared-core invariants

1. `m68k::Interpreter` exposes a platform-neutral A-line callback; Toolbox
   trap policy remains in `platform/mac68k`.
2. Code origin is preserved independently of runtime address as
   `mac.code.<resource-id>.<offset>`.
3. Snapshot eligibility is an explicit continuation barrier: between
   guest instructions, outside host-held guest callback frames and unfinished
   drawing transactions.
4. Neutral host key/text/mouse input is translated in the Mac Event Manager;
   the runtime does not reuse Windows VK/message values as Macintosh key
   codes.
5. Future generated Macintosh instructions must be guarded by every original
   instruction byte, including extension words, and must use precise
   interpreter steps near replay or snapshot stops. No generated Mac execution
   is claimed today.

## Original module plan and current status

```text
port_forge/src/formats/
  mac_resource_fork.hpp

port_forge/src/platform/mac68k/
  profile.hpp
  machine.hpp
  loader.hpp
  low_memory.hpp
  trap_registry.hpp
  memory_manager.hpp
  resource_manager.hpp
  segment_loader.hpp
  event_manager.hpp
  quickdraw.hpp
  executor.hpp
  replay.hpp
  canonical.hpp
  snapshot.hpp
  native.hpp     (source-guarded registry present; parity/promotion planned)
```

The first implementation slice was deliberately narrower: validated resource
fork and `CODE` parsing, A5/jump-table bootstrap, serializable handles,
fail-loud A-line dispatch, deterministic EventRecords, clipped monochrome
QuickDraw surfaces, and synthetic tests.

Requirement discovery now has two complementary inputs:

1. recursive static CODE decoding from the main entry and all nonzero MPW
   jump-table exports, including direct inter-segment A5 transfers and direct
   A-line trap sites;
2. deterministic replay/runtime coverage for indirect transfers, executable
   resources, patched traps, and actual game-state reachability.

Static output is a conservative implementation frontier, not a claim that
every discovered slot executes in the recorded game path.

Raw diagnostic snapshots remain comparison artifacts, while authenticated
restorable machine snapshots and content-bound LiveReplaySession publications
now provide continuation. Stable CODE identities and native-candidate evidence
also exist, but the Macintosh exact-byte-guarded function hook/parity layer
remains planned. Those distinctions are deliberate: the replay oracle must be
faithful before replacement code becomes authoritative.

The shared 68000 static decoder treats Line-A as a CPU exception and reports
generic `d16(An)` control-transfer operands. Classic Macintosh fall-through,
auto-pop, and A5/MPW meanings are applied only by the Mac static analyzer.

## Macintosh-to-native progression

```text
original SimAnt CODE
        |
        v
stable CODE identity + interpreter evidence
        |
        v
exact-byte-guarded native hook + entry/return parity
        |
        v
game-owned platform-neutral state/function
        |
        v
standalone native runtime with no Mac/68k dependency
```

Macintosh-facing functions remain thin compatibility adapters. Trap-free
functions with measured execution coverage are only candidates until indirect
calls, global reads/writes, ABI, and return effects are captured. The game
repository owns replacement selection and parity evidence; PortForge owns the
generic hook, fallback, observation, and manager boundaries.
