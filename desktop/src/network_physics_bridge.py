"""
VoltGuard - Week 2: Bridge Integration
----------------------------------------
Connects the C++ Packet Interceptor (modbus_parser.cpp, run in --json mode)
to the Python Physics Engine (physics_model.py).

Per the project plan, Week 2's job is:
    "Connect the network parser to the physics engine. Pass incoming
    command variables into the simulation API."

This module does NOT drop packets or act as an inline IPS yet -- that is
explicitly a Week 3 deliverable (Rust decision engine, sub-10ms latency).
Right now the bridge is a pipeline:

    traffic_log.bin --(C++ parser, --json)--> JSON Lines
                    --(this bridge)--> physics_model.evaluate_command()
                    --(this bridge)--> bridge_report.jsonl + console summary

That report file is what the Week 2 native Qt dashboard loads and displays.

Run:
    python3 src/network_physics_bridge.py
    (assumes ../modbus_parser has been built via build.sh, and
     ../data/traffic_log.bin already exists -- run traffic_generator.py
     first if not.)
"""

import json
import os
import subprocess
import sys

from physics_model import PipelinePhysicsEngine

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
PARSER_CANDIDATES = (
    os.path.join(PROJECT_ROOT, "modbus_parser"),
    os.path.join(PROJECT_ROOT, "modbus_parser.exe"),
    os.path.join(HERE, "modbus_parser"),
    os.path.join(HERE, "modbus_parser.exe"),
)
TRAFFIC_LOG = os.path.join(PROJECT_ROOT, "data", "traffic_log.bin")
BRIDGE_REPORT = os.path.join(PROJECT_ROOT, "data", "bridge_report.jsonl")

# The only register this project models physically (see physics_model.py).
PUMP_SPEED_REGISTER = "PUMP_SPEED_SETPOINT_RPM"
WRITE_SINGLE_REGISTER_FUNC = 6


def run_parser_json(traffic_log_path: str) -> list:
    """
    Invoke the compiled C++ parser in --json mode and capture its
    stdout, parsing each line as a JSON object. This is the actual
    "bridge" -- crossing from the C++ network layer into Python.
    """
    parser_bin = next(
        (path for path in PARSER_CANDIDATES if os.path.exists(path)), None
    )
    if parser_bin is None:
        raise FileNotFoundError(
            "modbus_parser executable not found. Build it first with ./build.sh"
        )
    if not os.path.exists(traffic_log_path):
        raise FileNotFoundError(
            f"'{traffic_log_path}' not found. Run traffic_generator.py first."
        )

    child_env = os.environ.copy()
    runtime_paths = [
        os.path.dirname(parser_bin),
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
    ]
    child_env["PATH"] = os.pathsep.join(
        path for path in runtime_paths + [child_env.get("PATH", "")] if path
    )

    try:
        result = subprocess.run(
            [parser_bin, traffic_log_path, "--json"],
            capture_output=True,
            text=True,
            check=True,
            env=child_env,
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip() or "no parser output"
        raise RuntimeError(
            f"modbus_parser failed with exit code {error.returncode}: {details}"
        ) from error

    frames = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        frames.append(json.loads(line))
    return frames


def evaluate_frames(frames: list, engine: PipelinePhysicsEngine) -> list:
    """
    Pass each parsed command's variables into the physics simulation API
    (evaluate_command) and merge the verdict back onto the frame record.
    Frames that aren't pump-speed writes pass through unevaluated (there's
    no physics model for them yet).
    """
    enriched = []

    for frame in frames:
        record = dict(frame)  # copy so we don't mutate the parser's output

        is_pump_command = (
            frame.get("function_code") == WRITE_SINGLE_REGISTER_FUNC
            and frame.get("register_name") == PUMP_SPEED_REGISTER
        )

        if is_pump_command:
            rpm = frame["register_value"]
            verdict = engine.evaluate_command(rpm)
            record.update(verdict)
        else:
            record["verdict"] = "NOT_MODELED"

        enriched.append(record)

    return enriched


def write_bridge_report(enriched_frames: list, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.writelines(json.dumps(record) + "\n" for record in enriched_frames)


def print_summary(enriched_frames: list) -> None:
    safe = sum(1 for r in enriched_frames if r.get("verdict") == "SAFE")
    catastrophic = sum(1 for r in enriched_frames if r.get("verdict") == "CATASTROPHIC")
    not_modeled = sum(1 for r in enriched_frames if r.get("verdict") == "NOT_MODELED")

    print(f"{'Frame':<6} {'Txn':<6} {'Func':<5} {'Register':<26} {'Value':<8} {'Pred(psi)':<10} {'Verdict'}")
    print("-" * 80)
    for r in enriched_frames:
        pred = r.get("predicted_pressure_psi", "-")
        print(f"{r['frame']:<6} {r['transaction_id']:<6} {r['function_code']:<5} "
              f"{r.get('register_name', '-'): <26} {r.get('register_value', '-'):<8} "
              f"{pred!s:<10} {r.get('verdict')}")

    print("-" * 80)
    print(f"Total: {len(enriched_frames)}  |  SAFE: {safe}  |  "
          f"CATASTROPHIC: {catastrophic}  |  Not modeled: {not_modeled}")

    if catastrophic:
        print(f"\n[ALERT] {catastrophic} command(s) would breach physical safety "
              f"limits. (Week 3 will make the Rust decision engine DROP these "
              f"before they reach the pump.)")


def main():
    traffic_log = sys.argv[1] if len(sys.argv) > 1 else TRAFFIC_LOG

    frames = run_parser_json(traffic_log)
    engine = PipelinePhysicsEngine()
    enriched = evaluate_frames(frames, engine)

    write_bridge_report(enriched, BRIDGE_REPORT)
    print_summary(enriched)
    print(f"\nWrote bridge report -> {BRIDGE_REPORT}")
    print("(Load this file in the Week 2 Qt dashboard: dashboard/voltguard_dashboard)")


if __name__ == "__main__":
    main()
