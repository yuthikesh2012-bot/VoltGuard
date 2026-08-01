"""
VoltGuard (Web) - Modbus/TCP Protocol Parser
---------------------------------------------
Pure-Python port of the Week 1 "Packet Interceptor" (originally
src/modbus_parser.cpp). Same parsing logic, byte-for-byte: walks a raw
Modbus/TCP byte stream, pulls out the MBAP header and PDU of each frame,
and decodes "Write Single Register" (function code 0x06) commands.

Ported to Python (rather than shelling out to a compiled C++ binary) so
the web app has no external build step -- it runs anywhere Python +
Flask run. The parsing logic itself is unchanged from the original
low-level C++ implementation.
"""

import struct

MBAP_HEADER_SIZE = 7  # transaction(2) + protocol(2) + length(2) + unit(1)
FUNC_WRITE_SINGLE_REGISTER = 0x06

REGISTER_NAMES = {
    0x0001: "PUMP_SPEED_SETPOINT_RPM",
}


def register_name(addr: int) -> str:
    return REGISTER_NAMES.get(addr, "UNKNOWN_REGISTER")


def _read_u16_be(buf: bytes, offset: int) -> int:
    return struct.unpack_from(">H", buf, offset)[0]


def parse_frame(buf: bytes, offset: int):
    """
    Parse one Modbus/TCP frame starting at `offset` in `buf`.
    Returns (frame_dict_or_None, bytes_consumed). bytes_consumed == 0
    means not enough data remains for a full header.
    """
    if offset + MBAP_HEADER_SIZE > len(buf):
        return None, 0

    transaction_id = _read_u16_be(buf, offset + 0)
    protocol_id = _read_u16_be(buf, offset + 2)
    length = _read_u16_be(buf, offset + 4)
    unit_id = buf[offset + 6]

    pdu_offset = offset + MBAP_HEADER_SIZE
    pdu_size = length - 1  # length field includes unit_id byte, PDU doesn't

    if pdu_offset + pdu_size > len(buf):
        raise ValueError(f"Truncated frame: not enough bytes at offset {offset}")

    function_code = buf[pdu_offset]

    register_address = 0
    register_value = 0
    # For this project we only expect Write Single Register (0x06).
    if function_code == FUNC_WRITE_SINGLE_REGISTER:
        register_address = _read_u16_be(buf, pdu_offset + 1)
        register_value = _read_u16_be(buf, pdu_offset + 3)

    frame = {
        "transaction_id": transaction_id,
        "protocol_id": protocol_id,
        "unit_id": unit_id,
        "function_code": function_code,
        "register_address": register_address,
        "register_name": register_name(register_address),
        "register_value": register_value,
    }
    return frame, MBAP_HEADER_SIZE + pdu_size


def parse_all(buf: bytes):
    """Parse every frame in a raw Modbus/TCP byte stream, in order."""
    offset = 0
    frame_number = 0
    frames = []

    while offset < len(buf):
        frame, consumed = parse_frame(buf, offset)
        if consumed == 0:
            break
        frame_number += 1
        frame["frame"] = frame_number
        frames.append(frame)
        offset += consumed

    return frames
