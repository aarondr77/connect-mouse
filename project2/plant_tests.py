"""
Automated acceptance tests for Project 2 (Arduino plant + LabJack T4).

Run from Nominal Connect via a Test Workflow control (see project2/TESTING.md).
Do not run arduino-plant.py at the same time — both need the LabJack.
"""

from __future__ import annotations

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
# Centered stick on a correctly wired module is usually ~2.5 V, not pegged at 5 V.
CENTERED_TYPICAL_MIN_V = 0.3
CENTERED_TYPICAL_MAX_V = 4.7

VOLTAGE_MIN_V = -0.5
VOLTAGE_MAX_V = 5.5
SWEEP_MIN_DELTA_V = 0.10
SWEEP_SAMPLE_COUNT = 24
SWEEP_SECONDS = 10.0
HOLD_STILL_SECONDS = 2.0


class PlantTests(connect_python.TestWorkflow):
    """Bench tests for the plant wiring and enable line."""

    def start_workflow(self, client: connect_python.Client) -> None:
        self.daq = NominalDAQ(
            name="labjack_t4",
            driver=LabJackTSeriesDriver(device_id="ANY"),
        )
        self.daq.open()

        self.daq.configure_digital_channel(
            direction=Direction.OUTPUT,
            physical_channel=ENABLE_LABJACK_LINE,
            logic=Logic.HIGH,
            alias="enable_out",
        )
        self.daq.configure_analog_channel(
            direction=Direction.INPUT,
            physical_channel="AIN0",
            alias="joystick_voltage",
            range_min=-10.0,
            range_max=10.0,
        )

        self.add_cleanup(self._shutdown_daq)
        self.addComment("LabJack connected and channels configured.")

    def _shutdown_daq(self) -> None:
        self.daq.write_digital_line("enable_out", 0)
        self.daq.close()

    def _read_voltage(self) -> float:
        return float(self.daq.read_analog().values[0])

    def _set_enable(self, on: bool) -> None:
        self.daq.write_digital_line("enable_out", 1 if on else 0)
        time.sleep(0.15)

    def _sample_voltages(
        self,
        count: int,
        duration_s: float,
        *,
        stream: bool = False,
        on_sample: Callable[[int, int, float], None] | None = None,
    ) -> list[float]:
        interval = duration_s / count if count else duration_s
        readings: list[float] = []
        for i in range(count):
            voltage = self._read_voltage()
            readings.append(voltage)
            if stream:
                t = datetime.now(timezone.utc)
                self.client.stream("joystick_voltage", t, voltage, name="value", unit="V")
            if on_sample is not None:
                on_sample(i + 1, count, voltage)
            time.sleep(interval)
        return readings

    def _rail_wiring_hint(self, voltage: float) -> str:
        if voltage >= RAIL_HIGH_V:
            return (
                f"AIN0 reads {voltage:.3f} V (~5 V power rail). "
                "The signal row (A0 + AIN0) is tied to +5V, not the stick output.\n"
                "Fix: move the jumper on that row from +5V / joystick +5V pin to "
                "joystick VRx or VRy (analog output pins, not the +5V power pin)."
            )
        if voltage <= RAIL_LOW_V:
            return (
                f"AIN0 reads {voltage:.3f} V (~GND). "
                "The signal row is tied to ground, not the stick output.\n"
                "Fix: connect the shared row to VRx or VRy, not GND."
            )
        return ""

    def _joystick_sweep_failure_message(self, readings: list[float]) -> str:
        v_min = min(readings)
        v_max = max(readings)
        delta = v_max - v_min
        mean = sum(readings) / len(readings)
        rail_hint = self._rail_wiring_hint(mean)
        if rail_hint:
            return rail_hint
        return (
            f"AIN0 barely moved: min={v_min:.3f} V, max={v_max:.3f} V, "
            f"delta={delta:.3f} V (need > {SWEEP_MIN_DELTA_V} V), avg={mean:.3f} V.\n"
            "During the test, move the stick in ALL directions (left, right, up, down).\n"
            "If voltage stays flat:\n"
            "  1. Run arduino-plant and watch Joystick voltage — which stick direction moves the plot?\n"
            "  2. If only UP/DOWN moves the plot, swap the breadboard wire from VRx to VRy "
            "(joystick pin next to VRx on the module).\n"
            "  3. Confirm the wiper wire (VRx or VRy) shares one row with A0 and AIN0."
        )

    def test_labjack_reads_voltage(self) -> None:
        """Sanity: AIN0 returns a plausible voltage with the joystick wired."""
        voltage = self._read_voltage()
        self.addComment(f"AIN0 = {voltage:.3f} V")
        self.assertGreaterEqual(voltage, VOLTAGE_MIN_V)
        self.assertLessEqual(voltage, VOLTAGE_MAX_V)
        rail_hint = self._rail_wiring_hint(voltage)
        self.assertFalse(
            rail_hint,
            rail_hint or f"Unexpected AIN0={voltage:.3f} V",
        )
        self.assertGreaterEqual(
            voltage,
            CENTERED_TYPICAL_MIN_V,
            f"AIN0={voltage:.3f} V looks stuck near 0 V with stick centered — check wiper wiring.",
        )
        self.assertLessEqual(
            voltage,
            CENTERED_TYPICAL_MAX_V,
            f"AIN0={voltage:.3f} V looks stuck near 5 V with stick centered — "
            "signal row may be on +5V instead of VRx/VRy.",
        )

    def test_enable_line_off(self) -> None:
        """Enable output can be driven low (system off)."""
        self._set_enable(False)
        voltage = self._read_voltage()
        self.addComment(f"Enable OFF, AIN0 = {voltage:.3f} V")

    def test_enable_line_on(self) -> None:
        """Enable output can be driven high (system on); Arduino LED should go solid."""
        self._set_enable(True)
        voltage = self._read_voltage()
        self.addComment(f"Enable ON, AIN0 = {voltage:.3f} V — check pin-13 LED is solid ON")

    @connect_python.retry(max_tries=2, wait=connect_python.wait_fixed(1.0))
    def test_joystick_sweep_when_enabled(self) -> None:
        """With enable on, moving the stick should change AIN0 by at least SWEEP_MIN_DELTA_V."""
        self._set_enable(True)
        self.client.clear_stream("joystick_voltage")

        hold_prompt = f"Hold stick centered ({HOLD_STILL_SECONDS:.0f} s baseline)..."
        self.client.set_output(hold_prompt)
        baseline = self._sample_voltages(4, HOLD_STILL_SECONDS, stream=True)
        baseline_delta = max(baseline) - min(baseline)
        self.addComment(f"Baseline delta (hold still): {baseline_delta:.3f} V")

        move_prompt = (
            f">>> NOW move the stick — left, right, up, AND down — for {SWEEP_SECONDS:.0f} s <<<"
        )
        self.addComment(move_prompt)
        self.client.set_output(move_prompt)

        def show_live(sample_i: int, total: int, voltage: float) -> None:
            if sample_i == 1 or sample_i == total or sample_i % 4 == 0:
                self.client.set_output(f"{move_prompt}\nAIN0 = {voltage:.3f} V ({sample_i}/{total})")

        readings = self._sample_voltages(
            SWEEP_SAMPLE_COUNT,
            SWEEP_SECONDS,
            stream=True,
            on_sample=show_live,
        )
        all_readings = baseline + readings
        v_min = min(all_readings)
        v_max = max(all_readings)
        delta = v_max - v_min
        self.addComment(
            f"Sweep: min={v_min:.3f} V, max={v_max:.3f} V, delta={delta:.3f} V"
        )
        self.assertGreater(
            delta,
            SWEEP_MIN_DELTA_V,
            self._joystick_sweep_failure_message(all_readings),
        )

    def test_enable_off_after_tests(self) -> None:
        """Leave the plant disabled when tests finish."""
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
    PlantTests.main()
