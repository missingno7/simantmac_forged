#!/usr/bin/env python3
"""Run a SimAnt Macintosh replay twice and compare exact stop state.

This is intentionally game-project policy. PortForge owns the generic replay,
coverage, and restorable snapshot formats; this script owns the SimAnt replay,
instruction checkpoint, artifact paths, and optional golden digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAY = PROJECT_ROOT / "scripts" / "play.py"
DEFAULT_REPLAY = "session_20260729_230725"
DEFAULT_EXPECTED_MANIFEST_SHA256 = (
    "8f64c2e63d1be5528d3e87da37a8d9c6"
    "4a80dce4b2505f2b2ce7a36fe70e4c02"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "artifacts" / "analysis" / "determinism_30m.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Replay Macintosh SimAnt twice to an exact instruction stop "
            "and require byte-identical restorable state."
        )
    )
    result.add_argument("--replay", default=DEFAULT_REPLAY)
    result.add_argument(
        "--instruction-limit", type=int, default=30_000_000
    )
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument(
        "--expected-manifest-sha256",
        default=DEFAULT_EXPECTED_MANIFEST_SHA256,
        help=(
            "pinned SHA-256 for snapshot.json "
            "(default: canonical 30m checkpoint)"
        ),
    )
    result.add_argument(
        "--build",
        action="store_true",
        help="build the Qt runner before the first replay",
    )
    return result


def run_once(
    replay: str,
    instruction_limit: int,
    snapshot: Path,
    build: bool,
) -> None:
    command = [
        sys.executable,
        str(PLAY),
        "--play-replay",
        replay,
        "--instruction-limit",
        str(instruction_limit),
        "--quit-on-stop",
        "--snapshot-on-crash",
        str(snapshot),
    ]
    if not build:
        command.insert(2, "--no-build")
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    # pf_mac_qt uses status 3 for the requested instruction-budget stop.
    if completed.returncode != 3:
        raise RuntimeError(
            "replay did not reach the requested instruction checkpoint "
            f"(exit {completed.returncode})"
        )


def load_snapshot(snapshot: Path) -> tuple[dict, dict[str, str]]:
    manifest_path = snapshot / "snapshot.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") not in {
        "portforge-mac68k-diagnostic-snapshot-v2",
        "portforge-mac68k-restorable-snapshot-v1",
    }:
        raise RuntimeError(
            f"snapshot has unsupported format: {manifest.get('format')}"
        )
    if manifest.get("reason") != "instruction limit reached":
        raise RuntimeError(
            f"snapshot stopped for an unexpected reason: "
            f"{manifest.get('reason')}"
        )
    hashes = {
        "memory": sha256(snapshot / manifest["memory_file"]),
        "executed": sha256(snapshot / manifest["executed_file"]),
        "manifest": sha256(manifest_path),
    }
    if "state_file" in manifest:
        hashes["state"] = sha256(snapshot / manifest["state_file"])
    if hashes["memory"] != manifest["memory_sha256"]:
        raise RuntimeError("snapshot memory hash does not match its manifest")
    if hashes["executed"] != manifest["executed_sha256"]:
        raise RuntimeError(
            "snapshot execution-coverage hash does not match its manifest"
        )
    if (
        "state" in hashes
        and hashes["state"] != manifest["state_sha256"]
    ):
        raise RuntimeError(
            "snapshot persistent-state hash does not match its manifest"
        )
    return manifest, hashes


def main() -> int:
    args = parser().parse_args()
    if args.instruction_limit <= 0:
        raise RuntimeError("--instruction-limit must be positive")

    output = args.output
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output = output.resolve()
    run_root = (
        PROJECT_ROOT
        / "artifacts"
        / "snapshots"
        / f"determinism_{args.instruction_limit}"
    )
    first = run_root / "run_a.pfmacsnapshot"
    second = run_root / "run_b.pfmacsnapshot"
    run_once(args.replay, args.instruction_limit, first, args.build)
    run_once(args.replay, args.instruction_limit, second, False)

    first_manifest, first_hashes = load_snapshot(first)
    second_manifest, second_hashes = load_snapshot(second)
    if first_hashes != second_hashes:
        raise RuntimeError(
            "replay diverged: " + json.dumps(
                {
                    "first": first_hashes,
                    "second": second_hashes,
                },
                sort_keys=True,
            )
        )
    if (
        args.expected_manifest_sha256
        and first_hashes["manifest"].lower()
        != args.expected_manifest_sha256.lower()
    ):
        raise RuntimeError(
            "replay is internally deterministic but differs from the "
            "expected manifest: "
            f"{first_hashes['manifest']}"
        )

    evidence = {
        "format": "simant-macintosh-determinism-evidence-v1",
        "replay": args.replay,
        "instruction_limit": args.instruction_limit,
        "pc": first_manifest["cpu"]["pc"],
        "timeline_ticks": first_manifest["runtime"]["timeline_ticks"],
        "event_cursor": first_manifest["runtime"]["event_cursor"],
        "guest_windows": len(first_manifest["windows"]),
        "trap_sites": len(first_manifest["trap_coverage"]),
        "resource_queries": len(first_manifest["resource_lookups"]),
        "low_memory_sites": len(first_manifest["low_memory_accesses"]),
        "executed_code_write_sites": len(
            first_manifest["executed_code_writes"]
        ),
        "hashes": first_hashes,
        "snapshots": [
            str(first.relative_to(PROJECT_ROOT)),
            str(second.relative_to(PROJECT_ROOT)),
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"deterministic: {first_hashes['manifest']}")
    print(f"evidence: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        print(f"verify_replay.py: {error}", file=sys.stderr)
        raise SystemExit(1)
