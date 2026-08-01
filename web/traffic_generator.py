"""
VoltGuard (Web) - Mock Modbus/TCP Traffic Generator
----------------------------------------------------
Builds real, byte-accurate Modbus/TCP "Write Single Register" frames
representing commands sent to an industrial pump. Produces both NORMAL
commands (safe RPM setpoints) and MALICIOUS commands (syntactically
valid, but physically dangerous RPM setpoints -- the "50,000 RPM" attack
scenario from the project brief).

Modbus/TCP frame layout (all fields big-endian):

    MBAP Header (7 bytes)
        Transaction ID   : 2 bytes
        Protocol ID      : 2 bytes  (always 0x0000 for Modbus)
        Length           : 2 bytes  (byte count of everything after this field)
        Unit ID          : 1 byte

    PDU (Protocol Data Unit)
        Function Code    : 1 byte   (0x06 = Write Single Register)
        Register Address : 2 bytes  (0x0001 = Pump Speed Setpoint register)
        Register Value   : 2 bytes  (the requested RPM, 0-65535)

This module is identical in intent to the original Week 1
traffic_generator.py, adapted to hand raw bytes back to the Flask app
instead of writing straight to disk.
"""

import random
import struct

PROTOCOL_ID = 0x0000
UNIT_ID = 0x01
FUNC_WRITE_SINGLE_REGISTER = 0x06
REGISTER_PUMP_SPEED = 0x0001

SAFE_RPM_MIN = 0
SAFE_RPM_MAX = 3000  # anything above this is where the danger zone begins
DANGEROUS_RPM_OPTIONS = [50000, 65000, 45000, 60000]


def build_modbus_frame(transaction_id: int, register_value: int,
                        register_addr: int = REGISTER_PUMP_SPEED,
                        function_code: int = FUNC_WRITE_SINGLE_REGISTER,
                        unit_id: int = UNIT_ID) -> bytes:
    """
    Construct a single, syntactically valid Modbus/TCP "Write Single
    Register" request frame. This function has NO concept of whether the
    value is dangerous -- that's exactly the point of the project. A
    standard IT firewall would happily allow anything built here.
    """
    pdu = struct.pack(">BHH", function_code, register_addr, register_value)
    length = len(pdu) + 1  # +1 for the unit id byte counted in "length"
    mbap = struct.pack(">HHHB", transaction_id, PROTOCOL_ID, length, unit_id)
    return mbap + pdu


def generate_traffic(num_normal: int = 20, num_malicious: int = 5):
    """
    Returns a shuffled list of dicts:
        {"frame_bytes": bytes, "label": "NORMAL"|"MALICIOUS",
         "rpm": int, "transaction_id": int}
    """
    entries = []
    transaction_id = 1

    for _ in range(num_normal):
        rpm = random.randint(SAFE_RPM_MIN, SAFE_RPM_MAX)
        entries.append({
            "frame_bytes": build_modbus_frame(transaction_id, rpm),
            "label": "NORMAL",
            "rpm": rpm,
            "transaction_id": transaction_id,
        })
        transaction_id += 1

    for _ in range(num_malicious):
        rpm = random.choice(DANGEROUS_RPM_OPTIONS)
        entries.append({
            "frame_bytes": build_modbus_frame(transaction_id, rpm),
            "label": "MALICIOUS",
            "rpm": rpm,
            "transaction_id": transaction_id,
        })
        transaction_id += 1

    # Shuffle so malicious commands are interleaved realistically, like
    # they'd appear hidden in normal traffic on the wire.
    random.shuffle(entries)
    return entries
