# NSI First Mini Project

Overview
--------

This repository contains two main parts:

- Server (host-side) code in the `Dektop/` folder — a small Python serial manager that communicates with devices over USB serial.
- Embedded device firmware in the `src/` folder — a PlatformIO/Arduino project targeting a TTGO ESP32 board.

Supported platforms
-------------------

- Host: Windows (tested), macOS/Linux should also work with correct serial device names.
- Device: ESP32 (environment defined in `platformio.ini`).

Part A — Server (Dektop)
------------------------

Location: `Dektop/server.py`

Purpose: scan for connected Silabs CP210x serial devices, send control/keep-alive commands, request temperature data, and set RGB colors based on temperature.

Dependencies
- Python 3.8+ (3.10 recommended)
- Python package: `pyserial` (used for `serial` and `serial.tools.list_ports`)

Quick start (from project root)

1. Create a virtual environment (optional):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependency:

```powershell
pip install pyserial
```

3. Run the server:

```powershell
python Dektop/server.py
```

Notes
- The script auto-scans for serial ports whose description/manufacturer/hwid contains `silicon`, `silabs` or `cp210`.
- Configure communication parameters at the top of `Dektop/server.py` (baud, timeouts, command list).

Part B — Embedded firmware (PlatformIO)
--------------------------------------

Location: `src/` (main sketch: `src/main.cpp`), configuration: `platformio.ini`

PlatformIO environment (from `platformio.ini`)

- Environment: `ttgo-t7-v13-mini32`
- Platform: `espressif32`
- Board: `ttgo-t7-v13-mini32`
- Framework: `arduino`
- Libraries (`lib_deps`):
	- adafruit/Adafruit Unified Sensor
	- adafruit/DHT sensor library

Install PlatformIO
- Install PlatformIO Core (CLI) or the PlatformIO VS Code extension.

Build & upload

```powershell
platformio run
platformio run --target upload --upload-port COM9
```

Replace `COM9` with the correct serial port for your board.

Project structure
-----------------

- `platformio.ini` — PlatformIO configuration and `lib_deps`
- `src/main.cpp` — Embedded firmware
- `include/` — Header files
- `lib/` — Local libraries (if any)
- `Dektop/` — Host/server code and notes
- `test/` — Tests and test-related files

Wiring / Pin connections
------------------------

These are the GPIO pins used by the firmware (`src/main.cpp`). Wire your hardware accordingly:

- DHT11 sensor:
	- Data -> GPIO0 (`DHT_PIN`)
	- VCC  -> 3.3V
	- GND  -> GND
- RGB LED (PWM channels):
	- Red   -> GPIO27 (`LED_R_PIN`)
	- Green -> GPIO25 (`LED_G_PIN`)
	- Blue  -> GPIO32 (`LED_B_PIN`)
	- Note: firmware inverts PWM values (uses `255 - value`), so it expects wiring where the MCU *sinks* current (common-anode RGB or LED anodes to 3.3V through resistors). Use transistors or MOSFETs for high-current LEDs and always include current-limiting resistors.
- Keep-alive LED / indicator:
	- LED (with series resistor) -> 3.3V (anode)
	- LED cathode -> GPIO4 (`KEEP_ALIVE_PIN`) (firmware pulses LOW to light)

General notes:

- Share a common ground between the ESP32 and sensors/peripherals.
- Use 3.3V-powered sensors; do not power DHT11 data line from 5V when directly connected to ESP32 pins.
- If unsure, consult `src/main.cpp` for the definitive pin constants.

Notes & Troubleshooting
-----------------------

- If the host script cannot find your board, list available ports with:

```powershell
python -c "import serial.tools.list_ports as p; print(list(p.comports()))"
```

- For Windows, use Device Manager to identify the COM port. On Unix-like systems, look for `/dev/ttyUSB*` or `/dev/ttyACM*`.
- Keep `platformio.ini` `lib_deps` in sync with any libraries referenced by `src/main.cpp`.

Further improvements
--------------------

- Add a `requirements.txt` in `Dektop/` listing `pyserial` for reproducible installs.
- Add a `README.md` inside `Dektop/` describing host usage and configuration options.

License
-------

This project is released under the MIT License — see the `LICENSE` file for details.