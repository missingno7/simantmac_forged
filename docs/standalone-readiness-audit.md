# Standalone and generated-build readiness audit

Status: audited against PortForge `c5d8eb76` on 2026-08-12.

## Verdict

The project is a working, reproducible Mac68k **oracle** integration. It is not
yet a generated executable or a detached native port. Its current Windows
entry point is the PortForge Qt runner, which boots the original HFS
application from `SimAnt_CD.iso` and interprets its CODE resources.

The Win16 `simant_forged` release is the nearest achievable first target, but
that target must be described accurately: it is a packaged
generated-with-interpreter-fallback runtime and still requires the lawful
original `SIMANTW.EXE`. It is not a PortForge-independent replacement. A Mac
equivalent would be a packaged Windows application that consumes the original
SimAnt CD image while generated blocks and the interpreter share one exact
Macintosh machine and service model.

A genuinely detached `SimAntMac.exe` that needs neither the original CODE
resources nor PortForge's interpreter is a separate, substantially larger
milestone.

## Evidence-backed current state

- Oracle boot, deterministic Event Manager time, semantic replay,
  ReplayEvidenceV3, implementation planning, detachment reporting, and offline
  Atlas are conformant.
- Static recovery decodes 123,172 of 182,266 CODE bytes (67.58%), identifies
  40,160 instructions, 359 MPW export spans, and 1,587 direct trap sites across
  219 trap slots.
- The retained dynamic audit reaches 205 export ranges and marks 49 as
  conservative native candidates. Candidate status is triage only; it is not
  a semantic-equivalence proof.
- Forty statically reachable trap slots are still unimplemented. The largest
  groups are File Manager I/O and metadata, Dialog Manager, TextEdit,
  QuickDraw/color-port state, Resource Manager writes, Package Manager, and
  timing/debug services.
- Exact machine snapshot continuation passes for its declared scope. Canonical
  PCM/video publication, complete deadline safety, and a frozen real F12
  session corpus remain partial.
- `portforge.project.json` truthfully declares only `oracle` as supported.
  `generated`, `native-replacement`, and `detached-product` are unsupported.
- PortForge already provides source-authenticated CODE identities, a Mac68k
  lift plan, movable-segment-aware exact-byte native hook guards, and safe
  fallback primitives. The Mac executor does not yet dispatch those hooks and
  no Mac code generator or generated runner exists.

## Milestone A: packaged generated-with-fallback executable

This is the correct analogue of the present Win16 release.

1. Promote the reusable Mac decoder/IR/lifting chain from analysis artifacts
   into declared PortForge capabilities. Every undecoded edge must remain an
   explicit frontier, never guessed control flow.
2. Add a Mac68k generator that emits compilable host blocks from stable
   `mac.code.<resource>.<offset>` identities and exact source hashes.
3. Dispatch `NativeHooks` from the Mac executor. A generated block must enter
   and leave through authenticated CPU/memory state, follow movable CODE
   segments, expose normalized observations, and fall back before effects when
   its guard or coverage fails.
4. Add a generated Mac Qt runner and execution identity. Direct, record,
   playback, snapshot, and generated/oracle handoff must continue to use the
   same `EventPollReplayDriver`, platform services, and semantic session.
5. Declare a `generated-with-fallback` implementation, immutable execution
   plan, and detachment report. Cross-representation replay evidence must prove
   each promoted block against the oracle before it enters the default plan.
6. Add project build and release surfaces comparable to Win16: `CMakeLists`,
   generated source output, launcher, tests, `VERSION`, package script, Qt
   deployment, and release verifier. The package must exclude the ISO and
   proprietary resource forks, locate user-supplied media predictably, verify
   its pinned SHA-256, and give a clear error when it is absent or wrong.
7. Close or explicitly prove unreachable the 40 static trap gaps for every
   packaged scenario. Writable game workflows additionally need fork-aware
   File Manager semantics rather than a read-only CD shortcut.

Acceptance for this milestone is a clean checkout that can build and package
without pre-generated binaries; launches from the packaged directory with a
user-supplied exact ISO; records, replays, saves, resumes, and quits cleanly;
passes oracle/generated canonical-state comparisons; and reports interpreter,
original-media, platform-service, and PortForge-runtime dependencies rather
than claiming detachment.

## Milestone B: detached native product

After Milestone A, detachment requires replacing all remaining original-code
execution and interpreter fallback with proved native implementations. It also
requires a game-owned state model, replacement of every reached Macintosh
service contract, a lawful resource conversion/install strategy, canonical
audio and video streams, and removal of `original-code`, `original-executable`,
`interpreter`, and `portforge-runtime` from the final dependency closure.

Acceptance is not “an EXE was produced.” It is a generated/port execution plan
whose detachment report has no forbidden dependency, plus cross-runtime replay
and native-transition evidence over the supported gameplay corpus. Original
art/audio distribution rights are independent of code detachment, so a
detached engine may still need an external lawful asset-install step.

## Work order

The next bounded engineering slice should be a **single generated Mac block**:
wire `NativeHooks` into `Executor`, generate one trap-free MPW export with exact
guards, and prove oracle/generated state equality plus guarded fallback. That
vertical slice validates the missing execution architecture before expanding
coverage. In parallel with later coverage work, complete canonical PCM/video,
deadline-safety, F12 corpus, and external-emulator differential scenarios so
the oracle remains trustworthy enough to certify replacements.
