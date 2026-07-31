#!/usr/bin/env python3
"""Build and run the classic Macintosh SimAnt Qt host.

The player records deterministic guest input and asks the runner to preserve
a restorable snapshot whenever guest execution stops on a diagnostic failure.
F11 flushes the replay while the game is running; F12 writes a manual
restorable snapshot.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT_FORGE = PROJECT_ROOT / "port_forge"
sys.path.insert(0, str(PORT_FORGE / "scripts"))
import qt_build_util


DEFAULT_ISO = PROJECT_ROOT / "assets" / "SimAnt_CD.iso"
REPLAY_SUFFIX = ".pfmacreplay.json"
SNAPSHOT_SUFFIX = ".pfmacsnapshot"


def stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def output_path(
    value: str, folder: Path, suffix: str, run_stamp: str
) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or len(candidate.parts) > 1:
        path = (
            candidate
            if candidate.is_absolute()
            else PROJECT_ROOT / candidate
        )
        return path.resolve()
    name = candidate.name
    if not name.endswith(suffix):
        name = f"{name}_{run_stamp}{suffix}"
    return (folder / name).resolve()


def replay_input(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate
    elif len(candidate.parts) > 1:
        path = PROJECT_ROOT / candidate
    else:
        direct = PROJECT_ROOT / "artifacts" / "replays" / candidate
        if direct.is_file():
            path = direct
        else:
            name = candidate.name
            if not name.endswith(REPLAY_SUFFIX):
                name += REPLAY_SUFFIX
            exact = PROJECT_ROOT / "artifacts" / "replays" / name
            if exact.is_file():
                path = exact
            else:
                prefix = candidate.name.removesuffix(REPLAY_SUFFIX)
                matches = sorted(
                    (PROJECT_ROOT / "artifacts" / "replays").glob(
                        f"{prefix}_*{REPLAY_SUFFIX}"
                    )
                )
                if not matches:
                    raise RuntimeError(f"replay not found: {value}")
                path = matches[-1]
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"replay not found: {path}")
    return path


def snapshot_input(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate
    elif len(candidate.parts) > 1:
        path = PROJECT_ROOT / candidate
    else:
        direct = PROJECT_ROOT / "artifacts" / "snapshots" / candidate
        if direct.is_dir():
            path = direct
        else:
            name = candidate.name
            if not name.endswith(SNAPSHOT_SUFFIX):
                name += SNAPSHOT_SUFFIX
            exact = PROJECT_ROOT / "artifacts" / "snapshots" / name
            if exact.is_dir():
                path = exact
            else:
                prefix = candidate.name.removesuffix(SNAPSHOT_SUFFIX)
                matches = sorted(
                    item
                    for item in (
                        PROJECT_ROOT / "artifacts" / "snapshots"
                    ).glob(f"{prefix}_*{SNAPSHOT_SUFFIX}")
                    if item.is_dir()
                )
                if not matches:
                    raise RuntimeError(f"snapshot not found: {value}")
                path = matches[-1]
    path = path.resolve()
    if not path.is_dir() or not (path / "snapshot.json").is_file():
        raise RuntimeError(f"snapshot not found: {path}")
    return path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the real Macintosh SimAnt ISO through PortForge/Qt."
    )
    result.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    result.add_argument(
        "--no-build",
        action="store_true",
        help="launch the existing build-pf_mac_qt/pf_mac_qt.exe",
    )
    result.add_argument(
        "--verbose-build",
        action="store_true",
        help="show qmake/compiler output",
    )
    result.add_argument(
        "--record-replay",
        nargs="?",
        const="session",
        metavar="NAME",
        help="record input from power-on; F11 flushes it immediately",
    )
    result.add_argument(
        "--play-replay",
        metavar="PATH_OR_NAME",
        help="play an earlier deterministic Macintosh input journal",
    )
    result.add_argument(
        "--resume",
        "--resume-snapshot",
        dest="resume_snapshot",
        metavar="PATH_OR_NAME",
        help="continue a restorable Macintosh snapshot",
    )
    result.add_argument(
        "--snapshot-on-crash",
        nargs="?",
        const="crash",
        default="crash",
        metavar="NAME",
        help="write a restorable Macintosh checkpoint on a guest stop",
    )
    result.add_argument(
        "--no-snapshot-on-crash",
        action="store_true",
        help="disable the automatic crash snapshot",
    )
    result.add_argument(
        "--instruction-limit",
        type=int,
        help="optional guest instruction limit",
    )
    result.add_argument(
        "--quit-on-stop",
        action="store_true",
        help="close Qt automatically after a guest stop",
    )
    result.add_argument(
        "--unthrottled",
        action="store_true",
        help="run interactive guest execution as fast as the host permits",
    )
    result.add_argument(
        "--scale",
        type=int,
        metavar="INTEGER",
        help=(
            "exact positive integer Qt display scale (for example 1, 2, "
            "or 3); omit to use the monitor DPI-derived scale"
        ),
    )
    result.add_argument(
        "--auto-click-splash",
        action="store_true",
        help="click the center of the first visible guest window",
    )
    result.add_argument(
        "runner_args",
        nargs=argparse.REMAINDER,
        help="extra arguments passed to pf_mac_qt after '--'",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    iso = args.iso.resolve()
    if not iso.is_file():
        raise RuntimeError(f"SimAnt ISO not found: {iso}")
    if args.record_replay and args.play_replay:
        raise RuntimeError(
            "--record-replay and --play-replay are mutually exclusive"
        )
    if args.instruction_limit is not None and args.instruction_limit <= 0:
        raise RuntimeError("--instruction-limit must be positive")
    if args.scale is not None and args.scale <= 0:
        raise RuntimeError("--scale must be a positive integer")
    if args.resume_snapshot and args.auto_click_splash:
        raise RuntimeError(
            "--auto-click-splash cannot be added to a resumed state"
        )

    if args.no_build:
        executable = (
            PORT_FORGE / "build-pf_mac_qt" / "pf_mac_qt.exe"
        )
        _, _, environment = qt_build_util.resolve_toolchain()
        if not executable.is_file():
            raise RuntimeError(
                f"Qt runner is not built: {executable}; omit --no-build"
            )
    else:
        executable, environment = qt_build_util.build(
            PORT_FORGE,
            "pf_mac_qt.pro",
            "pf_mac_qt.exe",
            quiet=not args.verbose_build,
        )

    run_stamp = stamp()
    command = [str(executable), str(iso), "--creator", "SANT"]
    if args.instruction_limit is not None:
        command.append(str(args.instruction_limit))

    replay_path: Path | None = None
    if args.record_replay:
        replay_path = output_path(
            args.record_replay,
            PROJECT_ROOT / "artifacts" / "replays",
            REPLAY_SUFFIX,
            run_stamp,
        )
        command.extend(["--record-replay", str(replay_path)])
    elif args.play_replay:
        replay_path = replay_input(args.play_replay)
        command.extend(["--play-replay", str(replay_path)])

    resume_path: Path | None = None
    if args.resume_snapshot:
        resume_path = snapshot_input(args.resume_snapshot)
        command.extend(["--resume-snapshot", str(resume_path)])

    snapshot_path: Path | None = None
    if not args.no_snapshot_on_crash and args.snapshot_on_crash:
        snapshot_path = output_path(
            args.snapshot_on_crash,
            PROJECT_ROOT / "artifacts" / "snapshots",
            SNAPSHOT_SUFFIX,
            run_stamp,
        )
        command.extend(["--snapshot-on-stop", str(snapshot_path)])
    manual_snapshot_path = output_path(
        "snapshot",
        PROJECT_ROOT / "artifacts" / "snapshots",
        SNAPSHOT_SUFFIX,
        run_stamp,
    )
    command.extend(["--manual-snapshot", str(manual_snapshot_path)])
    if args.quit_on_stop:
        command.append("--quit-on-stop")
    if args.unthrottled:
        command.append("--unthrottled")
    if args.scale is not None:
        command.extend(["--scale", str(args.scale)])
    if args.auto_click_splash:
        command.extend(["--auto-click", "320", "240"])
    runner_args = args.runner_args
    if runner_args[:1] == ["--"]:
        runner_args = runner_args[1:]
    command.extend(runner_args)

    print(f"runner: {executable}", flush=True)
    print(f"image:  {iso}", flush=True)
    if args.scale is not None:
        print(f"display scale: {args.scale}x (explicit)", flush=True)
    if replay_path:
        label = "recording" if args.record_replay else "replaying"
        print(f"{label}: {replay_path}", flush=True)
    if resume_path:
        print(f"resuming: {resume_path}", flush=True)
    if snapshot_path:
        print(f"failure snapshot target: {snapshot_path}", flush=True)
    print(f"F12 snapshot target: {manual_snapshot_path}", flush=True)
    print(
        "controls: left-click the splash; F11 saves replay; "
        "F12 writes the manual snapshot",
        flush=True,
    )
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, env=environment, check=False
    )
    return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"play.py: {error}", file=sys.stderr)
        raise SystemExit(1)
