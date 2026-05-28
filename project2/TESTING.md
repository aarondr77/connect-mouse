# Project 2 — Automated tests (TestWorkflow)

This adds **pass/fail checks** on top of your working bench setup. Connect runs each `test_*` method in order and shows green/red results in the UI.

## How this differs from `arduino-plant.py`

| | `arduino-plant.py` | `plant_tests.py` |
|---|-------------------|------------------|
| **Purpose** | Live operation: UI toggle, streaming plots | One-shot **acceptance** checklist |
| **Runs** | Loop until you stop it | Fixed list of tests, then done |
| **UI** | Checkbox + plots | Test Workflow panel (Run all / rerun one) |
| **Verdict** | You eyeball the plots | `assert...` → **pass** or **fail** |

Both talk to the LabJack directly. **Stop `arduino-plant` before running tests.**

---

## Tests included

| Test | What it checks |
|------|----------------|
| `test_labjack_reads_voltage` | AIN0 in a plausible range |
| `test_enable_line_off` | FIO4 driven low |
| `test_enable_line_on` | FIO4 driven high (LED should go solid) |
| `test_joystick_sweep_when_enabled` | You move stick L/R; voltage span > 0.25 V |
| `test_enable_off_after_tests` | FIO4 left low |

The sweep test **retries once** if you didn’t move the stick enough the first time.

---

## Wrong script path (instant “Finished”)

If the test finishes in under a second and the log only says **`Starting script`**, Connect is running a **stub file**, not `project2/plant_tests.py`.

In the Test Workflow control, the path must be the **TestWorkflow** file:

```
/Users/aarondiamond-reivich/Nominal/projects/project2/plant_tests.py
```

**Not** `project2/arduino/plant/plant_tests.py` (that was an empty template).

After fixing, **Run Workflow** should list **five** tests (`test_labjack_reads_voltage`, …) and take roughly **10+ seconds** total.

---

## Add the Test Workflow in Connect (GUI)

Because the exact editor labels can vary by Connect version, add this control in the app editor:

1. Open **`app.connect`** in the Connect **editor**.
2. Add a new pane (e.g. below **Script Controls**) or use an empty area.
3. Add a **Test Workflow** control (sometimes under **Controls** or **Script controls**).
4. Point it at:

   ```
   /Users/aarondiamond-reivich/Nominal/projects/project2/plant_tests.py
   ```

5. Save the app.

### What you should see at runtime

- A list of tests named like `test_labjack_reads_voltage`, `test_joystick_sweep_when_enabled`, …
- **Run workflow** (or similar) to execute all tests in order
- Per-test **pass / fail / skip** and output text
- A summary table from `set_workflow_outputs` (e.g. `4/5 tests passed`)

You can **rerun a single failed test** after fixing wiring (TestWorkflow supports individual reruns).

---

## Running the tests

1. Wiring complete (README §5); `plant.ino` uploaded.
2. **Quit Kipling**; unplug nothing needed except close other LabJack apps.
3. **Do not** run **arduino-plant** at the same time.
4. Open Connect → your app → **Test Workflow** → **Run workflow**.
5. When `test_joystick_sweep_when_enabled` runs, **move the joystick left and right** for a few seconds.
6. Check the built-in LED: solid during enable tests, blinking again at the end.

---

## Optional: run from terminal (debug)

With the project venv active and hardware connected:

```bash
cd /Users/aarondiamond-reivich/Nominal/projects
source .venv/bin/activate
# Outside Connect this uses StubClient for discovery only:
python project2/plant_tests.py --discover-tests
```

Full hardware tests need to run **inside Connect** (real `Client` + LabJack).

---

## Tuning thresholds

Edit constants at the top of `plant_tests.py`:

- `SWEEP_MIN_DELTA_V` — increase if the stick is noisy; decrease if the stick has short travel
- `SWEEP_SECONDS` / `SWEEP_SAMPLE_COUNT` — longer window if you need more time to move the stick

---

## Nominal Core (optional)

To upload runs/events to Nominal Core, set `asset_rid` in `start_workflow`:

```python
self.asset_rid = "your-asset-rid-here"
```

See [TestWorkflow](https://docs.nominal.io/connect/documentation/introduction/overview) docs in Connect’s Python SDK (`connect_python.TestWorkflow`).

---

## Next ideas

- Fail if enable ON but voltage never changes (stuck stick or AIN0 unwired)
- Stream `joystick_voltage` during tests for a live plot
- Gate production on “all tests passed” before allowing `arduino-plant` to run
