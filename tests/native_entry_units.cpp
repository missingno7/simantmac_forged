#include "../native/simant_mac_generated.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <stdexcept>

namespace {

constexpr uint32_t kBase = 0x2000;
constexpr uint32_t kFunctionBase = 0x3000;
constexpr uint32_t kStack = 0x8000;
constexpr uint32_t kArgument = 0x9000;
constexpr uint32_t kReturn = 0xA000;

constexpr std::array<uint8_t, 16> kFunctionSource = {
    0x4E, 0x56, 0x00, 0x00,
    0x20, 0x6E, 0x00, 0x08,
    0x20, 0x28, 0x00, 0x02,
    0x4E, 0x5E,
    0x4E, 0x75,
};

void initialize(pf::mac68k::Machine& machine) {
    machine.cpu.write16(kBase, 0x0000);
    machine.cpu.write16(kBase + 2, 0x0312);
    machine.register_code({1, kBase, 4, 4, 1});
    std::copy(
        kFunctionSource.begin(), kFunctionSource.end(),
        machine.cpu.memory.begin() + kFunctionBase);
    machine.register_code({2, kFunctionBase, 16, 2906, 1});
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

void reset_function_case(
    pf::mac68k::Machine& machine, uint32_t value,
    uint16_t status, uint32_t seed) {
    for (unsigned index = 0; index < 8; ++index) {
        machine.cpu.cpu.d[index] = seed ^ (0x11111111u * index);
        machine.cpu.cpu.a[index] =
            (seed + 0x01010101u * index) & pf::m68k::kAddressMask;
    }
    machine.cpu.cpu.pc = kFunctionBase;
    machine.cpu.cpu.status = status;
    machine.cpu.cpu.a[6] = 0x00707070u ^ seed;
    machine.cpu.cpu.a[7] = kStack;
    machine.cpu.cpu.ssp = kStack;
    machine.cpu.cpu.usp = 0;
    machine.cpu.cpu.vbr = 0;
    machine.cpu.cpu.stopped = false;
    machine.cpu.instructions = 0;
    machine.cpu.cpu_cycles = 0;
    machine.cpu.write32(kStack, kReturn);
    machine.cpu.write32(kStack + 4, kArgument);
    machine.cpu.write32(kArgument + 2, value);
    machine.cpu.write32(kStack - 4, 0xCCCCCCCCu);
}

bool same_function_effects(
    const pf::mac68k::Machine& oracle,
    const pf::mac68k::Machine& generated) {
    if (!same_cpu(oracle, generated)) return false;
    for (uint32_t address = kStack - 4;
         address < kStack + 8; ++address) {
        if (oracle.cpu.memory[address] !=
            generated.cpu.memory[address])
            return false;
    }
    return true;
}

void run_oracle_function(pf::mac68k::Executor& oracle) {
    for (unsigned instruction = 0; instruction < 5; ++instruction)
        oracle.step();
}

bool poison_would_match(
    const pf::mac68k::Machine& oracle,
    pf::mac68k::Machine& poisoned, uint32_t offset,
    bool little_endian) {
    const uint32_t oracle_value =
        (static_cast<uint32_t>(oracle.cpu.memory[kArgument + 2]) << 24) |
        (static_cast<uint32_t>(oracle.cpu.memory[kArgument + 3]) << 16) |
        (static_cast<uint32_t>(oracle.cpu.memory[kArgument + 4]) << 8) |
        static_cast<uint32_t>(oracle.cpu.memory[kArgument + 5]);
    reset_function_case(
        poisoned, oracle_value,
        oracle.cpu.cpu.status, 0x13579BDFu);
    uint32_t value = 0;
    if (little_endian) {
        for (unsigned index = 0; index < 4; ++index)
            value |= static_cast<uint32_t>(
                poisoned.cpu.memory[kArgument + offset + index])
                << (8 * index);
    } else {
        value = poisoned.cpu.read32(kArgument + offset);
    }
    poisoned.cpu.cpu.d[0] = value;
    return poisoned.cpu.cpu.d[0] == oracle.cpu.cpu.d[0];
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

        uint64_t function_cases = 0;
        uint32_t state = 0xC001D00Du;
        for (unsigned sample = 0; sample < 257; ++sample) {
            state = state * 1664525u + 1013904223u;
            for (uint16_t flags = 0; flags <= 0x1F; ++flags) {
                const uint16_t status = static_cast<uint16_t>(
                    pf::m68k::sr::S | flags);
                reset_function_case(
                    oracle_machine, state, status,
                    state ^ (sample * 0x01010101u));
                reset_function_case(
                    generated_machine, state, status,
                    state ^ (sample * 0x01010101u));
                run_oracle_function(oracle);
                generated.step();
                if (!same_function_effects(
                        oracle_machine, generated_machine)) {
                    std::fprintf(
                        stderr,
                        "native function parity mismatch: "
                        "value=%08X status=%04X oracle_cycles=%llu "
                        "generated_cycles=%llu\n",
                        static_cast<unsigned>(state),
                        static_cast<unsigned>(status),
                        static_cast<unsigned long long>(
                            oracle_machine.cpu.cpu_cycles),
                        static_cast<unsigned long long>(
                            generated_machine.cpu.cpu_cycles));
                    return 1;
                }
                ++function_cases;
            }
        }

        // Poison gates: an endian reversal and the plausible adjacent +4
        // field must both disagree with the oracle on a non-symmetric case.
        reset_function_case(
            oracle_machine, 0x12345678u,
            static_cast<uint16_t>(pf::m68k::sr::S), 0x13579BDFu);
        oracle_machine.cpu.write32(kArgument + 4, 0xA1B2C3D4u);
        run_oracle_function(oracle);
        pf::mac68k::Machine poisoned;
        initialize(poisoned);
        poisoned.cpu.write32(kArgument + 4, 0xA1B2C3D4u);
        if (poison_would_match(oracle_machine, poisoned, 4, false) ||
            poison_would_match(oracle_machine, poisoned, 2, true)) {
            std::fprintf(stderr, "native function poison gate failed\n");
            return 1;
        }

        // An exact-source mismatch must fall back to the interpreter before
        // the generated function can publish any effect.
        reset_function_case(
            generated_machine, 0x89ABCDEFu,
            static_cast<uint16_t>(pf::m68k::sr::S), 0x2468ACE0u);
        generated_machine.cpu.write16(kFunctionBase + 4, 0x4E71);
        const uint32_t before_sp = generated_machine.cpu.cpu.a[7];
        generated.step();
        if (generated.native_hooks().source_changed_dispatches != 1 ||
            generated_machine.cpu.cpu.a[7] != before_sp - 4u ||
            generated_machine.cpu.cpu.pc != kFunctionBase + 4) {
            std::fprintf(stderr, "native function source guard failed\n");
            return 1;
        }

        std::printf(
            "SimAnt native parity passed (%llu instruction cases, "
            "%llu function cases, poison/source guards)\n",
            static_cast<unsigned long long>(cases),
            static_cast<unsigned long long>(function_cases));
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "native entry test: %s\n", error.what());
        return 2;
    }
}
