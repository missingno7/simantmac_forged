#!/usr/bin/env python3
"""Prove exact real Macintosh machine-state continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "scripts" / "play.py"
DEFAULT_OUTPUT = ROOT / "recovery" / "snapshot-conformance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    instruction_limit: int,
    snapshot: Path,
    *,
    resume: Path | None = None,
    build: bool = False,
) -> None:
    command = [sys.executable, str(PLAY)]
    if not build:
        command.append("--no-build")
    command.extend(
        [
            "--instruction-limit",
            str(instruction_limit),
            "--quit-on-stop",
            "--unthrottled",
            "--snapshot-on-crash",
            str(snapshot),
        ]
    )
    if resume is not None:
        command.extend(["--resume-snapshot", str(resume)])
    command.extend(["--", "--no-host-input"])
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 3:
        raise RuntimeError(
            f"runner did not reach the {instruction_limit}-instruction "
            f"interval (exit {completed.returncode})"
        )


def authenticated_snapshot(snapshot: Path) -> tuple[dict[str, Any], dict[str, str]]:
    manifest_path = snapshot / "snapshot.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "portforge-mac68k-restorable-snapshot-v1":
        raise RuntimeError(f"snapshot is not restorable: {snapshot}")
    hashes: dict[str, str] = {}
    for region in ("memory", "executed", "state"):
        digest = sha256(snapshot / manifest[f"{region}_file"])
        if digest != manifest[f"{region}_sha256"]:
            raise RuntimeError(f"{snapshot.name}: {region} authentication failed")
        hashes[region] = digest
    return manifest, hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-instructions", type=int, default=2_000_000)
    parser.add_argument("--continuation-instructions", type=int, default=500_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build", action="store_true")
    options = parser.parse_args()
    if options.checkpoint_instructions <= 0 or options.continuation_instructions <= 0:
        raise RuntimeError("instruction intervals must be positive")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = ROOT / "artifacts/snapshots" / f"resume-equivalence-{stamp}"
    checkpoint = run_root / "checkpoint.pfmacsnapshot"
    resumed = run_root / "resumed.pfmacsnapshot"
    direct = run_root / "direct.pfmacsnapshot"
    run(
        options.checkpoint_instructions,
        checkpoint,
        build=options.build,
    )
    run(
        options.continuation_instructions,
        resumed,
        resume=checkpoint,
    )
    run(
        options.checkpoint_instructions + options.continuation_instructions,
        direct,
    )

    checkpoint_manifest, checkpoint_hashes = authenticated_snapshot(checkpoint)
    resumed_manifest, resumed_hashes = authenticated_snapshot(resumed)
    direct_manifest, direct_hashes = authenticated_snapshot(direct)
    if resumed_hashes != direct_hashes:
        raise RuntimeError(
            "resumed execution diverged from direct execution: "
            + json.dumps(
                {"resumed": resumed_hashes, "direct": direct_hashes},
                sort_keys=True,
            )
        )

    evidence = {
        "format": "simant-mac-snapshot-conformance-v2",
        "result": "passed",
        "claim": "machine-exact",
        "scope": "real cold-start oracle; byte-identical authenticated final continuation state",
        "checkpoint_instructions": options.checkpoint_instructions,
        "continuation_instructions": options.continuation_instructions,
        "total_instructions": (
            options.checkpoint_instructions + options.continuation_instructions
        ),
        "checkpoint": {
            "pc": checkpoint_manifest["cpu"]["pc"],
            "timeline_ticks": checkpoint_manifest["runtime"]["timeline_ticks"],
            "hashes": checkpoint_hashes,
        },
        "final": {
            "pc": resumed_manifest["cpu"]["pc"],
            "timeline_ticks": resumed_manifest["runtime"]["timeline_ticks"],
            "hashes": resumed_hashes,
            "direct_hashes": direct_hashes,
            "replay_cursor": resumed_manifest["replay_cursor"],
        },
        "authenticated_regions": ["memory", "executed", "state"],
        "state_contract": {
            "includes_deterministic_audio_source": True,
            "includes_deterministic_video_source": True,
            "host_audio_queue_authoritative": False,
            "host_window_or_gpu_state_authoritative": False,
        },
        "artifact_capabilities_proven": ["machine-exact"],
        "artifact_capabilities_not_claimed": [
            "replay-session-exact",
            "audio-continuing",
            "video-continuing",
        ],
        "snapshots": {
            "checkpoint": checkpoint.relative_to(ROOT).as_posix(),
            "resumed": resumed.relative_to(ROOT).as_posix(),
            "direct": direct.relative_to(ROOT).as_posix(),
        },
    }
    output = options.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"machine-exact resume: {resumed_hashes['state']}")
    print(f"evidence: {output.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"verify_snapshot_resume.py: {error}", file=sys.stderr)
        raise SystemExit(1)
