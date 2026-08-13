// SimAnt Macintosh generated recovery -- first source-bound instruction.
#pragma once

#include "../port_forge/src/arch/m68k/alu.hpp"
#include "../port_forge/src/platform/mac68k/executor.hpp"

namespace simant::mac68k::generated {

// mac.code.1.4: ORI.B #$12,D0 (original bytes 00 00 03 12).
//
// This is intentionally one decoded fallthrough instruction. PortForge's
// NativeHooks verifies the complete source bytes and the one-instruction
// result before accepting it; modified or relocated code is handled by the
// stable CODE-resource identity and interpreter fallback.
inline pf::mac68k::NativeBlockResult mac_code_1_4(
    pf::mac68k::Machine& machine) {
    const uint32_t low =
        pf::m68k::alu::logic(
            machine.cpu.cpu,
            (machine.cpu.cpu.d[0] & 0xFFu) | 0x12u,
            1);
    machine.cpu.cpu.d[0] =
        (machine.cpu.cpu.d[0] & 0xFFFFFF00u) | low;
    return {
        (machine.cpu.cpu.pc + 4u) & pf::m68k::kAddressMask,
        1,
        8,
    };
}

inline void install(pf::mac68k::Executor& executor) {
    executor.native_hooks().register_block(
        {1, 4}, {0x00, 0x00, 0x03, 0x12}, &mac_code_1_4);
}

} // namespace simant::mac68k::generated
