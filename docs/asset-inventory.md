# SimAnt Macintosh Asset Inventory

This report inventories the original files in `assets/` and the classic
Macintosh application stored inside them. The inspection was read-only. No
asset was rewritten, normalized, or extracted back into the repository.

Unless a statement is explicitly marked **Inference**, it is derived directly
from bytes or metadata in the supplied files. Source timestamps are recorded as
metadata, not treated as proof of provenance.

## Supplied files

| Path | Bytes | SHA-256 | MD5 |
| --- | ---: | --- | --- |
| `assets/SimAnt_CD.iso` | 14,663,680 | `8E7518796DBF32DB9FF483DCC49069D4D8EC6E4625918FE4D47B03DE8CC5FB0B` | `B57FE43330D2E281C35C8A366405E3F8` |
| `assets/SimAnt_CD.sit` | 5,918,128 | `429A2EF1482E2EE03E303DA681F1FB415EB096AC383869B89227903FD1531288` | `D784BB884D2BF95B0C93C25A67898FA4` |

`SimAnt_CD.sit` contains one member, `SimAnt_CD.iso`. Expanding it produces a
byte-identical copy of the supplied ISO.

## Container chain

### StuffIt archive

The SIT header identifies a StuffIt generation-5 archive with one entry and no
encryption or password flag. Its entry uses compression method 15
(`Arsenic` in StuffIt 5 terminology):

- member: `SimAnt_CD.iso`
- uncompressed size: 14,663,680 bytes
- compressed payload: 5,917,935 bytes
- payload offset: byte 193
- packed size: 40.358% of the original
- archive flags: `0`

The archive banner names Aladdin Systems and carries a 1997-2001 StuffIt
copyright. That banner dates the archiver, not the game or disc release.

### Hybrid CD image

The ISO is a Toast-authored hybrid disc. It contains two independent views:

- ISO 9660 volume `SIMANT`: the Windows edition and installer
- Apple Partition Map plus HFS volume `SimAnt`: the classic Macintosh edition

Important ISO metadata:

- system identifier: `APPLE COMPUTER, INC., TYPE: 0002`
- application identifier:
  `TOAST ISO 9660 BUILDER COPYRIGHT (C) 1993-1996 MILES SOFTWARE GMBH - HAVE A NICE DAY`
- ISO creation timestamp: 1997-10-13 17:52:49, offset field zero
- ISO modification timestamp: 1997-10-13 17:53:22, offset field zero
- ISO 9660 declared extent: 3,934 sectors of 2,048 bytes, or 8,056,832 bytes
- ISO 9660 tree: 81 files, 4 directories, 7,898,622 logical file bytes

The Apple Driver Descriptor uses 512-byte blocks. Its partition map is:

| Map entry | Start block | Blocks | Name | Type |
| --- | ---: | ---: | --- | --- |
| 1 | 1 | 2 | `MRKS` | `Apple_partition_map` |
| 2 | 15,739 | 12,291 | `Toast 3.0.1 Partition` | `Apple_HFS` |

Therefore the HFS partition starts at byte 8,058,368 and is 6,292,992 bytes
long. Its SHA-256 is
`9646D9017E3F44836316DC907C34C738A09F1E0D32AEC0D6126252943D3D3112`.
The Driver Descriptor ends at byte 14,351,360; the remaining 312,320 bytes of
the image are zero padding.

The HFS boot blocks are all zero and the volume contains no System Folder. This
is an application disc, not a bootable Macintosh system image.

## HFS volume and files

The HFS volume is named `SimAnt`. Its nominal classic-HFS timestamps are:

- created: 1997-10-13 17:49:33
- modified: 1997-10-13 17:52:54

Classic HFS timestamps have local-time semantics. The volume has 3,071
allocation blocks of 2,048 bytes, no free blocks, and the clean-unmounted
attribute (`0x0100`). Its catalog contains ten files and one child directory.
All file forks occupy single contiguous extents; the extents-overflow tree has
no records.

| HFS path | Type / creator | Finder flags | Data fork | Resource fork | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `SimAnt:Desktop DB` | `BTFL` / `DMGR` | `0x4000` | 8,192 | 0 | Finder desktop metadata |
| `SimAnt:Desktop DF` | `DTFL` / `DMGR` | `0x4000` | 45,314 | 0 | Finder desktop metadata |
| `SimAnt:E-Doc 1.0.20` | `APPL` / `MABM` | `0x2100` | 254,152 | 401,915 | Manual viewer |
| `SimAnt:E-Doc Readme` | `ttro` / `ttxt` | `0x0100` | 1,264 | 452 | Viewer documentation |
| `SimAnt:Help File` | `ttro` / `ttxt` | `0x0100` | 4,689 | 58,564 | Viewer help |
| `SimAnt:Icon\r` | `icon` / `MACS` | `0x4000` | 0 | 2,670 | Hidden volume icon |
| `SimAnt:Register SimAnt` | `APPL` / `ercR` | `0x2100` | 0 | 143,724 | Registration utility |
| `SimAnt:SimAnt:SimAnt™` | `APPL` / `SANT` | `0x2100` | 0 | 1,188,458 | Macintosh game |
| `SimAnt:SimAnt:Tutorial.Ant` | `SAGM` / `SANT` | `0x0100` | 2,048 | 0 | Macintosh tutorial game |
| `SimAnt:SimAnt User's Manual` | `dMAB` / `MABM` | `0x0500` | 3,975,315 | 3,590 | Electronic manual |

