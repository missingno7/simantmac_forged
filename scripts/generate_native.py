#!/usr/bin/env python3
"""Generate the selected SimAnt Mac68k native compatibility functions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "recovery" / "native-selection.json"
OUTPUT = ROOT / "native" / "simant_mac_generated.hpp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate source-bound Mac68k compatibility functions."
    )
    parser.add_argument(
        "--write", action="store_true", help="replace the tracked header"
    )
    return parser.parse_args()


def selected_instructions(record: dict, identity: str) -> list[dict]:
    instructions = record.get("source_instructions")
    if not isinstance(instructions, list) or not instructions:
        raise RuntimeError(f"selected function has no source certificate: {identity}")
    expected_offset = int(identity.rsplit(".", 1)[1])
    for instruction in instructions:
        if not isinstance(instruction, dict):
            raise RuntimeError(f"selected function has malformed source: {identity}")
        encoded = bytes.fromhex(instruction.get("bytes", ""))
        if not encoded or len(encoded) != instruction.get("length"):
            raise RuntimeError(f"selected function has invalid encoding: {identity}")
        if instruction.get("resource_offset") != expected_offset:
            raise RuntimeError(f"selected function source is not contiguous: {identity}")
        expected_offset += len(encoded)
    return instructions


def source_bytes(instructions: list[dict]) -> list[int]:
    return [
        byte
        for instruction in instructions
        for byte in bytes.fromhex(instruction["bytes"])
    ]


def byte_initializer(values: list[int], indent: str = "        ") -> str:
    rows = []
    for start in range(0, len(values), 4):
        rows.append(
            indent
            + ", ".join(f"0x{value:02X}" for value in values[start : start + 4])
            + ","
        )
    return "\n".join(rows)


def emit_instruction(identity: str, instructions: list[dict]) -> str:
    if len(instructions) != 1 or instructions[0]["bytes"] != "00000312":
        raise RuntimeError(
            f"{identity}: initial generator supports the bound ORI.B form"
        )
    return f"""// {identity}: ORI.B #$12,D0 (original bytes 00 00 03 12).
inline pf::mac68k::NativeBlockResult mac_code_1_4(
    pf::mac68k::Machine& machine) {{
    const uint32_t low = pf::m68k::alu::logic(
        machine.cpu.cpu,
        (machine.cpu.cpu.d[0] & 0xFFu) | 0x12u, 1);
    machine.cpu.cpu.d[0] =
        (machine.cpu.cpu.d[0] & 0xFFFFFF00u) | low;
    return {{
        (machine.cpu.cpu.pc + 4u) & pf::m68k::kAddressMask,
        1, 8,
    }};
}}
"""


def emit_linear_function(identity: str, instructions: list[dict]) -> str:
    encodings = [item["bytes"] for item in instructions]
    expected = [
        "4e560000",
        "206e0008",
        "20280002",
        "4e5e",
        "4e75",
    ]
    if encodings != expected:
        raise RuntimeError(
            f"{identity}: initial linear generator refuses changed ABI/IR"
        )
    return f"""// {identity}: generated linear MPW leaf function.
inline pf::mac68k::NativeBlockResult mac_code_2_2906(
    pf::mac68k::Machine& machine) {{
    auto& cpu = machine.cpu.cpu;
    cpu.a[7] = (cpu.a[7] - 4u) & pf::m68k::kAddressMask;
    machine.cpu.write32(cpu.a[7], cpu.a[6]);
    cpu.a[6] = cpu.a[7];
    cpu.a[0] = machine.cpu.read32(
        (cpu.a[6] + 8u) & pf::m68k::kAddressMask);
    cpu.d[0] = machine.cpu.read32(
        (cpu.a[0] + 2u) & pf::m68k::kAddressMask);
    pf::m68k::alu::logic(cpu, cpu.d[0], 4);
    cpu.a[7] = cpu.a[6];
    cpu.a[6] = machine.cpu.read32(cpu.a[7]);
    cpu.a[7] = (cpu.a[7] + 4u) & pf::m68k::kAddressMask;
    const uint32_t next_pc =
        machine.cpu.read32(cpu.a[7]) & pf::m68k::kAddressMask;
    cpu.a[7] = (cpu.a[7] + 4u) & pf::m68k::kAddressMask;
    return {{next_pc, 5, 76}};
}}
"""


def generate(selection: dict) -> str:
    if selection.get("format") != "simant-mac-native-selection-v1":
        raise RuntimeError("native selection has an unsupported format")
    if len(selection.get("program_sha256", "")) != 64 or len(
        selection.get("lift_plan_sha256", "")
    ) != 64:
        raise RuntimeError("native selection lacks source provenance")

    bodies = []
    registrations = []
    for record in selection.get("functions", []):
        identity = record.get("code_identity")
        certificate = record.get("certificate")
        instructions = selected_instructions(record, identity)
        values = source_bytes(instructions)
        parts = identity.split(".")
        if len(parts) != 4 or parts[:2] != ["mac", "code"]:
            raise RuntimeError(f"invalid selected identity: {identity}")
        resource_id, offset = int(parts[2]), int(parts[3])
        symbol = identity.replace(".", "_")
        if certificate == "instruction":
            bodies.append(emit_instruction(identity, instructions))
            registrations.append(
                "    executor.native_hooks().register_block(\n"
                f"        {{{resource_id}, {offset}}},\n"
                "        {\n"
                f"{byte_initializer(values)}\n"
                "        },\n"
                f"        &{symbol});"
            )
        elif certificate == "linear-function":
            bodies.append(emit_linear_function(identity, instructions))
            registrations.append(
                "    executor.native_hooks().register_linear_function(\n"
                f"        {{{resource_id}, {offset}}},\n"
                "        {\n"
                f"{byte_initializer(values)}\n"
                "        },\n"
                f"        &{symbol});"
            )
        else:
            raise RuntimeError(f"unsupported certificate: {certificate!r}")

    return """// Generated by scripts/generate_native.py; do not edit.
#pragma once

#include "../port_forge/src/arch/m68k/alu.hpp"
#include "../port_forge/src/platform/mac68k/executor.hpp"

namespace simant::mac68k::generated {

""" + "\n".join(bodies) + """\ninline void install(
    pf::mac68k::Executor& executor) {
""" + "\n".join(registrations) + """
}

} // namespace simant::mac68k::generated
"""


def main() -> int:
    args = parse_args()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    generated = generate(selection)
    if args.write:
        OUTPUT.write_text(generated, encoding="utf-8", newline="\n")
        print(f"generated: {OUTPUT}")
        return 0
    current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
    if current != generated:
        raise RuntimeError(
            "tracked native header is stale; run "
            "python scripts/generate_native.py --write"
        )
    print("SimAnt Mac68k generated header is current")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"generate_native.py: {error}", file=sys.stderr)
        raise SystemExit(1)
