#!/usr/bin/env python3
"""Validate and replay the current semantic Macintosh SimAnt corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "regressions" / "manifest.json"
MANIFEST_FORMAT = "portforge-replay-regressions-v1"
MANIFEST_SCHEMA = (
    "port_forge/schemas/portforge-replay-regressions-v1.schema.json"
)
SECTIONS = (
    "schema_versions",
    "identity",
    "boundary_profile",
    "environment",
    "channels",
    "timeline",
    "events",
    "checkpoints",
    "terminal",
    "capabilities",
)


def digest_json(value: Any) -> str:
    wire = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("$schema") != MANIFEST_SCHEMA:
        raise RuntimeError(f"{path}: expected $schema {MANIFEST_SCHEMA}")
    if manifest.get("format") != MANIFEST_FORMAT:
        raise RuntimeError(f"{path}: expected {MANIFEST_FORMAT}")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RuntimeError(f"{path}: cases must be a non-empty array")
    names: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("name"), str):
            raise RuntimeError(f"{path}: every case needs a name")
        if case["name"] in names:
            raise RuntimeError(f"{path}: duplicate case {case['name']!r}")
        names.add(case["name"])
        if not isinstance(case.get("artifact"), str):
            raise RuntimeError(f"{case['name']}: artifact must be a path")
        if not isinstance(case.get("playback_passes"), int) or case[
            "playback_passes"
        ] < 1:
            raise RuntimeError(f"{case['name']}: playback_passes must be positive")
        if not isinstance(case.get("expect"), dict):
            raise RuntimeError(f"{case['name']}: expect must be an object")
    return manifest


def observation(artifact: dict[str, Any]) -> dict[str, Any]:
    schemas = {item["canonical_schema"] for item in artifact["checkpoints"]}
    terminal = artifact["terminal"]
    terminal_stamp = terminal["stamp"]
    terminal_selector = terminal_stamp["selector"]
    return {
        "format": artifact.get("format"),
        "game_id": artifact["identity"]["game_id"],
        "program_sha256": artifact["identity"]["program_sha256"],
        "machine_model": artifact["identity"]["machine_model"],
        "boundary_profile_id": artifact["boundary_profile"]["id"],
        "boundary_profile_sha256": artifact["boundary_profile"]["sha256"],
        "canonical_schema": next(iter(schemas)) if len(schemas) == 1 else None,
        "timeline_boundaries": len(artifact["timeline"]),
        "events": len(artifact["events"]),
        "checkpoints": len(artifact["checkpoints"]),
        "terminal_point": terminal_selector["point"],
        "terminal_phase": terminal_selector["phase"],
        "terminal_occurrence": terminal_selector["occurrence"],
        "terminal_outcome": terminal_stamp["outcome"],
    }


def validate_case(case: dict[str, Any]) -> None:
    path = (ROOT / case["artifact"]).resolve()
    artifact = json.loads(path.read_text(encoding="utf-8"))
    hashes = {name: digest_json(artifact[name]) for name in SECTIONS}
    if artifact.get("content_sha256") != hashes:
        raise RuntimeError(f"{case['name']}: authoritative section hash mismatch")
    observed = observation(artifact)
    failures = [
        f"{key}: expected {expected!r}, got {observed.get(key)!r}"
        for key, expected in case["expect"].items()
        if observed.get(key) != expected
    ]
    if failures:
        raise RuntimeError(f"{case['name']}: " + "; ".join(failures))


def replay_case(case: dict[str, Any], *, build: bool) -> None:
    for run in range(case["playback_passes"]):
        command = [sys.executable, str(ROOT / "scripts/play.py")]
        if not build or run:
            command.append("--no-build")
        command.extend(
            [
                "--play-artifact",
                case["artifact"],
                "--exit-after-replay",
                "--no-snapshot-on-crash",
            ]
        )
        if run == 0:
            command.append("--unthrottled")
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode:
            raise RuntimeError(
                f"{case['name']}: playback {run + 1} exited "
                f"{completed.returncode}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-missing-artifacts", action="store_true")
    parser.add_argument("--build", action="store_true")
    options = parser.parse_args()
    cases = load_manifest(options.manifest.resolve())["cases"]
    available = []
    for case in cases:
        path = ROOT / case["artifact"]
        if not path.is_file() and options.allow_missing_artifacts:
            print(f"SKIP {case['name']}: {path} is absent")
            continue
        validate_case(case)
        available.append(case)
        print(f"VALID {case['name']}")
    if options.validate_only:
        return 0
    for case in available:
        replay_case(case, build=options.build)
        print(f"PASS {case['name']}: {case['playback_passes']} playback(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"verify_replay.py: {error}", file=sys.stderr)
        raise SystemExit(1)
