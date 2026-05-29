"""
Project 3: stream joystick + ultrasonic from LabJack only (Nominal Connect).

Wiring: see project3/README.md
  - LabJack AIN0/AIN1 ← VRx/VRy; FIO4 → Arduino D2 (enable); FIO5/FIO6 ← HC-SR04
  - Arduino runs sensor_node.ino for enable LED only (no USB telemetry)

Mouse movement and proximity click are deferred; this script only streams sensor data.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

import connect_python

logger = connect_python.get_logger(__name__)

ENABLE_LABJACK_LINE = "FIO4"
TRIG_LINE = "FIO5"
ECHO_LINE = "FIO6"
SYSTEM_ON_TOPIC = "script/project3/system_on"

SAMPLE_INTERVAL_S = 0.05  # ~20 Hz
DURATION_SECONDS = 3600.0

DISTANCE_MIN_CM = 2.0
DISTANCE_MAX_CM = 400.0


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


def system_on_from_message(contents: dict[str, Any], current: bool) -> bool:
    for key in ("enabled", "checked", "on", "value"):
        if key in contents:
            return as_bool(contents[key], current)
    if contents.get("widget_id") == "system_on":
        return not current
    return current


def is_valid_distance_cm(value: float) -> bool:
    return math.isfinite(value) and DISTANCE_MIN_CM <= value <= DISTANCE_MAX_CM


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
        vx = float(self._ljm.eReadName(self._handle, "AIN0"))
        vy = float(self._ljm.eReadName(self._handle, "AIN1"))
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


@connect_python.main
def main(client: connect_python.Client):
    logger.info("Project 3: mouse-control (LabJack streaming) — starting")

    labjack = LabJackBench()
    labjack.open()

    stream_names = [
        "system_on",
        "enable_out",
        "joystick_x",
        "joystick_y",
        "distance",
    ]
    for name in stream_names:
        client.clear_stream(name)

    last_enable: int | None = None
    start = time.monotonic()
    sample_count = 0
    system_on = False

    try:
        with connect_python.MessageBus(client) as message_bus:
            message_bus.subscribe_to_topic(SYSTEM_ON_TOPIC)

            while time.monotonic() - start < DURATION_SECONDS:
                message = message_bus.try_receive_message()
                while message is not None:
                    if message.topic.startswith(SYSTEM_ON_TOPIC):
                        system_on = system_on_from_message(message.contents, system_on)
                    message = message_bus.try_receive_message()

                ui_value = client.get_value("system_on")
                if ui_value is not None:
                    system_on = as_bool(ui_value, system_on)

                enable_bit = 1 if system_on else 0
                if enable_bit != last_enable:
                    labjack.set_enable(bool(enable_bit))
                    last_enable = enable_bit

                vx, vy = labjack.read_joystick_volts()
                distance = labjack.read_distance_cm()

                t = datetime.now(timezone.utc)
                client.stream("system_on", t, float(enable_bit), name="value")
                client.stream("enable_out", t, float(enable_bit), name="value")
                client.stream("joystick_x", t, vx, name="value", unit="V")
                client.stream("joystick_y", t, vy, name="value", unit="V")
                client.stream("distance", t, distance, name="value", unit="cm")

                sample_count += 1
                time.sleep(SAMPLE_INTERVAL_S)

            logger.info("Done. Streamed %s samples.", sample_count)
    finally:
        labjack.close()
        logger.info("LabJack closed; %s driven LOW.", ENABLE_LABJACK_LINE)


if __name__ == "__main__":
    main()
