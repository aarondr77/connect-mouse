import connect_python
import subprocess
import sys
from pathlib import Path

logger = connect_python.get_logger(__name__)

# Same as: cd …/Nominal/projects && source .venv/bin/activate && python -c "…"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_python_c(code: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if result.stderr:
        print(result.stderr, end="", flush=True)
    print(result.stdout, end="", flush=True)


def _inspect_module_public_names(module_qname: str) -> None:
    code = (
        f"import {module_qname} as m; "
        "print([x for x in dir(m) if not x.startswith('_')])"
    )
    _run_python_c(code)


@connect_python.main
def main(client: connect_python.Client):
    logger.info("Starting script")
    print(f"Python interpreter: {sys.executable}", flush=True)
    print("--- nominal_instro.instruments.daq ---", flush=True)
    _inspect_module_public_names("nominal_instro.instruments.daq")
    print("--- nominal_instro.drivers.daq.labjack ---", flush=True)
    _inspect_module_public_names("nominal_instro.drivers.daq.labjack")

    print("--- LabJackTSeriesDriver.__init__ (help) ---", flush=True)
    _run_python_c(
        "from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver; "
        "help(LabJackTSeriesDriver.__init__)"
    )

    print("--- LabJackTSeriesDriver (help) ---", flush=True)
    _run_python_c(
        "from nominal_instro.drivers.daq.labjack import LabJackTSeriesDriver; "
        "help(LabJackTSeriesDriver)"
    )

    print("--- nominal_instro.drivers.daq.labjack.t_series_models ---", flush=True)
    _run_python_c(
        "from nominal_instro.drivers.daq.labjack import t_series_models as m; "
        "print([x for x in dir(m) if not x.startswith('_')])"
    )

    print("--- LJ_T4 ---", flush=True)
    _run_python_c(
        "from nominal_instro.drivers.daq.labjack.t_series_models import LJ_T4; "
        "print(LJ_T4); print(type(LJ_T4)); help(LJ_T4)"
    )

    # Common tasks:

    # Read or write UI values.
    # frequency = client.get_value("frequency", 1.0)
    # client.set_value("status", "running")

    # Stream data.
    # from datetime import datetime, timezone
    # t = datetime.now(timezone.utc)
    # client.clear_stream("sine_wave")
    # client.stream("sine_wave", t, 1.23, name="value")

    # Stream multiple channels from a dict.
    # client.clear_stream("sensors")
    # client.stream_from_dict(
    #     "sensors",
    #     timestamp=t,
    #     channel_map={"temp": 20.0, "pressure": 101.3},
    # )

    # Publish or receive messages on the message bus.
    # with connect_python.MessageBus(client) as message_bus:
    #     message_bus.publish_message("script/test_topic", {"hello": "world"})
    #     message_bus.subscribe_to_topic("script/test_topic")
    #     message = message_bus.wait_for_message()
    #     client.set_output(message)

    pass


if __name__ == "__main__":
    main()
