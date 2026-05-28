"""
Project 2: LabJack enables an Arduino "plant"; Nominal Connect commands and streams data.

Connect UI: configure a checkbox/toggle with a message-bus action (see project2/README.md §6).

Wiring summary:
  - Common GND: LabJack GND ↔ Arduino GND ↔ joystick GND
  - LabJack FIO4 → Arduino D2 (enable) — T4 screw terminals are FIO4–FIO7, not FIO0
  - Joystick +5V → Arduino 5V; VRx → Arduino A0 and LabJack AIN0
"""

import time
from datetime import datetime, timezone
from typing import Any

import connect_python

# LabJack T4 screw terminals are labeled FIO4, FIO5, FIO6, FIO7 (not FIO0).
ENABLE_LABJACK_LINE = "FIO4"

# Must match the checkbox/toggle "on toggle" message topic in Connect (README §6).
SYSTEM_ON_TOPIC = "script/project2/system_on"

from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver
from nominal_instro.instruments.daq import NominalDAQ
from nominal_instro.instruments.daq.types import Direction, Logic

logger = connect_python.get_logger(__name__)

SAMPLE_INTERVAL_S = 0.25
DURATION_SECONDS = 300.0  # 5 minutes; stop script in Connect UI when done


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
    """Read on/off from a UI toggle message (see Nominal message bus docs)."""
    for key in ("enabled", "checked", "on", "value"):
        if key in contents:
            return as_bool(contents[key], current)
    if contents.get("widget_id") == "system_on":
        return not current
    return current


@connect_python.main
def main(client: connect_python.Client):
    logger.info("Project 2: Arduino plant — starting")

    daq = NominalDAQ(
        name="labjack_t4",
        driver=LabJackTSeriesDriver(device_id="ANY"),
    )
    daq.open()

    # Digital out: drives Arduino D2 (enable)
    daq.configure_digital_channel(
        direction=Direction.OUTPUT,
        physical_channel=ENABLE_LABJACK_LINE,
        logic=Logic.HIGH,
        alias="enable_out",
    )

    # Analog in: reads joystick VRx (0–5 V)
    daq.configure_analog_channel(
        direction=Direction.INPUT,
        physical_channel="AIN0",
        alias="joystick_voltage",
        range_min=-10.0,
        range_max=10.0,
    )

    client.clear_stream("system_on")
    client.clear_stream("joystick_voltage")
    client.clear_stream("enable_out")

    last_enable: int | None = None
    start = time.monotonic()
    sample_count = 0
    system_on = False

    try:
        with connect_python.MessageBus(client) as message_bus:
            message_bus.subscribe_to_topic(SYSTEM_ON_TOPIC)
            logger.info("Listening for UI toggles on topic %s", SYSTEM_ON_TOPIC)

            while time.monotonic() - start < DURATION_SECONDS:
                message = message_bus.try_receive_message()
                while message is not None:
                    if message.topic.startswith(SYSTEM_ON_TOPIC):
                        system_on = system_on_from_message(message.contents, system_on)
                        logger.info("UI message: %s", message.contents)
                    message = message_bus.try_receive_message()

                # Fallback if the widget also exposes a Connect variable named system_on
                ui_value = client.get_value("system_on")
                if ui_value is not None:
                    system_on = as_bool(ui_value, system_on)

                enable_bit = 1 if system_on else 0

                if enable_bit != last_enable:
                    daq.write_digital_line("enable_out", enable_bit)
                    logger.info(
                        "System %s (%s=%s)",
                        "ON" if system_on else "OFF",
                        ENABLE_LABJACK_LINE,
                        enable_bit,
                    )
                    last_enable = enable_bit

                measurement = daq.read_analog()
                voltage = measurement.values[0]
                t = datetime.now(timezone.utc)

                client.stream("system_on", t, float(enable_bit), name="value")
                client.stream("joystick_voltage", t, voltage, name="value", unit="V")
                client.stream("enable_out", t, float(enable_bit), name="value")

                sample_count += 1
                time.sleep(SAMPLE_INTERVAL_S)

            logger.info("Done. Streamed %s samples.", sample_count)
    finally:
        daq.write_digital_line("enable_out", 0)
        daq.close()
        logger.info("LabJack closed; %s driven LOW.", ENABLE_LABJACK_LINE)


if __name__ == "__main__":
    main()
