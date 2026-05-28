"""
Compatibility entrypoint — Nominal Connect may still reference this path.

Runs the real TestWorkflow in project2/plant_tests.py.
Prefer updating app.connect to point directly at ../plant_tests.py.
"""

import runpy
from pathlib import Path

_REAL_SCRIPT = Path(__file__).resolve().parents[2] / "plant_tests.py"

if __name__ == "__main__":
    runpy.run_path(str(_REAL_SCRIPT), run_name="__main__")
