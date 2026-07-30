#!/usr/bin/env python3
"""Prove that a Macintosh checkpoint resumes identically to a direct run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAY = PROJECT_ROOT / "scripts" / "play.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "artifacts" / "analysis" / "snapshot_resume_12m.json"
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
            "Checkpoint a deterministic SimAnt replay, resume it, and "
            "require exact equality with uninterrupted execution."
        )
    )
    result.add_argument(
        "--replay", default="resize_probe_20260730.pfmacreplay.json"
    )
    result.add_argument(
        "--checkpoint-instructions", type=int, default=10_000_000
    )
    result.add_argument(
        "--continuation-instructions", type=int, default=2_000_000
    )
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument(
        "--build",
        action="store_true",
        help="build the Qt runner before the checkpoint run",
    )
    return result


def run(
    replay: str,
    instruction_limit: int,
    snapshot: Path,
    *,
    resume: Path | None = None,
    build: bool = False,
) -> None:
    command = [
        sys.executable,
        str(PLAY),
        "--play-replay",
        replay,
        "--instruction-limit",
        str(instruction_limit),
        "--quit-on-stop",
        "--unthrottled",
        "--snapshot-on-crash",
        str(snapshot),
    ]
    if not build:
        command.insert(2, "--no-build")
    if resume is not None:
        command.extend(["--resume", str(resume)])
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode != 3:
        raise RuntimeError(
            f"runner did not reach checkpoint {instruction_limit} "
            f"(exit {completed.returncode})"
        )


def authenticated_hashes(snapshot: Path) -> tuple[dict, dict[str, str]]:
    manifest_path = snapshot / "snapshot.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != (
        "portforge-mac68k-restorable-snapshot-v1"
    ):
        raise RuntimeError(
            f"snapshot is not restorable: {manifest.get('format')}"
        )
    hashes = {"manifest": sha256(manifest_path)}
    for region in ("memory", "executed", "state"):
        path = snapshot / manifest[f"{region}_file"]
        digest = sha256(path)
        if digest != manifest[f"{region}_sha256"]:
            raise RuntimeError(
                f"{snapshot.name}: {region} authentication failed"
            )
        hashes[region] = digest
    return manifest, hashes


def main() -> int:
    args = parser().parse_args()
    if (
        args.checkpoint_instructions <= 0
        or args.continuation_instructions <= 0
    ):
        raise RuntimeError("instruction counts must be positive")
    total = (
        args.checkpoint_instructions + args.continuation_instructions
    )
    root = (
        PROJECT_ROOT
        / "artifacts"
        / "snapshots"
        / f"resume_equivalence_{total}"
    )
    checkpoint = root / "checkpoint.pfmacsnapshot"
    resumed = root / "resumed.pfmacsnapshot"
    direct = root / "direct.pfmacsnapshot"

    run(
        args.replay,
        args.checkpoint_instructions,
        checkpoint,
        build=args.build,
    )
    run(
        args.replay,
        args.continuation_instructions,
        resumed,
        resume=checkpoint,
    )
    run(args.replay, total, direct)

    checkpoint_manifest, checkpoint_hashes = authenticated_hashes(
        checkpoint
    )
    resumed_manifest, resumed_hashes = authenticated_hashes(resumed)
    direct_manifest, direct_hashes = authenticated_hashes(direct)
    if resumed_hashes != direct_hashes:
        raise RuntimeError(
            "resumed execution diverged from direct execution: "
            + json.dumps(
                {"resumed": resumed_hashes, "direct": direct_hashes},
                sort_keys=True,
            )
        )

    evidence = {
        "format": "simant-macintosh-snapshot-resume-evidence-v1",
        "replay": args.replay,
        "checkpoint_instructions": args.checkpoint_instructions,
        "continuation_instructions": args.continuation_instructions,
        "total_instructions": total,
        "checkpoint_replay_cursor": checkpoint_manifest[
            "replay_cursor"
        ],
        "final_replay_cursor": resumed_manifest["replay_cursor"],
        "pc": resumed_manifest["cpu"]["pc"],
        "timeline_ticks": resumed_manifest["runtime"]["timeline_ticks"],
        "hashes": resumed_hashes,
        "checkpoint_hashes": checkpoint_hashes,
        "snapshots": {
            "checkpoint": str(checkpoint.relative_to(PROJECT_ROOT)),
            "resumed": str(resumed.relative_to(PROJECT_ROOT)),
            "direct": str(direct.relative_to(PROJECT_ROOT)),
        },
    }
    output = args.output
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"resume-equivalent: {resumed_hashes['manifest']}")
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
        print(f"verify_snapshot_resume.py: {error}", file=sys.stderr)
        raise SystemExit(1)
