# VoltGuard — Web Edition (Week 1 + Week 2)

A browser-based version of Project 1, **"VoltGuard": Physics-Aware ICS/SCADA
Intrusion Detection System**, covering the Week 1 and Week 2 milestones from
the project plan.

Standard IT firewalls check whether a packet is syntactically valid Modbus —
not whether the command it carries is physically safe. VoltGuard parses raw
Modbus/TCP traffic and runs every pump-speed command through a physics
simulation before deciding whether it's safe.

## What's implemented (Week 1 + Week 2)

| Week | Deliverable | Where |
|---|---|---|
| 1 | Protocol Parsing — generate + parse Modbus/TCP frames | `traffic_generator.py`, `modbus_parser.py` |
| 1 | Physics Modeling — pump affinity law, safety threshold | `physics_model.py` |
| 2 | Bridge Integration — parser output feeds physics engine | `app.py` → `/api/bridge/run` |
| 2 | Native Dashboard → **Web Dashboard** | `templates/index.html`, `static/` |

This is a **web-application** re-implementation of the original desktop
prototype (C++ parser + Qt dashboard). The Modbus parsing logic is a
line-for-line Python port of the original `modbus_parser.cpp` — same byte
layout, same fields — so the app runs anywhere Python does, with no compiler
or Qt install required. The physics engine (`physics_model.py`) is unchanged
from the original.

Nothing here **drops** traffic yet — the bridge only observes and reports.
Inline blocking (a true IPS, sub-10ms latency) is a Week 3 deliverable per
the original plan.

## Run it

```bash
pip install -r requirements.txt
python3 app.py
```

Then open **http://localhost:5000** in a browser.

## Using the dashboard

1. **Generate Traffic** — pick how many normal vs. malicious frames to
   synthesize (malicious = syntactically valid but physically dangerous RPM
   setpoints, e.g. 50,000 RPM).
2. **Run Bridge → Physics Engine** — parses the raw bytes and runs every
   pump-speed command through `evaluate_command()`. Summary counts and a
   full report table appear, with CATASTROPHIC rows highlighted in red.
3. **Live Command Tester** — type or slide an RPM value straight into the
   physics engine (bypassing the packet layer entirely) and watch the gauge
   and verdict badge respond in real time. This is the same check as the
   plan's Mid-Project Review: "prove the engine catches an impossible
   physics command (e.g., negative valve pressure / 50,000 RPM)."
4. **Pressure vs. RPM chart** — plots the affinity-law curve P(rpm) against
   the safety threshold so you can see exactly where the danger zone begins.

## API reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/traffic/generate` | Body `{num_normal, num_malicious}` → generates and stores mock Modbus traffic |
| `POST` | `/api/bridge/run` | Parses stored traffic, evaluates each pump command via the physics engine |
| `GET`  | `/api/bridge/report` | Returns the last bridge run's enriched frames |
| `POST` | `/api/physics/evaluate` | Body `{rpm}` → single-command physics verdict |
| `GET`  | `/api/physics/curve` | Steady-state P(rpm) curve + safety threshold, for charting |
| `GET`  | `/api/physics/config` | Current pump/pipe physical constants |

## Project structure

```
web/
├── app.py                 # Flask app + Week 2 bridge logic
├── physics_model.py        # Week 1 physics engine (pump affinity law)
├── modbus_parser.py         # Week 1 protocol parser (Python port of modbus_parser.cpp)
├── traffic_generator.py     # Week 1 mock traffic generator
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

## Physics model (unchanged from the desktop version)

A centrifugal pump's affinity laws state pressure scales with the **square**
of rotational speed for fixed geometry:

```
P(rpm) = P_rated * (rpm / rpm_rated) ** 2
```

Default constants (`physics_model.PipelineConfig`):

- `rpm_rated = 1750` RPM
- `pressure_rated_psi = 45` psi at rated RPM
- `pipe_burst_psi = 150` psi (mechanical failure threshold)
- `safety_margin = 0.8` → trips at 120 psi, before the pipe actually bursts

A command is flagged **CATASTROPHIC** if its predicted pressure exceeds the
safety-margined threshold, or if the requested RPM is negative — regardless
of whether the Modbus packet carrying it was perfectly valid syntax.

## Next (Week 3, per the original plan)

- Rewrite the decision logic as a true inline IPS (Rust), holding packets
  until the simulation clears them (sub-10ms latency) instead of only
  reporting after the fact.
- Real-time "predicted vs. actual" state graphs as traffic streams in,
  rather than a static bridge-report run.
