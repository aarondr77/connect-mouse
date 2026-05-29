# Project 3 — Automated tests (TestWorkflow)

Bench acceptance tests for LabJack joystick + ultrasonic sensing. Connect runs each `test_*` method and shows pass/fail in the UI.

## Before you start

1. Upload [`sensor_node/sensor_node.ino`](sensor_node/sensor_node.ino) to the Arduino UNO (enable LED only — no serial telemetry).
2. Complete wiring per [`README.md`](README.md) (joystick on **AIN0/AIN1**, HC-SR04 on **FIO5/FIO6**, Echo divider on **FIO6**).
3. **Stop** `mouse-control.py` before running tests — only one script should use the LabJack at a time.

## How this differs from `mouse-control.py`

| | `mouse-control.py` | `mouse_tests.py` |
|---|-------------------|------------------|
| **Purpose** | Live streaming plots | One-shot wiring/sensor checklist |
| **Runs** | Loop until you stop | Fixed tests, then done |
| **Verdict** | You eyeball plots | `assert` → pass or fail |

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
/Users/aarondiamond-reivich/Nominal/projects/project3/mouse_tests.py
```

If the run finishes instantly with only `Starting script`, Connect is pointing at a stub file.

## Streaming script

1. Open [`app.connect`](app.connect) in Nominal Connect.
2. Run **Project 3 — Stream sensors**.
3. Move the joystick and wave a hand in front of the HC-SR04 — **joystick_x**, **joystick_y**, and **distance** plots should update.

All sensor data comes from the **LabJack** (not USB serial). The Arduino only mirrors **FIO4 → D2** for the pin-13 LED.

## Deferred (not in this build)

- Mouse cursor movement (`pynput`)
- Proximity click on the Mac
- `click` stream

See [`README.md`](README.md) Phase D for when you add those.
