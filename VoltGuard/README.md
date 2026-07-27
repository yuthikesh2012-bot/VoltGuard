# VoltGuard — Week 1

Physics-Aware ICS/SCADA Intrusion Detection System
**Week 1 milestone:** Protocol Parsing + Physics Modeling (baseline)

## Folder structure

```
VoltGuard_Week1/
├── README.md
├── requirements.txt
├── build.sh                 # builds the C++ parser
├── src/
│   ├── traffic_generator.py # generates mock Modbus/TCP traffic (normal + malicious)
│   ├── modbus_parser.cpp    # C++ parser for Modbus/TCP frames
│   └── physics_model.py     # SciPy baseline pipeline physics model
└── data/
    └── traffic_log.bin      # generated after running traffic_generator.py
```

## Setup

```bash
pip install -r requirements.txt
./build.sh
```

## Run order

1. **Generate mock traffic** (normal + malicious Modbus commands):
   ```bash
   python3 src/traffic_generator.py
   ```
   Writes `data/traffic_log.bin`.

2. **Parse the traffic** with the C++ protocol parser:
   ```bash
   ./modbus_parser data/traffic_log.bin
   ```
   Prints every parsed frame, flagging suspiciously high RPM values.

3. **Run the physics model** standalone to sanity-check the pressure math:
   ```bash
   python3 src/physics_model.py
   ```
   Evaluates sample RPM setpoints (including the 50,000 RPM attack case)
   against the mock pipeline's safety threshold, and shows a transient
   pressure-response simulation.

## Week 1 checkpoints (per project plan)

- [x] Protocol Parsing: C++ script parses mock Modbus/TCP traffic
- [x] Traffic generator: produces normal + malicious industrial commands
- [x] Physics Modeling: baseline fluid/pressure system (SciPy)

**Mid-Project Review readiness:**
- Parsing Audit — parser accurately reads Modbus hex payloads (verified against generator output)
- Simulation Test — physics engine catches an impossible command (e.g. 50,000 RPM → CATASTROPHIC)

## Next (Week 2)

Wire `modbus_parser.cpp`'s output directly into `physics_model.py`'s
`evaluate_command()` so incoming commands are checked against the physics
engine in real time, and begin the native Qt dashboard.
