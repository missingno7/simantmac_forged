#!/usr/bin/env python3
"""Verify a packaged SimAnt Macintosh generated-with-fallback bundle."""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
PACKAGE_NAME = f"SimAntMac-{VERSION}-windows-x64"
DEFAULT_ARCHIVE = ROOT / "dist" / f"{PACKAGE_NAME}.zip"
ORIGINAL_NAME = "SimAnt_CD.iso"
REQUIRED_RUNTIME_FILES = (
    "SimAntMac.exe",
    "SimAntMacRuntime.exe",
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Widgets.dll",
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
    "libwinpthread-1.dll",
    "platforms/qwindows.dll",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member(name: str) -> PurePosixPath:
    if "\\" in name:
        raise RuntimeError(f"archive member uses a backslash: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"archive member escapes its package: {name!r}")
    if not path.parts or path.parts[0] != PACKAGE_NAME:
        raise RuntimeError(f"archive member is outside {PACKAGE_NAME}: {name!r}")
    return path


def verify_archive(
    archive: Path,
    checksum: Path | None = None,
    asset_root: Path | None = None,
) -> dict[str, object]:
    archive = archive.resolve()
    checksum = (
        checksum.resolve() if checksum is not None
        else archive.with_name(archive.name + ".sha256")
    )
    if not archive.is_file() or not checksum.is_file():
        raise RuntimeError("release archive or checksum sidecar is missing")
    archive_digest = sha256_file(archive)
    fields = checksum.read_text(encoding="ascii").strip().split()
    if fields != [archive_digest, archive.name]:
        raise RuntimeError("release checksum sidecar does not match the archive")

    with zipfile.ZipFile(archive) as package:
        infos = [info for info in package.infolist() if not info.is_dir()]
        if len(infos) != len({info.filename for info in infos}):
            raise RuntimeError("release archive contains duplicate members")
        relative: dict[str, bytes] = {}
        for info in infos:
            member = safe_member(info.filename)
            if len(member.parts) < 2:
                raise RuntimeError("release archive contains a root file")
            relative[PurePosixPath(*member.parts[1:]).as_posix()] = (
                package.read(info)
            )

    missing = sorted(set(REQUIRED_RUNTIME_FILES) - relative.keys())
    if missing:
        raise RuntimeError("release is missing: " + ", ".join(missing))
    unexpected = sorted(set(relative) - set(REQUIRED_RUNTIME_FILES))
    if unexpected:
        raise RuntimeError("release contains unexpected files: " + ", ".join(unexpected))
    if any(
        PurePosixPath(name).name.casefold() == ORIGINAL_NAME.casefold()
        or PurePosixPath(name).suffix.casefold() in {".iso", ".py", ".pyc"}
        for name in relative
    ):
        raise RuntimeError("release contains original media or development files")

    root = asset_root or ROOT / "assets"
    original = root / ORIGINAL_NAME
    if original.is_file():
        payload = original.read_bytes()
        embedded = [name for name, data in relative.items() if payload in data]
        if embedded:
            raise RuntimeError(
                "release embeds the exact original ISO payload: " +
                ", ".join(embedded)
            )
    return {
        "package": PACKAGE_NAME,
        "archive": str(archive),
        "sha256": archive_digest,
        "files": len(relative),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--checksum", type=Path)
    parser.add_argument("--asset-root", type=Path)
    options = parser.parse_args()
    result = verify_archive(options.archive, options.checksum, options.asset_root)
    print(
        f"verified {result['package']}: {result['files']} files, "
        f"SHA-256 {result['sha256']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"verify_release.py: {error}", file=sys.stderr)
        raise SystemExit(1)
