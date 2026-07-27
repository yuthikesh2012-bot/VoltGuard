/*
 * VoltGuard - Week 1: Modbus/TCP Protocol Parser
 * ------------------------------------------------
 * Reads raw Modbus/TCP frames (as produced by traffic_generator.py) from
 * a binary log file and parses out the MBAP header + PDU fields.
 *
 * This is the "Packet Interceptor" module described in the project doc.
 * At this stage (Week 1) it only PARSES traffic and prints structured
 * output -- it does not yet talk to the physics engine or drop packets.
 * That inline-blocking logic comes in Week 2/3 (Rust decision engine).
 *
 * Build:
 *   g++ -std=c++17 -O2 -o modbus_parser modbus_parser.cpp
 *
 * Run:
 *   ./modbus_parser traffic_log.bin
 */

#include <iostream>
#include <fstream>
#include <vector>
#include <cstdint>
#include <iomanip>
#include <stdexcept>

struct ModbusFrame {
    uint16_t transaction_id;
    uint16_t protocol_id;
    uint16_t length;
    uint8_t  unit_id;
    uint8_t  function_code;
    uint16_t register_address;
    uint16_t register_value;
};

// Read a big-endian uint16_t from a byte buffer at a given offset.
static uint16_t read_u16_be(const std::vector<uint8_t>& buf, size_t offset) {
    return static_cast<uint16_t>((buf[offset] << 8) | buf[offset + 1]);
}

// Parse one Modbus/TCP frame starting at `offset` in `buf`.
// Returns the number of bytes consumed, or 0 if not enough data remains.
static size_t parse_frame(const std::vector<uint8_t>& buf, size_t offset, ModbusFrame& out) {
    const size_t MBAP_HEADER_SIZE = 7; // transaction(2) + protocol(2) + length(2) + unit(1)

    if (offset + MBAP_HEADER_SIZE > buf.size()) {
        return 0; // not enough bytes left for a header
    }

    out.transaction_id = read_u16_be(buf, offset + 0);
    out.protocol_id    = read_u16_be(buf, offset + 2);
    out.length         = read_u16_be(buf, offset + 4);
    out.unit_id        = buf[offset + 6];

    size_t pdu_offset = offset + MBAP_HEADER_SIZE;
    size_t pdu_size = out.length - 1; // length field includes unit_id byte, PDU doesn't

    if (pdu_offset + pdu_size > buf.size()) {
        throw std::runtime_error("Truncated frame: not enough bytes for declared PDU length");
    }

    out.function_code = buf[pdu_offset];

    // For this project we only expect Write Single Register (0x06).
    if (out.function_code == 0x06) {
        out.register_address = read_u16_be(buf, pdu_offset + 1);
        out.register_value   = read_u16_be(buf, pdu_offset + 3);
    } else {
        out.register_address = 0;
        out.register_value   = 0;
    }

    return MBAP_HEADER_SIZE + pdu_size;
}

static const char* register_name(uint16_t addr) {
    switch (addr) {
        case 0x0001: return "PUMP_SPEED_SETPOINT_RPM";
        default:     return "UNKNOWN_REGISTER";
    }
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <modbus_log_file>\n";
        return 1;
    }

    std::ifstream file(argv[1], std::ios::binary);
    if (!file) {
        std::cerr << "Error: could not open file '" << argv[1] << "'\n";
        return 1;
    }

    std::vector<uint8_t> buf((std::istreambuf_iterator<char>(file)),
                               std::istreambuf_iterator<char>());

    std::cout << "Loaded " << buf.size() << " bytes from '" << argv[1] << "'\n\n";

    size_t offset = 0;
    int frame_count = 0;

    while (offset < buf.size()) {
        ModbusFrame frame;
        size_t consumed;

        try {
            consumed = parse_frame(buf, offset, frame);
        } catch (const std::exception& e) {
            std::cerr << "Parse error at offset " << offset << ": " << e.what() << "\n";
            break;
        }

        if (consumed == 0) break;

        frame_count++;
        std::cout << "Frame #" << frame_count
                   << " | txn_id=" << frame.transaction_id
                   << " | unit=" << static_cast<int>(frame.unit_id)
                   << " | func=0x" << std::hex << std::setw(2) << std::setfill('0')
                   << static_cast<int>(frame.function_code) << std::dec;

        if (frame.function_code == 0x06) {
            std::cout << " | register=" << register_name(frame.register_address)
                       << " | value=" << frame.register_value;

            // Soft sanity flag (NOT the real physics check -- that lives
            // in the physics engine per the project design. This is just
            // a quick "does this look weird" print for visibility.)
            if (frame.register_value > 3000) {
                std::cout << "  <-- SUSPICIOUSLY HIGH (flag for physics engine)";
            }
        }
        std::cout << "\n";

        offset += consumed;
    }

    std::cout << "\nParsed " << frame_count << " Modbus/TCP frame(s) total.\n";
    return 0;
}
