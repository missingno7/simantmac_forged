#!/usr/bin/env python3
"""Static/parse guard for the public Macintosh player contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "scripts" / "play.py"
VERIFY_REPLAY = ROOT / "scripts" / "verify_replay.py"
PROJECT_MANIFEST = ROOT / "portforge.project.json"


def load_play():
    spec = importlib.util.spec_from_file_location("simantmac_play", PLAY)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/play.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    play = load_play()
    parser = play.parser()
    require(
        parser.parse_args(["--record-replay"]).record_replay == "",
        "--record-replay optional default disappeared",
    )
    require(
        parser.parse_args(["--record-artifact", "named"]).record_replay
        == "named",
        "--record-artifact compatibility alias drifted",
    )
    require(
        parser.parse_args(["--play-replay", "demo"]).play_replay == "demo",
        "--play-replay disappeared",
    )
    require(
        parser.parse_args(["--snapshot", "session"]).resume_snapshot
        == "session",
        "--snapshot session-resume alias disappeared",
    )
    require(
        parser.parse_args(["--", "--unthrottled"]).runner_args
        == ["--", "--unthrottled"],
        "strict '--' forwarding drifted",
    )

    source = PLAY.read_text(encoding="utf-8")
    for contract in (
        "--verify-replay",
        "--inspect-replay",
        "--inspect-session",
        "--verify-session",
        "--session-snapshot",
        "--snapshot-after-polls",
        "session_publication_mode",
        'resume_mode == "record"',
        "--replay-game-id",
        "--implementation-plan",
        "--artifact-dir",
        "mac68k-event-poll-live-session",
        "canonical outputs: state only",
    ):
        require(contract in source, f"missing player contract: {contract}")
    require(
        "args.quit_on_stop or args.headless or verify_mode" in source,
        "verification no longer exits fail-closed when the guest stops",
    )
    for retired in (
        "portforge-mac68k-replay-v1",
        "captured_artifact_inputs",
        "deliver_host_input",
    ):
        require(retired not in source, f"retired player authority returned: {retired}")
    verification = VERIFY_REPLAY.read_text(encoding="utf-8")
    require(
        '"--verify-replay"' in verification,
        "the corpus gate bypasses the coherent verification operation",
    )
    require(
        '"--play-artifact"' not in verification,
        "the corpus gate regressed to interactive playback",
    )
    manifest = json.loads(PROJECT_MANIFEST.read_text(encoding="utf-8"))
    replay = manifest["player"]["runtimes"]["oracle"].get("replay")
    require(
        replay == {
            "supported": True,
            "boundary_profile": "profiles/replay-boundaries-v1.json",
            "implementation_plan": "recovery/execution-plan-oracle.json",
        },
        "oracle ArtifactV2 authority is absent or drifted",
    )
    for field in ("boundary_profile", "implementation_plan"):
        require(
            (ROOT / replay[field]).is_file(),
            f"oracle replay authority is missing: {replay[field]}",
        )
    print("Macintosh player interface ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
