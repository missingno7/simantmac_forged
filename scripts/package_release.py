#!/usr/bin/env python3
"""Build the SimAnt Macintosh generated-with-fallback Windows bundle."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from play import build_generated_qt, port_forge_default
from verify_release import verify_archive


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
PACKAGE_NAME = f"SimAntMac-{VERSION}-windows-x64"
DIST = ROOT / "dist"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_stage(path: Path, dist: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != dist.resolve():
        raise RuntimeError(f"refusing to replace unexpected path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def deploy_qt(
    qmake: Path, runner: Path, stage: Path, environment: dict[str, str]
) -> None:
    deployer = qmake.parent / "windeployqt.exe"
    if not deployer.is_file():
        raise RuntimeError(f"Qt deployment tool was not found: {deployer}")
    target = stage / "SimAntMacRuntime.exe"
    shutil.copy2(runner, target)
    command = [
        str(deployer), "--release", "--compiler-runtime",
        "--skip-plugin-types",
        "generic,iconengines,imageformats,networkinformation,styles,tls",
        "--no-translations", "--no-system-d3d-compiler",
        "--no-system-dxc-compiler", "--no-opengl-sw", "--no-ffmpeg",
        str(target),
    ]
    print("$", subprocess.list2cmdline(command))
    subprocess.run(command, cwd=stage, env=environment, check=True)


def build_launcher(compiler: Path, stage: Path, environment: dict[str, str]) -> None:
    source = ROOT / "native" / "simant_mac_launcher.cpp"
    target = stage / "SimAntMac.exe"
    command = [
        str(compiler), "-std=c++17", "-O2", "-s", "-municode", "-mwindows",
        "-static-libgcc", "-static-libstdc++", "-Wl,--no-insert-timestamp",
        str(source), "-o", str(target),
        "-lshell32", "-luser32",
    ]
    print("$", subprocess.list2cmdline(command))
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def make_zip(stage: Path, dist: Path) -> Path:
    archive = dist / f"{PACKAGE_NAME}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as output:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                relative = Path(PACKAGE_NAME) / path.relative_to(stage)
                info = zipfile.ZipInfo(
                    relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                output.writestr(info, path.read_bytes(), compresslevel=9)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port-forge", type=Path, default=port_forge_default())
    parser.add_argument(
        "--dist", type=Path, default=DIST,
        help="output directory (defaults to the project dist directory)",
    )
    parser.add_argument("--no-build", action="store_true")
    options = parser.parse_args()
    port_forge = options.port_forge.resolve()
    dist = options.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(port_forge / "scripts"))
    import qt_build_util

    qmake, make, environment = qt_build_util.resolve_toolchain()
    runner = ROOT / "build-simant_mac_generated" / "pf_mac_qt_generated.exe"
    if not options.no_build:
        runner, environment = build_generated_qt(qt_build_util, quiet=False)
    elif not runner.is_file():
        raise RuntimeError(f"--no-build requested but {runner} is absent")

    stage = dist / PACKAGE_NAME
    reset_stage(stage, dist)
    deploy_qt(qmake, runner, stage, environment)
    build_launcher(make.parent / "g++.exe", stage, environment)
    archive = make_zip(stage, dist)
    digest = sha256(archive)
    checksum = dist / f"{archive.name}.sha256"
    checksum.write_text(
        f"{digest}  {archive.name}\n", encoding="ascii", newline="\n"
    )
    verified = verify_archive(archive, checksum)
    print(
        f"Generated Mac bundle: {archive}\n"
        f"Verified {verified['files']} files; SHA-256: {digest}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"package_release.py: {error}", file=sys.stderr)
        raise SystemExit(1)