The manual's hardware-requirements section describes the bundled Windows
edition. Its 286/386, DOS, and Windows 3.0 requirements must not be attributed
to the Macintosh executable.

## Macintosh application identity

The game application is HFS CNID 23 at `SimAnt:SimAnt:SimAnt™`:

- Finder type: `APPL`
- Finder creator: `SANT`
- Finder flags: `0x2100` (bundle and initialized bits)
- nominal creation and modification timestamp: 1991-10-10 06:00:00
- data fork: empty
- resource fork: 1,188,458 bytes
- resource-fork SHA-256:
  `3E73EF63500BED0C666DB56A25B5A5951C09D9A266C8C682F373B2825050F351`

The application is unusable if its resource fork or Finder metadata is
discarded.

The `vers` resources provide the exact executable identity:

- IDs 1 and 2: BCD version 1.0, final stage `0x80`, prerelease byte `0`
- ID 1 long string:
  `1.0, Copyright © 1991 Maxis Inc.\r       All Rights Reserved.`
- ID 2 long string: `Another Maxis Software Toy`
- owner resource: `SimAnt™ 1.0 - © 1991 Maxis Inc.`

**Fact:** the contained Macintosh executable is SimAnt 1.0 final, copyright
1991.

**Inference:** the 1997 timestamps and mixed Windows/Macintosh contents identify
the carrier as a later hybrid-CD mastering. External catalog descriptions call
similar media a Sim Classics release, but the supplied disc does not state
`Sim Classics`; that retail label should not be treated as established.

## Target Macintosh profile

Disc-internal facts:

- executable code is stored only in classic `CODE` resources
- there is no `cfrg` or other PowerPC fragment metadata
- a `NO64KROM` dialog says:
  `The 64K ROM System is not supported by this version of SimAnt™.`
- `SIZE` ID -1 is `58800015e0000015e000`
- preferred and minimum application partitions are both 1,433,600 bytes
  (1,400 KiB)
- `SIZE` flags `0x5880` request suspend/resume events, allow background
  execution, make the application activate its own windows, and declare
  32-bit-addressing compatibility
- the application is not high-level-event-aware
- required font names stored in `STR#` 2100 are Chicago, Geneva, and Monaco

**Inference:** use a 68000-family classic Macintosh baseline with 128 KiB or
newer ROM behavior. Mac Plus/SE/II-generation System 6 or System 7 Toolbox
semantics are the narrowest credible starting profile. The exact minimum System
version is not encoded in the inspected resources.

### Color behavior

The application has one 16-entry `clut` resource named `Sixteen Colors`, eleven
color cursors, 4-bit and 8-bit icons, and monochrome cursors and icons. Its
dialogs say that SimAnt Color runs substantially faster in 16-color mode and
offer to change the monitor setting. The bundled manual also describes
black-and-white-monitor behavior.

**Inference:** this is one color-capable executable with a monochrome fallback,
not two separate supplied binaries. A first graphics implementation should
support 4-bit indexed color and 1-bit fallback. Higher indexed depths are useful
for icon compatibility but are not the preferred gameplay mode.

## Resource fork

The main resource fork has:

- resource data offset: 256
- resource map offset: 1,168,721
- resource data length: 1,168,465
- resource map length: 19,737
- resource types: 38
- resource records: 835

### Resource census

Payload totals exclude the four-byte length prefix used in the resource data
area.

