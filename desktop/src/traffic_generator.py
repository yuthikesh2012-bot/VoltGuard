"""
VoltGuard - Week 1: Mock Modbus/TCP Traffic Generator
------------------------------------------------------
Generates raw Modbus/TCP frames representing commands sent to an industrial
pump (e.g. in a water treatment plant). Produces both NORMAL commands
(safe RPM setpoints) and MALICIOUS commands (syntactically valid, but
physically dangerous RPM setpoints, e.g. the "50,000 RPM" attack scenario
from the project brief).

Modbus/TCP frame layout (all fields big-endian):

    MBAP Header (7 bytes)
        Transaction ID   : 2 bytes  (increments per request)
        Protocol ID      : 2 bytes  (always 0x0000 for Modbus)
        Length           : 2 bytes  (byte count of everything after this field)
        Unit ID          : 1 byte   (slave/device address)

    PDU (Protocol Data Unit)
        Function Code    : 1 byte   (0x06 = Write Single Register)
        Register Address : 2 bytes  (0x0001 = Pump Speed Setpoint register)
        Register Value   : 2 bytes  (the requested RPM, 0-65535)

Output: writes all frames sequentially to `traffic_log.bin`, and also
prints each frame as hex + a human-readable label so you can eyeball it.
"""

import struct
import random

import os
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "traffic_log.bin")

# --- Modbus protocol constants ---
PROTOCOL_ID = 0x0000
UNIT_ID = 0x01
FUNC_WRITE_SINGLE_REGISTER = 0x06
REGISTER_PUMP_SPEED = 0x0001  # holding register: pump speed setpoint (RPM)

# --- Plant-safety constants (used later by the physics engine, Week 1/2) ---
SAFE_RPM_MIN = 0
SAFE_RPM_MAX = 3000  # anything above this is where the danger zone begins


def build_modbus_frame(transaction_id: int, register_value: int,
                        register_addr: int = REGISTER_PUMP_SPEED,
                        function_code: int = FUNC_WRITE_SINGLE_REGISTER,
                        unit_id: int = UNIT_ID) -> bytes:
    """
    Construct a single, syntactically valid Modbus/TCP "Write Single
    Register" request frame. Note: this function has NO concept of whether
    the value is dangerous -- that's exactly the point of the project.
    A malformed IT firewall would happily allow anything built here.
    """
    pdu = struct.pack(">BHH", function_code, register_addr, register_value)
    length = len(pdu) + 1  # +1 for the unit id byte counted in "length"
    mbap = struct.pack(">HHHB", transaction_id, PROTOCOL_ID, length, unit_id)
    return mbap + pdu


def generate_normal_command(transaction_id: int) -> bytes:
    """A safe, plausible pump speed setpoint."""
    rpm = random.randint(SAFE_RPM_MIN, SAFE_RPM_MAX)
    return build_modbus_frame(transaction_id, rpm), rpm


def generate_malicious_command(transaction_id: int) -> bytes:
    """
    A syntactically perfect Modbus frame requesting an impossible /
    catastrophic RPM. This is the exact attack described in the problem
    statement: valid protocol syntax, physically dangerous payload.
    Register value must fit in an unsigned 16-bit int (0-65535), so we
    pick something absurdly high but still "legal" on the wire.
    """
    dangerous_options = [50000, 65000, 45000, 60000]
    rpm = random.choice(dangerous_options)
    return build_modbus_frame(transaction_id, rpm), rpm


def generate_traffic(num_normal: int = 20, num_malicious: int = 5):
    frames = []
    transaction_id = 1

    for _ in range(num_normal):
        frame, rpm = generate_normal_command(transaction_id)
        frames.append((frame, "NORMAL", rpm))
        transaction_id += 1

    for _ in range(num_malicious):
        frame, rpm = generate_malicious_command(transaction_id)
        frames.append((frame, "MALICIOUS", rpm))
        transaction_id += 1

    # Shuffle so malicious commands are interleaved realistically,
    # like they'd appear hidden in normal traffic on the wire.
    random.shuffle(frames)
    return frames


def main():
    frames = generate_traffic(num_normal=20, num_malicious=5)

    with open(OUTPUT_FILE, "wb") as f:
        for frame, label, rpm in frames:
            f.write(frame)
            print(f"[{label:9s}] RPM={rpm:>6} | hex={frame.hex()}")

    print(f"\nWrote {len(frames)} Modbus/TCP frames to '{OUTPUT_FILE}'")
    print(f"({sum(1 for _,l,_ in frames if l=='MALICIOUS')} malicious / "
          f"{sum(1 for _,l,_ in frames if l=='NORMAL')} normal)")


if __name__ == "__main__":
    main()
