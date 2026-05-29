# Project 2 — Learnings: Hardware-in-the-Loop Testing with Nominal Connect

A summary of what we built, a real wiring bug the test suite caught, and ideas for making bench tests more diagnostic. Written to share with others exploring **Nominal Connect**, **LabJack**, and **Arduino** together.

---

## What we built

### The goal

A first **hardware-in-the-loop (HITL)** bench experiment using **Nominal Connect** as the control room:

1. **Turn a “system” on/off** from a Connect UI
2. **Stream sensor data** to plots and verify the system behaves as expected

We used a **LabJack T4** as the bridge between the Mac and the bench, and an **Arduino UNO** (Elegoo Super Starter Kit) as a simple “plant” — plus a **joystick module** instead of a standalone potentiometer.

### Architecture

```
┌─────────────────┐                      ┌──────────────────┐
│ Nominal Connect │  checkbox / plots    │  Mac (Python)    │
│  app.connect    │ ◄──────────────────► │  arduino-plant   │
└─────────────────┘                      │  plant_tests     │
                                         └────────┬─────────┘
                                                  │ USB
                                         ┌────────▼─────────┐
                                         │  LabJack T4      │
                                         │  FIO4 → enable   │
                                         │  AIN0 → voltage  │
                                         └────────┬─────────┘
                                                  │ wires
                                         ┌────────▼─────────┐
                                         │  Arduino UNO     │
                                         │  plant.ino       │
                                         │  D2 ← enable     │
                                         │  A0 ← joystick   │
                                         └──────────────────┘
```

### Three layers of software

| Layer | File | Runs on | Role |
|-------|------|---------|------|
| **Firmware** | `plant/plant.ino` | Arduino | Local “machine”: when **D2** is high, LED solid + PWM follows stick; when low, LED blinks slowly |
| **Operator script** | `arduino-plant.py` | Mac / Connect | Listens for UI toggle (message bus), drives **LabJack FIO4**, streams `joystick_voltage` and `system_on` to plots |
| **Acceptance tests** | `plant_tests.py` | Mac / Connect | Automated pass/fail checklist via `connect_python.TestWorkflow` |

### Connect app (`app.connect`)

- **Script table** — run `arduino-plant` for live operation
- **Test Workflow** — run `plant_tests` for automated acceptance
- **Form** — checkbox **System on** publishes to message bus topic `script/project2/system_on`
- **Plots** — `joystick_voltage`, `system_on`

### How control works

The checkbox does **not** call Python directly. It publishes a **message bus** event; `arduino-plant.py` subscribes and drives **FIO4** high/low, which reaches Arduino **D2**.

---

## What the tests look for

`plant_tests.py` defines a **TestWorkflow**: methods named `test_*` run in order, like Python `unittest`, with pass/fail shown in Connect.

| Test | What it checks |
|------|----------------|
| `test_labjack_reads_voltage` | LabJack **AIN0** returns a plausible voltage; **not pegged** to ~0 V or ~5 V at rest (stick centered) |
| `test_enable_line_off` | **FIO4** can be driven **low** |
| `test_enable_line_on` | **FIO4** can be driven **high** (Arduino pin-13 LED should go solid) |
| `test_joystick_sweep_when_enabled` | With enable on, moving the stick changes **AIN0** by at least **0.1 V** over a ~12 s window (baseline + sweep); streams live to the plot |
| `test_enable_off_after_tests` | **FIO4** left **low** when done |

**Important:** Only one script should use the LabJack at a time — stop `arduino-plant` before running tests.

See also: [TESTING.md](./TESTING.md) for setup instructions.

---

## The bug we observed

### Symptoms

- **`test_joystick_sweep_when_enabled`** failed repeatedly
- Early runs: voltage **barely changed** (`delta ≈ 0.01 V`) even when moving the stick
- Later runs (after some wiring changes): voltage **stuck at exactly ~5.003 V** with **zero change** (`min = max = 5.003 V`, `delta = 0`)

### What passed anyway

Four other tests passed, including:

- LabJack connects and reads **AIN0**
- Enable line **FIO4 → D2** works (off/on/off)

So the bug was **not** “LabJack broken” or “enable path broken” — it was specific to the **analog signal path** from the joystick.

### Root cause

**The joystick module’s GND pin was not connected to the breadboard ground rail.**

We had:

- **LabJack GND** and **Arduino GND** tied together on the breadboard ✓
- **Joystick +5V** wired to Arduino **5V** ✓
- **Joystick VRx** on the same row as **A0** and **AIN0** ✓
- **Joystick GND** — **no wire** ✗

Without **GND** on the module, the internal potentiometer has no proper reference. **VRx** floats or sits at the supply rail (~**5 V**) and does not track stick movement — exactly what the tests measured.

**Fix:** One jumper from **joystick GND** (leftmost pin) to the same **−** rail as LabJack and Arduino GND.

After that fix, centered voltage was ~**2.5 V**, the stick moved the reading, and the sweep test passed.

### Why 5.003 V was the smoking gun

