#include "../native/simant_mac_generated.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <stdexcept>

namespace {

constexpr uint32_t kBase = 0x2000;

void initialize(pf::mac68k::Machine& machine) {
    machine.cpu.write16(kBase, 0x0000);
    machine.cpu.write16(kBase + 2, 0x0312);
    machine.register_code({1, kBase, 4, 4, 1});
}
void reset_case(
    pf::mac68k::Machine& machine, uint32_t d0, uint16_t status) {
    std::fill(std::begin(machine.cpu.cpu.d),
              std::end(machine.cpu.cpu.d), 0u);
    std::fill(std::begin(machine.cpu.cpu.a),
              std::end(machine.cpu.cpu.a), 0u);
    machine.cpu.cpu.d[0] = d0;
    machine.cpu.cpu.pc = kBase;
    machine.cpu.cpu.status = status;
    machine.cpu.cpu.usp = 0;
    machine.cpu.cpu.ssp = 0;
    machine.cpu.cpu.vbr = 0;
    machine.cpu.cpu.stopped = false;
    machine.cpu.instructions = 0;
    machine.cpu.cpu_cycles = 0;
}

bool same_cpu(
    const pf::mac68k::Machine& oracle,
    const pf::mac68k::Machine& generated) {
    return std::equal(
               std::begin(oracle.cpu.cpu.d),
               std::end(oracle.cpu.cpu.d),
               std::begin(generated.cpu.cpu.d)) &&
           std::equal(
               std::begin(oracle.cpu.cpu.a),
               std::end(oracle.cpu.cpu.a),
               std::begin(generated.cpu.cpu.a)) &&
           oracle.cpu.cpu.pc == generated.cpu.cpu.pc &&
           oracle.cpu.cpu.status == generated.cpu.cpu.status &&
           oracle.cpu.instructions == generated.cpu.instructions &&
           oracle.cpu.cpu_cycles == generated.cpu.cpu_cycles;
}

} // namespace

int main() {
    try {
        pf::mac68k::Machine oracle_machine;
        pf::mac68k::Machine generated_machine;
        initialize(oracle_machine);
        initialize(generated_machine);
        pf::mac68k::Executor oracle(oracle_machine);
        pf::mac68k::Executor generated(generated_machine);
        simant::mac68k::generated::install(generated);

        uint64_t cases = 0;
        for (uint32_t low = 0; low <= 0xFF; ++low) {
            for (uint16_t flags = 0; flags <= 0x1F; ++flags) {
                const uint32_t d0 = 0xA5C30000u | low;
                const uint16_t status = static_cast<uint16_t>(
                    pf::m68k::sr::S | flags);
                reset_case(oracle_machine, d0, status);
                reset_case(generated_machine, d0, status);
                oracle.step();
                generated.step();
                if (!same_cpu(oracle_machine, generated_machine)) {
                    std::fprintf(
                        stderr,
                        "native parity mismatch: d0=%08X status=%04X\n",
                        static_cast<unsigned>(d0),
                        static_cast<unsigned>(status));
                    return 1;
                }
                ++cases;
            }
        }

        if (generated.native_hooks().native_dispatches != cases ||
            generated.native_hooks().unregistered_dispatches != 0 ||
            generated.native_hooks().source_changed_dispatches != 0) {
            std::fprintf(stderr, "native dispatch counters disagree\n");
            return 1;
        }
        for (uint32_t offset = 0; offset < 4; ++offset) {
            if (!generated_machine.cpu.was_executed(kBase + offset) ||
                !oracle_machine.cpu.was_executed(kBase + offset)) {
                std::fprintf(stderr, "executed-byte parity mismatch\n");
                return 1;
            }
        }

        std::printf(
            "SimAnt mac.code.1.4 native parity passed (%llu cases)\n",
            static_cast<unsigned long long>(cases));
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "native entry test: %s\n", error.what());
        return 2;
    }
}
