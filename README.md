# SimAnt Macintosh PortForge project

This project owns the classic Macintosh SimAnt assets, launcher, replays,
snapshots, and game-specific evidence. The `port_forge` submodule contains the
reusable 68k Macintosh runtime, Toolbox compatibility layer, and Qt host.

Run from this project root:

```powershell
python scripts\play.py
python scripts\play.py --record-replay session
python scripts\play.py --record-replay session --auto-click-splash
python scripts\play.py --play-replay session
python scripts\play.py --play-replay session_20260729_230725 `
    --resume artifacts\snapshots\determinism_30000000\run_a.pfmacsnapshot
python scripts\play.py --unthrottled
python scripts\analyze.py
python scripts\lift.py
python scripts\verify_replay.py
python scripts\verify_snapshot_resume.py
```

The launcher builds `port_forge\pf_mac_qt.pro` and runs the original image at
`assets\SimAnt_CD.iso`. Replays are written to `artifacts\replays`; authenticated
restorable snapshots are written to `artifacts\snapshots` and are enabled by
default. Automatic diagnostic stops use `crash_<timestamp>.pfmacsnapshot`;
F12 checkpoints use `snapshot_<timestamp>.pfmacsnapshot`, so a normal manual
capture is no longer mislabeled as a crash. Press F11 to flush a recording or
F12 to take a manual checkpoint.
Resume by full path or artifact name with `--resume`; when replay playback is
also selected, its journal hash and saved cursor must match the checkpoint.
Interactive execution is paced against the Macintosh Event Manager's 60 Hz
timeline. Replay playback stays unthrottled for rapid deterministic
regression runs; `--unthrottled` provides the same opt-out for a live run.

`scripts\analyze.py` builds the reusable PortForge Macintosh static analyzer
and writes `artifacts\analysis\mac_trap_frontier.json`. The SimAnt launcher
owns the ISO/creator defaults and artifact path; the CODE decoder, MPW
jump-table lifting, trap catalog, and implementation comparison remain
game-neutral code inside `port_forge`.

`scripts\lift.py` generates
`artifacts\analysis\mac_static_lift_plan.json`: source-authenticated decoded
instructions, stable CODE identities, control-flow targets, MPW edges, and
explicit frontiers. Supplying `--snapshot` overlays executed bytes and dynamic
trap calls to rank native candidates without putting SimAnt policy into
PortForge.

`scripts\verify_replay.py` runs the canonical journal twice to the same exact
instruction stop and compares the restorable manifest, guest RAM,
executed-byte bitmap, and persistent manager state byte-for-byte. It writes
the current evidence to `artifacts\analysis\determinism_30m.json`.
`scripts\verify_snapshot_resume.py` separately proves that a 10M checkpoint
continued for 2M instructions is identical to an uninterrupted 12M run.

The recording made before the launcher was moved is preserved as:

`artifacts\snapshots\crash_20260729_230725.pfmacsnapshot`

Its matching journal is:

`artifacts\replays\session_20260729_230725.pfmacreplay.json`

Replay it with:

```powershell
python scripts\play.py --play-replay session_20260729_230725
```

The journal now passes the original `BeginUpdate` crash and the later color
`CopyBits` (`A8EC`), masked `BitsRgn` picture, rounded-window-region,
control-redraw, and text-rendering paths. It also crosses the observed
`Pack7` number conversion, window selection, pen-state, `FrameOval`,
`FrameRect`, local-coordinate `GetMouse`, indexed-color `EraseRect`,
`StripAddress`, and tagged VBL-queue paths.

The current recording runs continuously with seven guest windows. The latest
capped verification reached 600,000,000 guest instructions without an
unsupported trap or runtime error:

```powershell
python scripts\play.py --play-replay session_20260729_230725 `
    --instruction-limit 600000000 --quit-on-stop
```

Its diagnostic snapshot is:

`artifacts\snapshots\auto_after_vbl_pointer_20260730_094953.pfmacsnapshot`

A later unrecorded interactive run reached `FindWindow` (`A92C`) on its fifth
delivered input event. PortForge now performs generic standard-WDEF hit
testing for the menu bar, content, drag, grow, close, and zoom-in parts. The
captured click at global point `(313, 304)` resolves to the active front
window's grow box. Because that run was not recorded, replaying beyond this
specific click requires a new journal.

Two subsequent snapshots reached QuickDraw `PtInRgn` (`A8E8`) and Menu
Manager `MenuSelect` (`A93D`). Both now have generic implementations:
`PtInRgn` handles compact and complex regions, while `MenuSelect` safely
resolves an already-dropped enabled item and treats a menu-title-only click
as a cancelled modal selection. The saved replay was reverified through
70,000,000 instructions after these changes with seven guest windows and no
unsupported trap.

The later `GrowWindow` (`A92B`) snapshot is now handled generically with
classic packed-Point size/bounds semantics. The same saved journal was
reverified through 100,000,000 instructions after the native Qt projection
changes, ending with seven guest windows and no unsupported trap.

