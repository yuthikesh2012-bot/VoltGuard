"""
VoltGuard (Web) - Flask application
------------------------------------
Web-application version of Project 1 ("VoltGuard": Physics-Aware
ICS/SCADA Intrusion Detection System), covering the Week 1 + Week 2
deliverables:

  Week 1 - Protocol Parsing:  traffic_generator.py + modbus_parser.py
  Week 1 - Physics Modeling:  physics_model.py
  Week 2 - Bridge Integration: this file's /api/bridge/run route feeds
           each parsed pump-speed command straight into
           PipelinePhysicsEngine.evaluate_command()
  Week 2 - Native Dashboard -> replaced here by a browser dashboard
           (templates/index.html + static/app.js) serving the same job:
           load parsed traffic into a table and highlight CATASTROPHIC
           rows.

State is kept in-memory (single-process demo app). Nothing here drops
or blocks traffic yet -- per the project plan, inline blocking (the
Rust IPS, sub-10ms latency) is a Week 3 deliverable.
"""

from flask import Flask, render_template, request, jsonify

from traffic_generator import generate_traffic
from modbus_parser import parse_all
from physics_model import PipelinePhysicsEngine

app = Flask(__name__)
engine = PipelinePhysicsEngine()

PUMP_SPEED_REGISTER = "PUMP_SPEED_SETPOINT_RPM"
WRITE_SINGLE_REGISTER_FUNC = 6

MAX_FRAMES_PER_REQUEST = 500

# In-memory state for this demo instance.
STATE = {
    "traffic_bytes": b"",
    "traffic_meta": [],   # generation-time ground truth (label, rpm) per txn id
    "report": [],         # last bridge run's enriched frames
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/physics/config", methods=["GET"])
def api_physics_config():
    cfg = engine.config
    return jsonify({
        "rpm_rated": cfg.rpm_rated,
        "pressure_rated_psi": cfg.pressure_rated_psi,
        "pipe_burst_psi": cfg.pipe_burst_psi,
        "safety_margin": cfg.safety_margin,
        "safety_threshold_psi": round(engine.safety_threshold_psi(), 2),
    })


@app.route("/api/physics/curve", methods=["GET"])
def api_physics_curve():
    """Steady-state pressure curve P(rpm), used to draw the safe/catastrophic
    zones on the dashboard's physics chart."""
    try:
        max_rpm = int(request.args.get("max_rpm", 6000))
    except ValueError:
        max_rpm = 6000
    max_rpm = max(100, min(max_rpm, 100000))

    steps = 60
    points = [
        {
            "rpm": round(max_rpm * i / steps, 1),
            "predicted_psi": round(engine.predict_pressure(max_rpm * i / steps), 2),
        }
        for i in range(steps + 1)
    ]

    return jsonify({
        "points": points,
        "threshold_psi": round(engine.safety_threshold_psi(), 2),
        "pipe_burst_psi": engine.config.pipe_burst_psi,
    })


@app.route("/api/physics/evaluate", methods=["POST"])
def api_physics_evaluate():
    """Live single-command tester -- type in an RPM, see the physics
    firewall's verdict immediately. Mirrors the Mid-Project Review check:
    'prove the engine catches an impossible physics command.'"""
    data = request.get_json(force=True) or {}
    try:
        rpm = float(data.get("rpm"))
    except (TypeError, ValueError):
        return jsonify({"error": "rpm must be a number"}), 400

    return jsonify(engine.evaluate_command(rpm))


@app.route("/api/traffic/generate", methods=["POST"])
def api_generate_traffic():
    """Week 1: generate mock Modbus/TCP traffic (normal + malicious)."""
    data = request.get_json(force=True) or {}

    try:
        num_normal = int(data.get("num_normal", 20))
        num_malicious = int(data.get("num_malicious", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "num_normal / num_malicious must be integers"}), 400

    num_normal = max(0, min(num_normal, MAX_FRAMES_PER_REQUEST))
    num_malicious = max(0, min(num_malicious, MAX_FRAMES_PER_REQUEST))

    if num_normal + num_malicious == 0:
        return jsonify({"error": "Request at least one frame"}), 400

    entries = generate_traffic(num_normal, num_malicious)
    blob = b"".join(e["frame_bytes"] for e in entries)

    STATE["traffic_bytes"] = blob
    STATE["traffic_meta"] = {
        e["transaction_id"]: {"label": e["label"], "rpm": e["rpm"]}
        for e in entries
    }
    STATE["report"] = []

    return jsonify({
        "frame_count": len(entries),
        "byte_count": len(blob),
        "normal": num_normal,
        "malicious": num_malicious,
    })


@app.route("/api/bridge/run", methods=["POST"])
def api_run_bridge():
    """
    Week 2 - Bridge Integration: parse the currently-loaded traffic and
    pass each pump-speed command's RPM into the physics engine's
    simulation API, variable-by-variable, exactly as network_physics_bridge.py
    does for the desktop version.
    """
    if not STATE["traffic_bytes"]:
        return jsonify({"error": "No traffic generated yet. Generate traffic first."}), 400

    try:
        frames = parse_all(STATE["traffic_bytes"])
    except ValueError as e:
        return jsonify({"error": f"Parse error: {e}"}), 400

    enriched = []
    for frame in frames:
        record = dict(frame)
        is_pump_command = (
            frame.get("function_code") == WRITE_SINGLE_REGISTER_FUNC
            and frame.get("register_name") == PUMP_SPEED_REGISTER
        )

        if is_pump_command:
            verdict = engine.evaluate_command(frame["register_value"])
            record.update(verdict)
        else:
            record["verdict"] = "NOT_MODELED"

        ground_truth = STATE["traffic_meta"].get(frame.get("transaction_id"))
        if ground_truth:
            record["generated_label"] = ground_truth["label"]

        enriched.append(record)

    STATE["report"] = enriched

    safe = sum(1 for r in enriched if r["verdict"] == "SAFE")
    catastrophic = sum(1 for r in enriched if r["verdict"] == "CATASTROPHIC")
    not_modeled = sum(1 for r in enriched if r["verdict"] == "NOT_MODELED")

    return jsonify({
        "frames": enriched,
        "summary": {
            "total": len(enriched),
            "safe": safe,
            "catastrophic": catastrophic,
            "not_modeled": not_modeled,
        },
    })


@app.route("/api/bridge/report", methods=["GET"])
def api_get_report():
    return jsonify({"frames": STATE["report"]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
