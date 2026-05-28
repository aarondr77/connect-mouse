import time
from datetime import datetime, timezone

import connect_python
from nominal_instro.instruments.daq import NominalDAQ
from nominal_instro.instruments.daq.types import Direction
from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver

logger = connect_python.get_logger(__name__)

DURATION_SECONDS = 60.0
SAMPLE_INTERVAL = 1.0


@connect_python.main
def main(client: connect_python.Client):
    logger.info("Starting LabJack T4 stream")

    daq = NominalDAQ(
        name="labjack_t4",
        driver=LabJackTSeriesDriver(device_id="ANY"),
    )
    daq.open()

    daq.configure_analog_channel(
        direction=Direction.INPUT,
        physical_channel="AIN0",
        alias="ain0",
        range_min=-10.0,
        range_max=10.0,
    )

    client.clear_stream("ain0")

    start = time.monotonic()
    sample_count = 0

    try:
        while time.monotonic() - start < DURATION_SECONDS:
            measurement = daq.read_analog()
            logger.info(f"raw measurement: {measurement!r}")  # for first-run inspection

            # Adjust attribute access based on the log output above
            value = measurement.values[0]
            t = datetime.now(timezone.utc)

            client.stream("ain0", t, value, name="value")

            sample_count += 1
            time.sleep(SAMPLE_INTERVAL)

        logger.info(f"Done. Streamed {sample_count} samples over {DURATION_SECONDS}s.")
    finally:
        daq.close()
        print("FINISHED")


if __name__ == "__main__":
    main()