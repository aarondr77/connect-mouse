# Project 3 — Joystick mouse + ultrasonic click

Control the Mac cursor with a **joystick** and left-click via **ultrasonic proximity**. All sensor data comes from the **LabJack**; one Python script handles streaming and optional mouse control.

## Tabs

| Tab | Purpose |
|-----|---------|
| **Home** | This page — overview and workflow |
| **Live** | Run the script, toggle mouse control, tune sliders, watch plots |
| **Tests** | Automated wiring/sensor checks (stop the Live script first) |

## Quick start

1. Open **Live** → click **Run** on *Project 3 — Mouse control* (streams sensors; mouse stays off).
2. Move the stick and wave a hand — confirm plots update (joystick volts, **mouse dx/dy**, distance).
3. Flip **Mouse control on** when you want cursor movement and proximity clicks.
4. Tune speed, dead zone, and click thresholds with the sliders (live, no restart). Joystick plots show **dead_lo** / **dead_hi** lines that track the dead-zone slider (2.5 V ± dead zone).

**Keyboard toggle:** While the script is running, press **⌘⇧M** (Cmd+Shift+M) to turn mouse control on or off — useful if the cursor drifts and you cannot click the toggle.

**macOS:** Grant **Accessibility** to Nominal Connect for mouse control and the hotkey.