A working joystick on **VRx** should sit near mid-scale (~**2.5 V** centered) and swing toward **0–5 V** when moved. **Constant 5.003 V** means we were effectively reading the **power rail**, not the wiper — classic “missing ground” or “signal wired to +5V instead of VRx.”

---

## Did the tests “tell us the bug”?

**Partially.**

| What worked | What didn’t (at first) |
|-------------|-------------------------|
| Failed on bad hardware automatically | First version of `test_labjack_reads_voltage` accepted **5.003 V** as “in range” |
| Pinpointed the **subsystem** (analog path, not enable) | Early failure messages said “move the stick” when the signal couldn’t move |
| After iteration, added **rail detection** and clearer hints | Required understanding that **5 V = power rail**, not “max stick position” |

**Lesson:** HITL tests need **physics-based contracts**, not only “value in range.” A joystick at rest should **not** read 5 V.

---

## Testing strategies we discussed

These ideas came from asking: *“Could tests not only detect a bug but point to the exact fix?”*

### 1. Layered tests (test pyramid for hardware)

Fail **early** and **specifically**:

```
Instrument sanity     →  Is LabJack reading correctly? (optional reference on AIN1)
Signal contracts      →  Not pegged to 0/5 V; looks like a wiper at rest
Stimulus–response     →  Does voltage change when the stick moves?
Control path          →  Enable line FIO4 ↔ D2
End-to-end            →  UI + plant behavior
```

Our bug would ideally fail at **“signal contracts”** before asking anyone to move the stick for 10 seconds.

### 2. Symptom → cause decision tree (fault dictionary)

| Observation | Likely cause | Suggested fix |
|-------------|--------------|---------------|
| **~5 V**, no change | Missing joystick **GND**, or signal on **+5V** | Connect GND to − rail; confirm VRx not on power pin |
| **~0 V**, no change | Signal shorted to **GND** | Rewire wiper row |
| **~2.5 V**, no change | Wrong axis (**VRy** vs **VRx**), or user didn’t move stick during window | Swap VRx/VRy; retry sweep |
| Enable tests pass, analog fails | Problem on **joystick path**, not LabJack digital | Focus on GND, +5V, VRx row |

Encode this once in assertion messages so failures read like **OBD-II codes for the bench**.

### 3. Mocking / isolation (software testing lens)

| Technique | What it proves | Catches wiring bugs? |
|-----------|----------------|----------------------|
| **Mock DAQ in Python** | Connect workflow, pass/fail logic | No — no real hardware |
| **Inject known voltage** (divider on AIN0) | LabJack + script path | No — bypasses joystick |
| **Real HITL tests** | Whole bench | **Yes** — if assertions are smart enough |

**Mocking** answers: *“If the sensor were perfect, would our software pass?”*  
**Smart HITL contracts** answer: *“Is the sensor path physically plausible?”*

Both are useful; they solve different problems.

### 4. Redundant sensing (cross-check)

Read the **same quantity two ways**:

- **LabJack AIN0** vs **Arduino A0** over USB serial

If they disagree → problem at the **junction row**.  
If both pegged at 5 V → **joystick power/GND**, not LabJack.

### 5. Stimulus–response vs passive sampling

Split interactive tests:

1. **Hold still** — noise-only delta  
2. **Move stick** — must exceed threshold  

Separates **operator timing** from **broken wiring**. Pegged-at-rail failures should be caught **before** phase 2.

### 6. Reference channel (instrument sanity)

Use **AIN1** with a fixed voltage divider (~2.5 V). If AIN1 is correct but AIN0 is pegged, the LabJack is fine and the **joystick path** is not.

---

## What we’d do differently next time

1. **Fail fast on rail pegging** in the first test (already added to `plant_tests.py`).
2. **Explicit fault messages** mapping voltage patterns to wiring checks (GND, +5V, VRx).
3. **Optional** Arduino serial cross-check for integration debugging.
4. **Optional** separate **software-only** test module with mocked readings for CI.
5. Document **expected voltages** for beginners (~2.5 V centered, not 5 V).

---

## Key takeaway

We built a small but real **edge test app**: Connect UI → Python → LabJack → Arduino plant, with **automated acceptance tests** that caught a **real hardware wiring bug** (missing joystick GND).

The test suite did its job even when messages were imperfect. The next step in maturity is not more tests for their own sake — it’s **diagnostic tests** that encode bench knowledge so the **first failing assertion** names the likely fix.

That’s the same progression as good software testing: from *“something failed”* to *“this contract was violated, here’s what that usually means.”*

---

## File map

| File | Purpose |
|------|---------|
| `plant/plant.ino` | Arduino firmware |
| `arduino-plant.py` | Live operator script + streaming |
| `plant_tests.py` | Automated TestWorkflow |
| `README.md` | Full build & wiring guide |
| `TESTING.md` | How to run tests in Connect |
| `LEARNINGS.md` | This document |

---

## Related reading

- [Nominal Connect overview](https://docs.nominal.io/connect/documentation/introduction/overview)
- [Message bus](https://docs.nominal.io/connect/documentation/message-bus/message-bus) (UI ↔ script)
- `connect_python.TestWorkflow` — unittest-style workflows in Connect