| Type | Count | Payload bytes | Type | Count | Payload bytes |
| --- | ---: | ---: | --- | ---: | ---: |
| `BNDL` | 1 | 36 | `CARD` | 53 | 5,414 |
| `clut` | 1 | 136 | `CNTL` | 2 | 46 |
| `CODE` | 13 | 185,250 | `crsr` | 11 | 3,606 |
| `CURS` | 5 | 340 | `DATA` | 1 | 5,630 |
| `DITL` | 16 | 3,016 | `DLOG` | 16 | 336 |
| `DREL` | 1 | 94 | `FREF` | 2 | 14 |
| `icl4` | 2 | 1,024 | `icl8` | 2 | 2,048 |
| `ICN#` | 2 | 512 | `ics#` | 2 | 128 |
| `ics4` | 2 | 256 | `ics8` | 2 | 512 |
| `INST` | 14 | 380 | `MBAR` | 1 | 14 |
| `mctb` | 1 | 182 | `MDRV` | 1 | 10,084 |
| `MENU` | 6 | 511 | `MIDI` | 30 | 34,035 |
| `PICT` | 244 | 479,401 | `SANT` | 1 | 32 |
| `SIZE` | 1 | 10 | `snd ` | 49 | 325,173 |
| `SONG` | 33 | 594 | `STR ` | 5 | 86 |
| `STR#` | 115 | 15,459 | `styl` | 89 | 5,558 |
| `TEXT` | 89 | 29,942 | `TILE` | 5 | 54,215 |
| `vers` | 2 | 108 | `WIND` | 10 | 277 |
| `ZERO` | 1 | 202 | `ZHEX` | 4 | 464 |

Notable IDs:

- `MENU`: 300-305 (Apple, File, Window, View, Options, Speed)
- `WIND`: 1000-1006, 2000, 2500, 2510
- `DLOG` and matching `DITL`: 1100-1102, 1200, 1300, 12000, 12001,
  12003, 12005-12012
- `CURS`: 1001-1005
- `BNDL`: 128
- `FREF`: 128 and 129
- `PICT`: 244 records
- `STR#`: 115 records
- `snd `: 10000-10003, 10300-10308, and 12000-12350 in steps of 10

The initial display assets are directly identifiable:

- `WIND` 2000, `Splash Wind`: bounds `(20, 0)-(340, 510)`
- `PICT` 2000, `Splash Screen Pict`: 510 x 320, 32,298 bytes
- `WIND` 2500 and `PICT` 2500: 320 x 256 scenario screen

### Finder bundle mapping

`BNDL` 128 has signature `SANT`, version 0, and maps:

- local `FREF` 0 to resource 128; local `FREF` 1 to resource 129
- local `ICN#` 0 to resource 128; local `ICN#` 1 to resource 129

`FREF` 128 describes `APPL` with local icon 0. `FREF` 129 describes
`SAGM` with local icon 1. Macintosh game documents therefore use Finder type
`SAGM`, creator `SANT`.

## CODE resources and jump table

`CODE` 0 is 2,936 bytes with SHA-256
`D6AC71166C6447D...F83852CA8697D9`; the unabbreviated value appears below. Its
header declares:

- globals above A5: 2,952 bytes
- globals below A5: 18,326 bytes
- jump table: 2,920 bytes
- jump-table location: A5 + `0x20`
- jump-table entries: 365, each eight bytes

Every on-disc jump-table entry has the form:

```text
target offset : uint16
0x3F3C        : move.w immediate,-(sp)
segment ID    : uint16
0xA9F0        : _LoadSeg
```

Entry zero targets `CODE` 1 offset 4. There are 358 nonzero entry targets and
seven zero placeholders at global jump-table indices 94, 124, 151, 225, 255,
292, and 341. Every nonzero target is even and within its segment resource. The
four-byte header of each segment exactly covers a contiguous range of the
global jump table.

| `CODE` | Bytes | JT byte / index | Entries | Zero entries | Nonzero target range | SHA-256 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 2,936 | A5 + 32 | 365 | 7 | n/a | `D6AC71166C6447DD50AB82A948A210DDF8BE505764A72C3397F83852CA8697D9` |
| 1 | 558 | 0 / 0 | 10 | 0 | 4-552 | `3197DFC0A09445FDBF59400502FFFFE185FB274EC6AA8A3F7C5BAFBE083D0291` |
| 2 | 13,304 | 80 / 10 | 85 | 1 | 502-10,952 | `3D1A9830253D409A78BB1E9ED230377FB93B7FF902F0693316D150B5D696BDFC` |
| 3 | 7,346 | 760 / 95 | 6 | 0 | 44-6,534 | `28513FE426B53594D2E2A8ED877530EAD72B77BB8C2CDA089FDCFC1F3B184C77` |
| 4 | 5,178 | 808 / 101 | 30 | 1 | 28-5,048 | `AE464E6484885562D5D5A140F7C3571FB95E3B99700D9AD7FFCE1B4A25F66718` |
| 5 | 25,056 | 1,048 / 131 | 28 | 1 | 8,272-24,592 | `F7B46796D3F57174FDCCA3D983A447E47599B0183502EEE8A6F4BB84BF515917` |
| 6 | 9,538 | 1,272 / 159 | 16 | 0 | 826-9,044 | `1F08ADF42031406C8C57C3AEFAADFACC14C8D658236E03058C01E06F119BF022` |
| 7 | 22,322 | 1,400 / 175 | 53 | 1 | 482-20,022 | `9A12B3E21B962B5660DBAF2BF4EB6487E2D279DCBA220F169FFF153451EA1B96` |
| 8 | 18,604 | 1,824 / 228 | 15 | 0 | 8,842-17,812 | `D3BA54D04E7B4F7E5C0468FD2FB1FB5850212FD2D0AB6094562C87E32DF0354E` |
| 9 | 26,080 | 1,944 / 243 | 20 | 1 | 600-23,562 | `8C0C8A6B351B75FDDA2EE3FD111D2A30783F49E2CD49DB62069CAF92FC0ACD83` |
| 10 | 25,974 | 2,104 / 263 | 32 | 1 | 1,478-25,244 | `C89C81F052C82787221AAE3745FE897A8986688444BC005FFE46E085C6201A13` |
| 11 | 13,048 | 2,360 / 295 | 58 | 1 | 308-12,998 | `2CF5B15841EC848A8EC2DFAB047A8B192B7311BE674ECEB911E97F0CFBD44324` |
| 12 | 15,306 | 2,824 / 353 | 12 | 0 | 404-7,994 | `8DDC8A30684A6A67889EB5F70CB7F699C71A121DC96977F3F2995C890783365A` |

