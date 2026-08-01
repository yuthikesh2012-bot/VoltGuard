# VoltGuard

Physics-aware ICS/SCADA intrusion detection system.

## Project variants

| Variant | Location | Status |
|---|---|---|
| Desktop prototype | `desktop/` | Week 2 bridge integration and native Qt dashboard |
| Web application | `web/` | Week 2 bridge integration and browser dashboard |

## Structure

```text
VoltGuard/
├── README.md
├── desktop/
│   ├── README.md
│   ├── build.sh
│   ├── requirements.txt
│   ├── src/
│   └── dashboard/
└── web/
    ├── README.md
    ├── requirements.txt
    ├── app.py
    ├── modbus_parser.py
    ├── traffic_generator.py
    ├── physics_model.py
    ├── templates/
    └── static/
```

## Run the web application

```bash
cd web
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in a browser.

## Build the desktop prototype

```bash
cd desktop
./build.sh
```

The desktop build requires a C++17 compiler and Qt with `qmake` or `qmake6`.
See `desktop/README.md` for the native dashboard workflow.
