"""
Project 3: joystick mouse + ultrasonic proximity click (Nominal Connect).

Wiring: see project3/README.md
  - LabJack AIN0/AIN1 ← VRx/VRy; FIO4 → Arduino D2 (enable); FIO5/FIO6 ← HC-SR04
  - Arduino runs sensor_node.ino for enable LED only (no USB telemetry)

While the script runs, sensor data always streams. Toggle mouse_control_on in
Connect to arm FIO4, move the cursor, and fire proximity left-clicks.
Tune live via Connect UI sliders.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import connect_python

logger = connect_python.get_logger(__name__)

ENABLE_LABJACK_LINE = "FIO4"
TRIG_LINE = "FIO5"
ECHO_LINE = "FIO6"
MOUSE_CONTROL_TOPIC = "script/project3/mouse_control_on"
# Global mouse-control toggle (macOS). Requires Accessibility for pynput.
MOUSE_CONTROL_HOTKEY = "<cmd>+<shift>+m"

# Bench wiring: VRx (stick left/right) → AIN1, VRy (stick up/down) → AIN0.
JOYSTICK_X_CHANNEL = "AIN1"
JOYSTICK_Y_CHANNEL = "AIN0"

SAMPLE_INTERVAL_S = 0.05  # ~20 Hz
DURATION_SECONDS = 3600.0

DISTANCE_MIN_CM = 2.0
DISTANCE_MAX_CM = 400.0

JOYSTICK_CENTER_V = 2.5
DEFAULT_DEAD_ZONE_V = 0.2
DEFAULT_MOUSE_SPEED = 80.0  # px/V
DEFAULT_NEAR_CM = 15.0
DEFAULT_FAR_CM = 22.0
DEFAULT_STABLE_MS = 100.0


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "on", "yes")
    return bool(value)


def as_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bool_from_message(
    contents: dict[str, Any], current: bool, *, widget_id: str
) -> bool:
    for key in ("enabled", "checked", "on", "value"):
        if key in contents:
            return as_bool(contents[key], current)
    if contents.get("widget_id") == widget_id:
        return not current
    return current


def is_valid_distance_cm(value: float) -> bool:
    return math.isfinite(value) and DISTANCE_MIN_CM <= value <= DISTANCE_MAX_CM


def dead_zone_bounds(
    dead_zone_v: float, center_v: float = JOYSTICK_CENTER_V
) -> tuple[float, float]:
    """Lower/upper voltage limits of the no-move band (for plot reference lines)."""
    dz = max(0.0, dead_zone_v)
    return center_v - dz, center_v + dz


class MouseMapper:
    """Map joystick voltages to relative cursor pixel deltas."""

    def __init__(self, center_v: float = JOYSTICK_CENTER_V) -> None:
        self._center_v = center_v

    def deltas(
        self,
        vx: float,
        vy: float,
        *,
        dead_zone_v: float,
        mouse_speed: float,
    ) -> tuple[int, int]:
        dx = self._axis_delta(vx, dead_zone_v, mouse_speed)
        # Bench VRy: higher voltage when stick is up → negative screen dy (cursor up).
        dy = -self._axis_delta(vy, dead_zone_v, mouse_speed)
        return dx, dy

    def _axis_delta(self, voltage: float, dead_zone_v: float, mouse_speed: float) -> int:
        if not math.isfinite(voltage):
            return 0
        delta_v = voltage - self._center_v
        if abs(delta_v) < dead_zone_v:
            return 0
        return int(round(delta_v * mouse_speed))


class ProximityClick:
    """Fire one left-click per approach into the near zone (hysteresis + debounce)."""

    def __init__(self) -> None:
        self._was_near = False
        self._near_since: float | None = None

    def update(
        self,
        distance_cm: float,
        *,
        near_cm: float,
        far_cm: float,
        stable_ms: float,
        now: float,
    ) -> bool:
        """Return True when a click should fire this sample."""
        if not is_valid_distance_cm(distance_cm):
            return False

        near = distance_cm < near_cm
        far = distance_cm > far_cm

        if near:
            if self._near_since is None:
                self._near_since = now
            stable = (now - self._near_since) >= (stable_ms / 1000.0)
            should_click = near and stable and not self._was_near
        else:
            self._near_since = None
            should_click = False

        self._was_near = near if near else (self._was_near and not far)
        return should_click


class MouseControlHotkey:
    """Global hotkey to toggle mouse control without using the cursor."""

    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._hotkeys: Any = None

    def start(self) -> None:
        try:
            from pynput import keyboard

            self._hotkeys = keyboard.GlobalHotKeys(
                {MOUSE_CONTROL_HOTKEY: self._on_toggle}
            )
            self._hotkeys.start()
            logger.info(
                "Mouse control hotkey: press Cmd+Shift+M to toggle on/off"
            )
        except Exception as exc:
            logger.warning("Mouse control hotkey unavailable: %s", exc)

    def stop(self) -> None:
        if self._hotkeys is None:
            return
        try:
            self._hotkeys.stop()
        except Exception:
            pass
        self._hotkeys = None


class MacMouse:
    """pynput wrapper for relative move + left click."""

    def __init__(self) -> None:
        self._controller: Any = None
        self._available = False
        self._warned = False
        self._init_controller()

    def _init_controller(self) -> None:
        try:
            from pynput.mouse import Button, Controller

            self._controller = Controller()
            self._button = Button
            self._available = True
            logger.info(
                "Mouse control ready (pynput). Grant Accessibility permission "
                "in System Settings if cursor/click do not respond."
            )
        except Exception as exc:
            self._available = False
            logger.warning("Mouse control unavailable: %s", exc)

    def move(self, dx: int, dy: int) -> None:
        if not self._available or (dx == 0 and dy == 0):
            return
        try:
            self._controller.move(dx, dy)
        except Exception as exc:
            if not self._warned:
                logger.warning(
                    "Mouse move failed (check Accessibility permission): %s", exc
                )
                self._warned = True

    def click_left(self) -> None:
        if not self._available:
            return
        try:
            self._controller.click(self._button.left)
        except Exception as exc:
            if not self._warned:
                logger.warning(
                    "Mouse click failed (check Accessibility permission): %s", exc
                )
                self._warned = True


class LabJackBench:
    """Single labjack-ljm handle for analog, enable, and HC-SR04."""

    def __init__(self) -> None:
        self._ljm: Any = None
        self._handle: int | None = None

    def open(self) -> None:
        from labjack import ljm

        self._ljm = ljm
        self._handle = ljm.openS("T4", "USB", "ANY")
        ljm.eWriteName(self._handle, ENABLE_LABJACK_LINE, 0)

    def close(self) -> None:
        if self._ljm is not None and self._handle is not None:
            try:
                self._ljm.eWriteName(self._handle, ENABLE_LABJACK_LINE, 0)
                self._ljm.close(self._handle)
            except Exception:
                pass
        self._handle = None

    def set_enable(self, on: bool) -> None:
        if self._handle is None:
            return
        self._ljm.eWriteName(self._handle, ENABLE_LABJACK_LINE, 1 if on else 0)

    def read_joystick_volts(self) -> tuple[float, float]:
        if self._handle is None:
            return math.nan, math.nan
        vx = float(self._ljm.eReadName(self._handle, JOYSTICK_X_CHANNEL))
        vy = float(self._ljm.eReadName(self._handle, JOYSTICK_Y_CHANNEL))
        return vx, vy

    def read_distance_cm(self) -> float:
        if self._handle is None:
            return math.nan
        ljm = self._ljm
        handle = self._handle
        try:
            ljm.eWriteName(handle, TRIG_LINE, 0)
            time.sleep(0.000002)
            ljm.eWriteName(handle, TRIG_LINE, 1)
            time.sleep(0.00001)
            ljm.eWriteName(handle, TRIG_LINE, 0)

            deadline = time.perf_counter() + 0.03
            while ljm.eReadName(handle, ECHO_LINE) == 0:
                if time.perf_counter() >= deadline:
                    return math.nan
            t_high = time.perf_counter()
            while ljm.eReadName(handle, ECHO_LINE) == 1:
                if time.perf_counter() >= deadline:
                    return math.nan
            pulse_s = time.perf_counter() - t_high
            distance_cm = pulse_s * 1e6 * 0.034 / 2.0
            if not is_valid_distance_cm(distance_cm):
                return math.nan
            return distance_cm
        except Exception as exc:
            logger.debug("Ultrasonic read failed: %s", exc)
            return math.nan


def read_tuning(client: connect_python.Client) -> dict[str, float | bool]:
    near_cm = as_float(client.get_value("near_cm"), DEFAULT_NEAR_CM)
    far_cm = as_float(client.get_value("far_cm"), DEFAULT_FAR_CM)
    if far_cm <= near_cm:
        far_cm = near_cm + 2.0
    return {
        "dead_zone_v": as_float(client.get_value("dead_zone_v"), DEFAULT_DEAD_ZONE_V),
        "mouse_speed": as_float(client.get_value("mouse_speed"), DEFAULT_MOUSE_SPEED),
        "near_cm": near_cm,
        "far_cm": far_cm,
        "stable_ms": as_float(client.get_value("stable_ms"), DEFAULT_STABLE_MS),
    }


@connect_python.main
def main(client: connect_python.Client):
    logger.info("Project 3: mouse-control — starting")

    labjack = LabJackBench()
    labjack.open()
    mouse = MacMouse()
    mapper = MouseMapper()
    proximity = ProximityClick()

    stream_names = [
        "mouse_control_on",
        "enable_out",
        "joystick_x",
        "joystick_y",
        "distance",
        "mouse_dx",
        "mouse_dy",
        "click",
        "near_state",
    ]
    for name in stream_names:
        client.clear_stream(name)

    last_enable: int | None = None
    start = time.monotonic()
    sample_count = 0
    mouse_control_on = False

    def toggle_mouse_control() -> None:
        nonlocal mouse_control_on, last_enable
        mouse_control_on = not mouse_control_on
        labjack.set_enable(mouse_control_on)
        last_enable = 1 if mouse_control_on else 0
        try:
            client.set_value("mouse_control_on", mouse_control_on)
        except Exception as exc:
            logger.debug("Could not sync UI toggle: %s", exc)
        state = "ON" if mouse_control_on else "OFF"
        logger.info("Mouse control %s (keyboard: Cmd+Shift+M)", state)

    hotkey = MouseControlHotkey(toggle_mouse_control)
    hotkey.start()

    try:
        with connect_python.MessageBus(client) as message_bus:
            message_bus.subscribe_to_topic(MOUSE_CONTROL_TOPIC)

            while time.monotonic() - start < DURATION_SECONDS:
                message = message_bus.try_receive_message()
                while message is not None:
                    if message.topic.startswith(MOUSE_CONTROL_TOPIC):
                        mouse_control_on = bool_from_message(
                            message.contents, mouse_control_on, widget_id="mouse_control_on"
                        )
                    message = message_bus.try_receive_message()

                ui_value = client.get_value("mouse_control_on")
                if ui_value is not None:
                    mouse_control_on = as_bool(ui_value, mouse_control_on)

                enable_bit = 1 if mouse_control_on else 0
                if enable_bit != last_enable:
                    labjack.set_enable(bool(enable_bit))
                    last_enable = enable_bit

                tuning = read_tuning(client)
                vx, vy = labjack.read_joystick_volts()
                distance = labjack.read_distance_cm()

                dead_zone_v = float(tuning["dead_zone_v"])
                dead_lo, dead_hi = dead_zone_bounds(dead_zone_v)

                dx, dy = mapper.deltas(
                    vx,
                    vy,
                    dead_zone_v=dead_zone_v,
                    mouse_speed=float(tuning["mouse_speed"]),
                )

                now = time.monotonic()
                near_state = (
                    1.0
                    if is_valid_distance_cm(distance)
                    and distance < float(tuning["near_cm"])
                    else 0.0
                )
                click_value = 0.0
                if mouse_control_on:
                    if dx != 0 or dy != 0:
                        mouse.move(dx, dy)
                    if proximity.update(
                        distance,
                        near_cm=float(tuning["near_cm"]),
                        far_cm=float(tuning["far_cm"]),
                        stable_ms=float(tuning["stable_ms"]),
                        now=now,
                    ):
                        mouse.click_left()
                        click_value = 1.0
                        logger.info("Proximity click (distance=%.1f cm)", distance)

                t = datetime.now(timezone.utc)
                client.stream("mouse_control_on", t, float(enable_bit), name="value")
                client.stream("enable_out", t, float(enable_bit), name="value")
                client.stream_from_dict(
                    "joystick_x",
                    t,
                    channel_map={"value": vx, "dead_lo": dead_lo, "dead_hi": dead_hi},
                )
                client.stream_from_dict(
                    "joystick_y",
                    t,
                    channel_map={"value": vy, "dead_lo": dead_lo, "dead_hi": dead_hi},
                )
                client.stream("distance", t, distance, name="value", unit="cm")
                client.stream("mouse_dx", t, float(dx), name="value", unit="px")
                client.stream("mouse_dy", t, float(dy), name="value", unit="px")
                client.stream("click", t, click_value, name="value")
                client.stream("near_state", t, near_state, name="value")

                sample_count += 1
                time.sleep(SAMPLE_INTERVAL_S)

            logger.info("Done. Streamed %s samples.", sample_count)
    finally:
        hotkey.stop()
        labjack.close()
        logger.info("LabJack closed; %s driven LOW.", ENABLE_LABJACK_LINE)


if __name__ == "__main__":
    main()
