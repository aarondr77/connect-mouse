"""
Automated acceptance tests for Project 2 (Arduino plant + LabJack T4).

Run from Nominal Connect via a Test Workflow control (see project2/TESTING.md).
Do not run arduino-plant.py at the same time — both need the LabJack.
"""

from __future__ import annotations

import time

import connect_python
from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver
from nominal_instro.instruments.daq import NominalDAQ
from nominal_instro.instruments.daq.types import Direction, Logic

ENABLE_LABJACK_LINE = "FIO4"

# Joystick on AIN0: expect roughly 0–3.3 V (stick) on a 0–5 V Arduino source.
VOLTAGE_MIN_V = -0.5
VOLTAGE_MAX_V = 5.5
SWEEP_MIN_DELTA_V = 0.25
SWEEP_SAMPLE_COUNT = 20
SWEEP_SECONDS = 8.0


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

    def _sample_voltages(self, count: int, duration_s: float) -> list[float]:
        interval = duration_s / count
        readings: list[float] = []
        for _ in range(count):
            readings.append(self._read_voltage())
            time.sleep(interval)
        return readings

    def test_labjack_reads_voltage(self) -> None:
        """Sanity: AIN0 returns a plausible voltage with the joystick wired."""
        voltage = self._read_voltage()
        self.addComment(f"AIN0 = {voltage:.3f} V")
        self.assertGreaterEqual(voltage, VOLTAGE_MIN_V)
        self.assertLessEqual(voltage, VOLTAGE_MAX_V)

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
        """With enable on, moving the stick left/right should change AIN0 by at least SWEEP_MIN_DELTA_V."""
        self._set_enable(True)
        prompt = (
            f">>> Move the joystick LEFT and RIGHT now — sampling for {SWEEP_SECONDS:.0f} s <<<"
        )
        self.addComment(prompt)
        self.client.set_output(prompt)

        readings = self._sample_voltages(SWEEP_SAMPLE_COUNT, SWEEP_SECONDS)
        v_min = min(readings)
        v_max = max(readings)
        delta = v_max - v_min
        self.addComment(
            f"Sampled {len(readings)} readings: min={v_min:.3f} V, max={v_max:.3f} V, delta={delta:.3f} V"
        )
        self.assertGreater(
            delta,
            SWEEP_MIN_DELTA_V,
            f"Expected stick sweep span > {SWEEP_MIN_DELTA_V} V while enabled. "
            "Move the joystick left/right during the test.",
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
