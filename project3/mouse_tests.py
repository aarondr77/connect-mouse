"""
Automated acceptance tests for Project 3 (LabJack joystick + ultrasonic).

Run from Nominal Connect via Test Workflow (see project3/TESTING.md).
Stop mouse-control.py before running — both need the LabJack.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime, timezone

import connect_python
from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver
from nominal_instro.instruments.daq import NominalDAQ
from nominal_instro.instruments.daq.types import Direction, Logic

ENABLE_LABJACK_LINE = "FIO4"

RAIL_HIGH_V = 4.85
RAIL_LOW_V = 0.15
CENTERED_TYPICAL_MIN_V = 0.3
CENTERED_TYPICAL_MAX_V = 4.7

VOLTAGE_MIN_V = -0.5
VOLTAGE_MAX_V = 5.5
SWEEP_MIN_DELTA_V = 0.10
SWEEP_SAMPLE_COUNT = 24
SWEEP_SECONDS = 10.0
HOLD_STILL_SECONDS = 2.0
DISTANCE_MIN_CM = 2.0
DISTANCE_MAX_CM = 400.0


def _rail_wiring_hint(voltage: float, channel: str) -> str:
    if voltage >= RAIL_HIGH_V:
        return (
            f"{channel} reads {voltage:.3f} V (~5 V power rail). "
            "Signal row may be tied to +5V instead of VRx/VRy."
        )
    if voltage <= RAIL_LOW_V:
        return (
            f"{channel} reads {voltage:.3f} V (~GND). "
            "Signal row may be tied to ground instead of VRx/VRy."
        )
    return ""


class MouseTests(connect_python.TestWorkflow):
    """Bench tests for Project 3 LabJack wiring."""

    def start_workflow(self, client: connect_python.Client) -> None:
        self.daq = NominalDAQ(
            name="labjack_t4",
            driver=LabJackTSeriesDriver(device_id="ANY"),
        )
        self.daq.open()
        self._configure_channels()
        self.add_cleanup(self._shutdown)
        self.addComment("LabJack connected.")

    def _configure_channels(self) -> None:
        self.daq.configure_digital_channel(
            direction=Direction.OUTPUT,
            physical_channel=ENABLE_LABJACK_LINE,
            logic=Logic.HIGH,
            alias="enable_out",
        )
        self.daq.configure_analog_channel(
            direction=Direction.INPUT,
            physical_channel="AIN0",
            alias="joystick_x",
            range_min=-10.0,
            range_max=10.0,
        )
        self.daq.configure_analog_channel(
            direction=Direction.INPUT,
            physical_channel="AIN1",
            alias="joystick_y",
            range_min=-10.0,
            range_max=10.0,
        )

    def _shutdown(self) -> None:
        self.daq.write_digital_line("enable_out", 0)
        self.daq.close()

    def _read_voltages(self) -> tuple[float, float]:
        measurement = self.daq.read_analog()
        values = list(measurement.values)
        if len(values) >= 2:
            return float(values[0]), float(values[1])
        if len(values) == 1:
            return float(values[0]), math.nan
        return math.nan, math.nan

    def _set_enable(self, on: bool) -> None:
        self.daq.write_digital_line("enable_out", 1 if on else 0)
        time.sleep(0.15)

    def _sample_axis(
        self,
        axis: str,
        count: int,
        duration_s: float,
        *,
        stream: bool = False,
        on_sample: Callable[[int, int, float], None] | None = None,
    ) -> list[float]:
        interval = duration_s / count if count else duration_s
        readings: list[float] = []
        stream_id = "joystick_x" if axis == "x" else "joystick_y"
        for i in range(count):
            vx, vy = self._read_voltages()
            voltage = vx if axis == "x" else vy
            readings.append(voltage)
            if stream:
                t = datetime.now(timezone.utc)
                self.client.stream(stream_id, t, voltage, name="value", unit="V")
            if on_sample is not None:
                on_sample(i + 1, count, voltage)
            time.sleep(interval)
        return readings

    def _assert_not_on_rail(self, voltage: float, channel: str) -> None:
        self.assertGreaterEqual(voltage, VOLTAGE_MIN_V)
        self.assertLessEqual(voltage, VOLTAGE_MAX_V)
        hint = _rail_wiring_hint(voltage, channel)
        self.assertFalse(hint, hint or f"Unexpected {channel}={voltage:.3f} V")
        self.assertGreaterEqual(
            voltage,
            CENTERED_TYPICAL_MIN_V,
            f"{channel}={voltage:.3f} V stuck near 0 V — check wiper wiring.",
        )
        self.assertLessEqual(
            voltage,
            CENTERED_TYPICAL_MAX_V,
            f"{channel}={voltage:.3f} V stuck near 5 V — check signal row vs +5V.",
        )

    def test_labjack_joystick_x_not_on_rail(self) -> None:
        """AIN0 (X) is not pegged at 0 V or 5 V with stick centered."""
        self._set_enable(False)
        vx, _ = self._read_voltages()
        self.addComment(f"AIN0 (X) = {vx:.3f} V (centered)")
        self._assert_not_on_rail(vx, "AIN0")

    def test_labjack_joystick_y_not_on_rail(self) -> None:
        """AIN1 (Y) is not pegged at 0 V or 5 V with stick centered."""
        self._set_enable(False)
        _, vy = self._read_voltages()
        self.addComment(f"AIN1 (Y) = {vy:.3f} V (centered)")
        self._assert_not_on_rail(vy, "AIN1")

    def _sweep_axis(self, axis: str, label: str) -> None:
        self._set_enable(True)
        channel = "AIN0" if axis == "x" else "AIN1"
        stream_id = "joystick_x" if axis == "x" else "joystick_y"
        self.client.clear_stream(stream_id)

        hold = f"Hold stick centered ({HOLD_STILL_SECONDS:.0f} s)..."
        self.client.set_output(hold)
        baseline = self._sample_axis(axis, 4, HOLD_STILL_SECONDS, stream=True)

        move = f">>> Move stick {label} for {SWEEP_SECONDS:.0f} s <<<"
        self.addComment(move)
        self.client.set_output(move)

        def live(i: int, total: int, v: float) -> None:
            if i == 1 or i == total or i % 4 == 0:
                self.client.set_output(f"{move}\n{channel} = {v:.3f} V ({i}/{total})")

        sweep = self._sample_axis(
            axis, SWEEP_SAMPLE_COUNT, SWEEP_SECONDS, stream=True, on_sample=live
        )
        all_v = baseline + sweep
        delta = max(all_v) - min(all_v)
        self.addComment(f"{channel} sweep delta = {delta:.3f} V")
        self.assertGreater(
            delta,
            SWEEP_MIN_DELTA_V,
            f"{channel} barely moved (delta={delta:.3f} V). Move stick {label} during test.",
        )

    def test_joystick_x_motion(self) -> None:
        """Moving stick X changes AIN0."""
        self._sweep_axis("x", "left/right (X)")

    def test_joystick_y_motion(self) -> None:
        """Moving stick Y changes AIN1."""
        self._sweep_axis("y", "up/down (Y)")

    def _read_distance_cm(self) -> float:
        """Read HC-SR04 via LJM (release NominalDAQ handle first)."""
        try:
            from labjack import ljm
        except ImportError:
            return math.nan
        self.daq.close()
        handle = None
        try:
            handle = ljm.openS("T4", "USB", "ANY")
            ljm.eWriteName(handle, "FIO5", 0)
            time.sleep(0.000002)
            ljm.eWriteName(handle, "FIO5", 1)
            time.sleep(0.00001)
            ljm.eWriteName(handle, "FIO5", 0)
            deadline = time.perf_counter() + 0.03
            while ljm.eReadName(handle, "FIO6") == 0:
                if time.perf_counter() >= deadline:
                    return math.nan
            t0 = time.perf_counter()
            while ljm.eReadName(handle, "FIO6") == 1:
                if time.perf_counter() >= deadline:
                    return math.nan
            pulse_s = time.perf_counter() - t0
            return pulse_s * 1e6 * 0.034 / 2.0
        except Exception:
            return math.nan
        finally:
            if handle is not None:
                try:
                    ljm.close(handle)
                except Exception:
                    pass
            self.daq.open()
            self._configure_channels()

    def test_ultrasonic_in_range(self) -> None:
        """HC-SR04 on FIO5/FIO6 reports distance in 2–400 cm."""
        self.addComment("Hold an object in front of the sensor...")
        in_range = False
        for _ in range(10):
            d = self._read_distance_cm()
            if math.isfinite(d):
                self.addComment(f"distance={d:.1f} cm")
            if DISTANCE_MIN_CM <= d <= DISTANCE_MAX_CM:
                in_range = True
                break
            time.sleep(0.3)
        if not in_range:
            self.addComment(
                "SKIPPED: distance not in range. Stop mouse-control.py; check FIO5/FIO6 + divider."
            )
            return

    def test_enable_off_after_tests(self) -> None:
        """Leave enable low when tests finish."""
        self._set_enable(False)
        self.addComment("Enable driven OFF.")

    def set_workflow_outputs(
        self, test_records: list[connect_python.TestRecord], client: connect_python.Client
    ) -> None:
        passed = sum(1 for r in test_records if r.is_successful())
        total = len(test_records)
        lines = [f"{passed}/{total} tests passed", ""]
        for record in test_records:
            status = record.status or "?"
            lines.append(f"{record.test}: {status}")
            if record.output:
                lines.append(f"  {record.output}")
        client.set_output("\n".join(lines))


if __name__ == "__main__":
    MouseTests.main()
