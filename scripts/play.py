#!/usr/bin/env python3
"""One launcher for SimAnt Macintosh play, ArtifactV2, and snapshots.

The Qt window is presentation only. Direct play, recording, playback, and
session resume all run through PortForge's Mac EventPollReplayDriver and
LiveReplaySession authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ISO = PROJECT_ROOT / "assets" / "SimAnt_CD.iso"
REPLAY_DIR = PROJECT_ROOT / "artifacts" / "replays"
SNAPSHOT_DIR = PROJECT_ROOT / "artifacts" / "snapshots"
EVIDENCE_DIR = PROJECT_ROOT / "artifacts" / "evidence"
REPLAY_SUFFIX = ".pfreplay.json"
SESSION_SUFFIX = ".pfsession.json"
RAW_SNAPSHOT_SUFFIX = ".pfmacsnapshot"


def port_forge_default() -> Path:
    configured = os.environ.get("PORT_FORGE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    pinned = PROJECT_ROOT / "port_forge"
    if (pinned / "pf_mac_qt.pro").is_file():
        return pinned.resolve()
    return (PROJECT_ROOT.parent / "port_forge").resolve()


def stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def named_output(value: str, folder: Path, suffix: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or len(candidate.parts) > 1:
        path = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
    else:
        name = candidate.name
        if not name.endswith(suffix):
            name += suffix
        path = folder / name
    return path.resolve()


def generated_output(folder: Path, stem: str, suffix: str) -> Path:
    return (folder / f"{stem}_{stamp()}{suffix}").resolve()


def _latest_named(value: str, folder: Path, suffix: str, *, directory: bool) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate
    elif len(candidate.parts) > 1:
        path = PROJECT_ROOT / candidate
    else:
        direct = folder / candidate
        if direct.exists():
            path = direct
        else:
            name = candidate.name
            if not name.endswith(suffix):
                name += suffix
            exact = folder / name
            if exact.exists():
                path = exact
            else:
                prefix = candidate.name.removesuffix(suffix)
                matches = sorted(folder.glob(f"{prefix}_*{suffix}"))
                matches = [
                    item
                    for item in matches
                    if (item.is_dir() if directory else item.is_file())
                ]
                if not matches:
                    raise RuntimeError(f"artifact not found: {value}")
                path = matches[-1]
    path = path.resolve()
    valid = path.is_dir() if directory else path.is_file()
    if not valid:
        raise RuntimeError(f"artifact not found: {path}")
    return path


def replay_input(value: str) -> Path:
    return _latest_named(value, REPLAY_DIR, REPLAY_SUFFIX, directory=False)


def session_input(value: str) -> Path:
    return _latest_named(value, SNAPSHOT_DIR, SESSION_SUFFIX, directory=False)


def snapshot_input(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate
    elif len(candidate.parts) > 1:
        path = PROJECT_ROOT / candidate
    else:
        direct = SNAPSHOT_DIR / candidate
        if direct.exists():
            path = direct
        else:
            for suffix in (SESSION_SUFFIX, RAW_SNAPSHOT_SUFFIX):
                exact = SNAPSHOT_DIR / (candidate.name + suffix)
                if exact.exists():
                    path = exact
                    break
            else:
                prefix = candidate.name
                matches = sorted(
                    list(SNAPSHOT_DIR.glob(f"{prefix}_*{SESSION_SUFFIX}"))
                    + list(SNAPSHOT_DIR.glob(
                        f"{prefix}_*{RAW_SNAPSHOT_SUFFIX}"
                    ))
                )
                if not matches:
                    raise RuntimeError(f"snapshot not found: {value}")
                path = matches[-1]
    path = path.resolve()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "pf-replay-session-snapshot-publication-v1":
            raise RuntimeError(f"snapshot publication has an unknown schema: {path}")
        return path
    if path.is_dir() and (path / "snapshot.json").is_file():
        return path
    raise RuntimeError(f"snapshot not found: {path}")


def session_publication_mode(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "pf-replay-session-snapshot-publication-v1":
        raise RuntimeError(f"snapshot publication has an unknown schema: {path}")
    mode = data.get("live_session", {}).get("mode")
    if mode not in {"interactive", "record", "playback"}:
        raise RuntimeError(f"snapshot publication has an unknown mode: {path}")
    return mode


def replay_asset_manifest() -> str:
    entries: list[dict[str, object]] = []
    for relative in (
        Path("game.json"),
        Path("assets/README.md"),
        Path("docs/asset-inventory.md"),
    ):
        path = PROJECT_ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        entries.append({
            "path": relative.as_posix(),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    encoded = json.dumps(
        entries, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Run SimAnt Macintosh through one semantic LiveReplaySession "
            "runtime. Plain invocation selects the oracle interpreter."
        ),
        epilog=(
            "Interactive controls: F11 starts/stops ArtifactV2 recording; "
            "F12 publishes an exact resumable session snapshot. Raw crash "
            "snapshots are diagnostic compatibility only. Use '--' before "
            "advanced pf_mac_qt arguments."
        ),
    )
    operation = result.add_mutually_exclusive_group()
    operation.add_argument(
        "--record-replay", "--record-artifact",
        dest="record_replay", nargs="?", const="", metavar="NAME",
        help=(
            "start recording ArtifactV2 immediately; without this option "
            "F11 can start recording mid-game"
        ),
    )
    operation.add_argument(
        "--play-replay", "--play-artifact",
        dest="play_replay", metavar="PATH_OR_NAME",
        help="play and verify an immutable Macintosh ArtifactV2",
    )
    operation.add_argument(
        "--verify-replay", metavar="PATH_OR_NAME",
        help=(
            "run deterministic playback to terminal and publish "
            "ReplayEvidenceV3"
        ),
    )
    operation.add_argument(
        "--inspect-replay", metavar="PATH_OR_NAME",
        help="authenticate and inspect ArtifactV2 without launching the game",
    )
    operation.add_argument(
        "--inspect-session", metavar="PATH_OR_NAME",
        help="authenticate and inspect a session snapshot publication",
    )
    operation.add_argument(
        "--verify-session", metavar="PATH_OR_NAME",
        help="verify a session publication and every bound attachment",
    )
    result.add_argument(
        "--snapshot", "--resume-snapshot", dest="resume_snapshot",
        metavar="PATH_OR_NAME",
        help=(
            "resume a LiveReplaySession publication, or explicitly resume "
            "a raw diagnostic machine snapshot"
        ),
    )
    result.add_argument(
        "--session-snapshot", "--snapshot-out",
        dest="session_snapshot", metavar="PATH_OR_NAME",
        help="F12 publication path (default: artifacts/snapshots/session_*)",
    )
    result.add_argument(
        "--snapshot-after-polls", type=int, metavar="N",
        help="publish the same F12 session snapshot after N completed polls",
    )
    result.add_argument(
        "--exit-after-snapshot", action="store_true",
        help="close after --snapshot-after-polls publishes successfully",
    )
    result.add_argument(
        "--runtime", choices=("oracle", "generated"), default="oracle",
        help=(
            "execution stage: oracle interpreter or source-guarded generated "
            "blocks with explicit interpreter fallback"
        ),
    )
    result.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    result.add_argument("--port-forge", type=Path, default=port_forge_default())
    result.add_argument(
        "--no-build", action="store_true",
        help="never build; fail if the selected shared tool is unavailable",
    )
    result.add_argument(
        "--dry-run", action="store_true",
        help="report the exact selected adapter/command without building",
    )
    result.add_argument(
        "--verbose-build", action="store_true", help="show Qt compiler output"
    )
    result.add_argument(
        "--headless", action="store_true",
        help="use Qt's offscreen sink for bounded deterministic testing",
    )
    result.add_argument(
        "--live-atlas", action="store_true",
        help="request Live Atlas (currently an explicit Mac capability blocker)",
    )
    result.add_argument(
        "--atlas-interval", type=int, default=1, metavar="N",
        help="publish Live Atlas every N semantic polls when supported",
    )
    result.add_argument(
        "--replay-boundary-limit", type=int, metavar="N",
        help=(
            "stop a new or resumed recording after N completed semantic "
            "event polls"
        ),
    )
    result.add_argument(
        "--evidence-out", metavar="PATH_OR_NAME",
        help="ReplayEvidenceV3 output path for complete playback",
    )
    result.add_argument(
        "--exit-after-replay", action="store_true",
        help=(
            "close after new or resumed record/play reaches its semantic "
            "terminal"
        ),
    )
    result.add_argument(
        "--snapshot-on-crash", nargs="?", const="", default="",
        metavar="NAME",
        help="raw diagnostic snapshot on stop (default target when enabled)",
    )
    result.add_argument(
        "--no-snapshot-on-crash", action="store_true",
        help="disable raw diagnostic crash snapshots",
    )
    result.add_argument(
        "--instruction-limit", type=int,
        help="diagnostic-only exact guest instruction stop",
    )
    result.add_argument("--quit-on-stop", action="store_true")
    result.add_argument("--unthrottled", action="store_true")
    result.add_argument("--no-host-input", action="store_true")
    result.add_argument("--scale", type=int, metavar="INTEGER")
    result.add_argument(
        "--auto-click-splash", action="store_true",
        help="queue a semantic click when the first guest window appears",
    )
    result.add_argument("runner_args", nargs=argparse.REMAINDER)
    return result


def artifact_tool(port_forge: Path, *, no_build: bool, dry_run: bool) -> Path:
    executable = port_forge / "build" / "pf_artifact.exe"
    if dry_run:
        return executable
    if no_build:
        if not executable.is_file():
            raise RuntimeError(f"shared artifact tool is not built: {executable}")
        return executable
    subprocess.run(
        [
            sys.executable,
            str(port_forge / "build.py"),
            "--targets", "pf_artifact", "--no-tests",
        ],
        cwd=port_forge,
        check=True,
    )
    if not executable.is_file():
        raise RuntimeError(f"build produced no shared artifact tool: {executable}")
    return executable


def run_inspection(args: argparse.Namespace, port_forge: Path) -> int | None:
    command_name: str | None = None
    path: Path | None = None
    if args.inspect_replay:
        command_name, path = "inspect", replay_input(args.inspect_replay)
    elif args.inspect_session:
        command_name, path = "inspect-session", session_input(args.inspect_session)
    elif args.verify_session:
        command_name, path = "verify-session", session_input(args.verify_session)
    if not command_name or not path:
        return None
    tool = artifact_tool(
        port_forge, no_build=args.no_build, dry_run=args.dry_run
    )
    command = [str(tool), command_name, str(path)]
    print("$", subprocess.list2cmdline(command), flush=True)
    if args.dry_run:
        return 0
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


def build_generated_qt(qt_build_util, *, quiet: bool) -> tuple[Path, dict[str, str]]:
    project = PROJECT_ROOT / "simant_mac_generated.pro"
    output_dir = PROJECT_ROOT / "build-simant_mac_generated"
    executable = output_dir / "pf_mac_qt_generated.exe"
    qmake, make, environment = qt_build_util.resolve_toolchain()
    output_dir.mkdir(parents=True, exist_ok=True)
    sink = subprocess.DEVNULL if quiet else None
    subprocess.run(
        [str(qmake), "-o", "Makefile", str(project)],
        cwd=output_dir,
        check=True,
        env=environment,
        stdout=sink,
    )
    subprocess.run(
        [str(make)],
        cwd=output_dir,
        check=True,
        env=environment,
        stdout=sink,
        stderr=sink,
    )
    if not executable.is_file():
        raise RuntimeError(f"generated Qt build produced no {executable}")
    return executable, environment


def main() -> int:
    args = parser().parse_args()
    if args.runner_args and args.runner_args[0] != "--":
        raise RuntimeError(
            "advanced runner arguments must follow the explicit '--' delimiter"
        )
    runner_args = args.runner_args[1:] if args.runner_args else []
    if args.atlas_interval <= 0:
        raise RuntimeError("--atlas-interval must be positive")
    if args.live_atlas:
        raise RuntimeError(
            "Mac Live Atlas is not yet a conformant capability: stable M68K "
            "identity telemetry must first fan out alongside replay evidence; "
            "an address-only or second-observer projection is not exposed"
        )
    if args.atlas_interval != 1 and not args.live_atlas:
        raise RuntimeError("--atlas-interval requires --live-atlas")
    if args.replay_boundary_limit is not None and args.replay_boundary_limit <= 0:
        raise RuntimeError("--replay-boundary-limit must be positive")
    if args.snapshot_after_polls is not None and args.snapshot_after_polls <= 0:
        raise RuntimeError("--snapshot-after-polls must be positive")
    if args.exit_after_snapshot and args.snapshot_after_polls is None:
        raise RuntimeError("--exit-after-snapshot requires --snapshot-after-polls")
    if args.instruction_limit is not None and args.instruction_limit <= 0:
        raise RuntimeError("--instruction-limit must be positive")
    if args.scale is not None and args.scale <= 0:
        raise RuntimeError("--scale must be a positive integer")

    port_forge = args.port_forge.resolve()
    inspection = run_inspection(args, port_forge)
    if inspection is not None:
        return inspection

    verify_mode = args.verify_replay is not None
    play_value = args.verify_replay or args.play_replay
    if args.evidence_out and not play_value:
        raise RuntimeError("--evidence-out requires replay playback")

    iso = args.iso.resolve()
    if not iso.is_file():
        raise RuntimeError(f"SimAnt ISO not found: {iso}")
    resume_path = snapshot_input(args.resume_snapshot) if args.resume_snapshot else None
    resume_mode = session_publication_mode(resume_path)
    if resume_path and play_value:
        raise RuntimeError("replay playback owns its bound base; omit --snapshot")
    if resume_path and resume_path.is_file() and args.record_replay is not None:
        raise RuntimeError(
            "a session publication already owns its mode; resume it directly "
            "instead of requesting a new recording"
        )
    if resume_path and args.auto_click_splash:
        raise RuntimeError("--auto-click-splash cannot alter a resumed session")
    if (
        args.replay_boundary_limit is not None
        and args.record_replay is None
        and resume_mode != "record"
    ):
        raise RuntimeError(
            "--replay-boundary-limit requires --record-replay or a resumed "
            "recording publication"
        )
    if (
        args.exit_after_replay
        and args.record_replay is None
        and not play_value
        and resume_mode not in {"record", "playback"}
    ):
        raise RuntimeError(
            "--exit-after-replay requires record, playback, or a resumed "
            "record/play publication"
        )
    if args.headless:
        bounded = (
            bool(play_value)
            or (
                (args.record_replay is not None or resume_mode == "record")
                and args.replay_boundary_limit is not None
            )
            or resume_mode == "playback"
            or args.snapshot_after_polls is not None
            or args.instruction_limit is not None
        )
        if not bounded:
            raise RuntimeError(
                "--headless requires playback, a recording boundary limit, "
                "a session-snapshot boundary, or an instruction limit"
            )

    sys.path.insert(0, str(port_forge / "scripts"))
    import qt_build_util

    generated_runtime = args.runtime == "generated"
    generated_executable = (
        PROJECT_ROOT / "build-simant_mac_generated" /
        "pf_mac_qt_generated.exe"
    )
    if args.dry_run:
        executable = (
            generated_executable if generated_runtime else
            port_forge / "build-pf_mac_qt" / "pf_mac_qt.exe"
        )
        environment = os.environ.copy()
    elif args.no_build:
        executable = (
            generated_executable if generated_runtime else
            port_forge / "build-pf_mac_qt" / "pf_mac_qt.exe"
        )
        _, _, environment = qt_build_util.resolve_toolchain()
        if not executable.is_file():
            raise RuntimeError(
                f"Qt runner is not built: {executable}; omit --no-build"
            )
    elif generated_runtime:
        executable, environment = build_generated_qt(
            qt_build_util, quiet=not args.verbose_build
        )
    else:
        executable, environment = qt_build_util.build(
            port_forge,
            "pf_mac_qt.pro",
            "pf_mac_qt.exe",
            quiet=not args.verbose_build,
        )
    if args.headless or verify_mode:
        environment["QT_QPA_PLATFORM"] = "offscreen"

    execution_plan = (
        PROJECT_ROOT / "recovery" /
        (
            "execution-plan-generated.json" if generated_runtime else
            "execution-plan-oracle.json"
        )
    ).resolve()
    command = [
        str(executable), str(iso), "--creator", "SANT",
        "--expected-image-sha256",
        "8e7518796dbf32db9ff483dcc49069d4d8ec6e4625918fe4d47b03de8cc5fb0b",
        "--replay-game-id", "simant-mac",
        "--replay-assets-sha256", replay_asset_manifest(),
        "--implementation-plan", str(execution_plan),
        "--artifact-dir", str((PROJECT_ROOT / "artifacts").resolve()),
    ]
    if args.instruction_limit is not None:
        command.append(str(args.instruction_limit))

    replay_path: Path | None = None
    if args.record_replay is not None:
        replay_path = (
            generated_output(REPLAY_DIR, "rec", REPLAY_SUFFIX)
            if args.record_replay == ""
            else named_output(args.record_replay, REPLAY_DIR, REPLAY_SUFFIX)
        )
        command.extend(["--record-artifact", str(replay_path)])
    elif play_value:
        replay_path = replay_input(play_value)
        command.extend(["--play-artifact", str(replay_path)])
    if args.replay_boundary_limit is not None:
        command.extend([
            "--replay-boundary-limit", str(args.replay_boundary_limit)
        ])

    exit_after_replay = args.exit_after_replay or verify_mode or (
        args.headless and (
            args.record_replay is not None
            or bool(play_value)
            or resume_mode in {"record", "playback"}
        )
    )
    if exit_after_replay:
        command.append("--exit-after-replay")
    evidence_path: Path | None = None
    if args.evidence_out or verify_mode:
        evidence_path = (
            named_output(args.evidence_out, EVIDENCE_DIR, ".json")
            if args.evidence_out
            else generated_output(
                EVIDENCE_DIR,
                f"{replay_path.name.removesuffix(REPLAY_SUFFIX)}_evidence",
                ".json",
            )
        )
        command.extend([
            "--evidence-out", str(evidence_path),
            "--canonical-projections",
            str((port_forge / "config" /
                 "canonical-projections-v1.json").resolve()),
        ])
    if resume_path:
        command.extend(["--resume-snapshot", str(resume_path)])

    session_path = (
        named_output(args.session_snapshot, SNAPSHOT_DIR, SESSION_SUFFIX)
        if args.session_snapshot
        else generated_output(SNAPSHOT_DIR, "session", SESSION_SUFFIX)
    )
    command.extend(["--session-snapshot", str(session_path)])
    if args.snapshot_after_polls is not None:
        command.extend([
            "--session-snapshot-boundary",
            str(args.snapshot_after_polls),
        ])
        if args.exit_after_snapshot or args.headless:
            command.append("--exit-after-session-snapshot")
    crash_path: Path | None = None
    if not args.no_snapshot_on_crash:
        crash_path = (
            named_output(
                args.snapshot_on_crash, SNAPSHOT_DIR, RAW_SNAPSHOT_SUFFIX
            )
            if args.snapshot_on_crash
            else generated_output(
                SNAPSHOT_DIR, "crash", RAW_SNAPSHOT_SUFFIX
            )
        )
        command.extend(["--snapshot-on-stop", str(crash_path)])
    if args.quit_on_stop or args.headless or verify_mode:
        command.append("--quit-on-stop")
    if args.unthrottled or verify_mode or args.headless:
        command.append("--unthrottled")
    if args.no_host_input or verify_mode or args.headless:
        command.append("--no-host-input")
    if args.scale is not None:
        command.extend(["--scale", str(args.scale)])
    if args.auto_click_splash:
        command.extend(["--auto-click", "320", "240"])

    owned = {
        "--record-artifact", "--play-artifact", "--resume-snapshot",
        "--session-snapshot", "--manual-snapshot", "--artifact-dir",
        "--replay-game-id", "--replay-assets-sha256",
        "--implementation-plan", "--evidence-out",
        "--canonical-projections", "--replay-boundary-limit",
        "--expected-image-sha256",
        "--session-snapshot-boundary",
        "--exit-after-session-snapshot",
    }
    for value in runner_args:
        option = value.split("=", 1)[0]
        if option in owned:
            raise RuntimeError(
                f"{option} is owned by scripts/play.py and cannot be forwarded"
            )
    command.extend(runner_args)

    print("project: simant-mac", flush=True)
    print(f"runtime: {args.runtime}", flush=True)
    print("adapter: mac68k-event-poll-live-session", flush=True)
    print("execution: interactive semantic-session viewer", flush=True)
    print("canonical outputs: state only; PCM/video publication unsupported", flush=True)
    if replay_path:
        action = "verifying" if verify_mode else (
            "recording" if args.record_replay is not None else "playing"
        )
        print(f"{action}: {replay_path}", flush=True)
    if resume_path:
        print(f"resuming: {resume_path}", flush=True)
    if evidence_path:
        print(f"evidence: {evidence_path}", flush=True)
    print(f"F12 session publication: {session_path}", flush=True)
    if crash_path:
        print(f"diagnostic crash snapshot: {crash_path}", flush=True)
    print(
        "controls: F11 start/stop ArtifactV2 recording; "
        "F12 exact LiveReplaySession snapshot",
        flush=True,
    )
    print("$", subprocess.list2cmdline(command), flush=True)
    if args.dry_run:
        return 0
    return subprocess.run(
        command, cwd=PROJECT_ROOT, env=environment, check=False
    ).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError,
            json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"play.py: {error}", file=sys.stderr)
        raise SystemExit(1)