The A5-world initialization resources are not empty:

| Resource | Bytes | SHA-256 |
| --- | ---: | --- |
| `DATA` 0 | 5,630 | `E2B59778923FDA7521F83B462E71F531E38A4B4D616F179A834F2A874AD3AEEB` |
| `ZERO` 0 | 202 | `841A056B3DDCFE5358689C930688356CCEE11CD573A111CDE73B157B79F2FF5A` |
| `DREL` 0 | 94 | `0044A1AEF0ED93A96E998E94E60D68743D3B6ABAC05A7F760D167496B4EF0D06` |

A loader must preserve and implement their initialization semantics rather than
assuming the entire A5 world begins as zero-filled memory.

## External companions and system resources

`SimAnt:SimAnt:Tutorial.Ant` is the only game-content companion on the HFS
volume:

- Finder type / creator: `SAGM` / `SANT`
- data fork: 2,048 bytes
- resource fork: empty
- SHA-256:
  `69A964E49A06355D984C1FA09787070C3EB8E5784736C0F7C55AACE97BE10383`
- data begins with `SAGM` and contains `Tutorial.Ant` and
  `Copyright 1991 Maxis Inc.`

The ISO 9660 tree also contains `SIMANT\TUTORIAL.ANT`, but that is a 298-byte
Windows-format file. It is not interchangeable with the Macintosh document.

Saved games use `SAGM` / `SANT`, so the runtime needs a writable virtual
directory or overlay even though the source HFS volume is read-only and full.
The supplied tutorial should appear in the application's default directory.

Chicago, Geneva, and Monaco must be available through the Font Manager.
Gameplay sound and music are otherwise self-contained:

- 49 `snd ` resources
- 30 `MIDI` resources
- 33 `SONG` resources
- embedded `MDRV` 12, `22k Note and MIDI driver/8`, 10,084 bytes

The registration utility, E-Doc viewer, help, manual, volume icon, and Desktop
files are ancillary and are not required to start the game.

## Loader implications

1. Verify the ISO SHA-256 before loading. Retain the SIT only as an immutable
   provenance wrapper or as a fallback source from which the verified ISO can
   be reproduced.
2. Parse the Apple Partition Map and HFS partition. Do not use only the ISO
   9660 view, which exposes the Windows build.
3. Preserve MacRoman names, data and resource forks, Finder type/creator, and
   Finder flags. Locate the game as `APPL` / `SANT`; its data fork is empty.
4. Construct the A5 world from `CODE` 0 and the `DATA`, `ZERO`, and `DREL`
   resources. Install the jump table at A5 + `0x20`; begin at `CODE` 1 offset
   4. Preserve code identity as `mac.code.<resource-id>.<offset>`.
5. Implement `_LoadSeg` behavior for `CODE` 1-12, or eagerly load segments
   while retaining equivalent jump-table and segment identity semantics.
6. Dispatch 68K A-line Toolbox and OS traps. Initial manager boundaries should
   include Memory, Resource, Segment Loader, Event, QuickDraw, Window, Menu,
   Dialog, Control, Text, Font, File, and Sound.
7. Provide faithful 1-bit and 4-bit indexed QuickDraw surfaces, PICT decoding,
   `CopyBits`, clipping, palette behavior, and cursor support before mapping
   results to Qt.
8. Mount the original HFS content read-only and route saved games to a
   deterministic writable overlay.

Because the disc is non-bootable and contains no System Folder, the evidence
supports direct application loading with a narrow classic Macintosh runtime.
It does not support booting or emulating a complete System installation.