## Native Macintosh UI projection

QuickDraw remains authoritative. Menu-bar and standard-scrollbar pixels stay
in guest surfaces for `CopyBits`, readback, headless tests, snapshots, and
replay determinism. At the Qt presentation boundary:

- the guest menu strip is clipped with a generic surface inset and projected
  from live `MBAR`/`MENU` records into a real `QMenuBar`;
- standard CDEF-1 controls are projected at their exact guest rectangles into
  real child `QScrollBar` widgets;
- standard grow boxes are projected as real `QSizeGrip` widgets on resizable
  WDEF families;
- native-control rectangles are removed from the Qt raster paint region, so a
  translucent idle host style cannot reveal classic CDEF/WDEF pixels
  underneath; the canonical QuickDraw surface itself remains unchanged;
- full 32-bit Macintosh menu results and ControlHandles cross the neutral UI
  contract without token remapping;
- Qt menu actions re-enter the classic Event Manager as a completed
  `mouseDown`; only a consuming `GetNextEvent`/`WaitNextEvent` arms the
  one-shot `MenuSelect` result, so `EventAvail` remains a true peek;
- completed Qt scrollbar gestures follow the same event-causal path:
  `TrackControl` consumes a full-width ControlHandle/action/position exactly
  once, arrow/page gestures return their classic CDEF part, and a completed
  thumb gesture commits its clamped guest value;
- completed Qt frame resizes are attached to a synthetic consumed
  `mouseDown`; `FindWindow` reports the matching grow box and `GrowWindow`
  returns the one-shot clamped host size. SimAnt then calls `SizeWindow` and
  repositions its own controls through its normal Macintosh code;
- guest window visibility, title, order, document/dialog frame family,
  resizing, movement, and control state are re-read on every presenter slice.

Visible `MoveWindow` now translates simple or shaped structure/content/update
regions, rebuilds the local visibility region, and updates the QuickDraw
coordinate map without copying retained pixels through the desktop. Moving the
desktop Qt shell is host-only and cannot be mistaken for a guest `WindowPtr`.
Visible `SizeWindow` preserves and repacks overlapping monochrome or indexed
pixels when `rowBytes` changes, updates the guest BitMap/PixMap and WindowRecord,
rebuilds standard WDEF regions, and marks only newly exposed content for update.
Qt input exceptions are retained and rethrown at the runner's guarded execution
boundary, where replay/snapshot diagnostics work, rather than crossing an event
handler.

The reported resize crash also reached the standard `HiWord`/`LoWord`
Utilities used to unpack `GrowWindow`'s result. Both traps now implement their
classic stack ABI. A deterministic probe replay requests a 400x320 resize of
the proc-8 game window:

```powershell
python scripts\play.py --play-replay resize_probe_20260730 `
    --instruction-limit 60000000 --quit-on-stop
```

It reaches the intentional instruction cap with seven guest windows. The
application's two scrollbar records move from the old 320x272 layout to the
new 400x320 port edges, proving the guest resize handler—not a direct runner
mutation—performed the layout.

Hosted presentation also revalidates each retained QuickDraw port against its
authoritative guest `WindowRecord`, `portRect`, PixMap storage, and clip region
before projection. This closes the intermittent case where the native frame
accepted a resize while retained surface geometry still described the previous
dimensions. New snapshots record guest, retained bitmap, and surface geometry
for every window.

Color QuickDraw transparent transfers use the current RGB background color as
the source transparency key. SimAnt's ant-wheel source uses white behind the
yellow ants, so the wheel now overlays yellow ants without copying its white
background.

`TrackControl` (`A968`) with a NIL `actionProc` is implemented for completed
native standard-scrollbar gestures. A custom `actionProc` remains an explicit
boundary because it requires a re-entrant guest callback/modal continuation
bridge; PortForge does not silently replace that callback with direct
scrollbar-value mutation.

## Static requirement frontier

The current SimAnt report recursively decodes 123,172 of 182,266 CODE bytes
(67.58%) from 359 entry seeds, resolves 1,595 MPW A5 jump-table transfers, and
proves 1,587 direct A-line sites across 219 canonical trap slots. After the
current implementations, 45 reachable slots remain fail-loud. The report also
correlates loaded CODE ranges, executed bytes, and cumulative trap coverage to
rank candidate functions for native parity experiments.

This is a much better implementation backlog than waiting for one crash at a
time, but it is intentionally not called whole-program proof. The JSON keeps
unresolved computed transfers and aligned-but-unconfirmed candidates separate.
Indirect function pointers, indexed switch tables, trap-vector patching,
selector multiplexers, generated/decompressed code, and executable
`MDEF`/`CDEF`/`WDEF`/`DRVR` resources still require dynamic trace/replay
evidence.

The full current audit, reference comparison, ordered blockers, native
candidate map, deterministic hashes, and Macintosh-to-native detachment plan
are in [docs/macintosh-runtime-audit.md](docs/macintosh-runtime-audit.md).
