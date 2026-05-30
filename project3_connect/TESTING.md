# Project 3 — Automated tests (TestWorkflow)

Bench acceptance tests for LabJack joystick + ultrasonic sensing. Connect runs each `test_*` method and shows pass/fail in the UI.

## Before you start

1. Upload [`sensor_node/sensor_node.ino`](sensor_node/sensor_node.ino) to the Arduino UNO (enable LED only — no serial telemetry).
2. Complete wiring per [`README.md`](README.md) (joystick on **AIN0/AIN1**, HC-SR04 on **FIO5/FIO6**, Echo divider on **FIO6**).
3. **Stop** `mouse-control.py` before running tests — only one script should use the LabJack at a time.

## How this differs from `mouse-control.py`

| | `mouse-control.py` | `mouse_tests.py` |
|---|-------------------|------------------|
| **Purpose** | Live streaming + mouse/click when armed | One-shot wiring/sensor checklist |
| **Runs** | Loop until you stop | Fixed tests, then done |
| **Verdict** | You eyeball plots + cursor behavior | `assert` → pass or fail |

## Tests included

| Test | What it checks |
|------|----------------|
| `test_labjack_joystick_x_not_on_rail` | **AIN0** not stuck at 0 V or 5 V (centered) |
| `test_labjack_joystick_y_not_on_rail` | **AIN1** same |
| `test_joystick_x_motion` | Move stick X; voltage span > 0.1 V |
| `test_joystick_y_motion` | Move stick Y; span > 0.1 V |
| `test_ultrasonic_in_range` | **FIO5/FIO6** distance in 2–400 cm |
| `test_enable_off_after_tests` | **FIO4** left low |

## Wrong script path

The Test Workflow path must be:

```
/Users/aarondiamond-reivich/Nominal/projects/project3_connect/mouse_tests.py
```

If the run finishes instantly with only `Starting script`, Connect is pointing at a stub file.

## Mouse control script

1. Open [`app.connect`](app.connect) in Nominal Connect → **Live** tab.
2. Run **Project 3 — Mouse control**.
3. Move the joystick and wave a hand in front of the HC-SR04 — **joystick_x**, **joystick_y**, and **distance** plots should update.

All sensor data comes from the **LabJack** (not USB serial). The Arduino only mirrors **FIO4 → D2** for the pin-13 LED.

### macOS Accessibility (one-time)

Before cursor/click work, grant **Accessibility** permission:

**System Settings → Privacy & Security → Accessibility** → enable Nominal Connect (or the Python binary shown in the script log).

### Manual mouse + click checklist

1. Run the script on the **Live** tab; confirm sensor plots live.
2. Leave **Mouse control on** off — move stick and wave hand → **no** cursor move or Mac click; plots still update.
3. Turn **Mouse control on** — move stick → cursor moves; centered stick stops movement.
4. Adjust **Mouse speed (px/V)** (default 80) and **Dead zone (V)** sliders live — feel changes without restart.
5. Wave hand into ultrasonic range → one left-click per approach; **click** plot spikes to 1.
6. Tune **Near/Far threshold** and **Click stable (ms)** if you get double-clicks or misses.
7. Turn **Mouse control on** off → cursor and clicks stop; Arduino LED blinks again.

Connect UI tuning widgets (read live by the script):

| Widget id | Default | Purpose |
|-----------|---------|---------|
| `mouse_speed` | 80 px/V | Cursor speed |
| `dead_zone_v` | 0.2 V | Ignore stick noise near center |
| Y axis | (fixed in script) | Stick up → cursor up |
| `near_cm` | 15 cm | Enter proximity zone |
| `far_cm` | 22 cm | Leave proximity zone (hysteresis) |
| `stable_ms` | 100 ms | Hold near before click fires |
