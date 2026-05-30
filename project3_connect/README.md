# Project 3 (Connect): Joystick mouse + ultrasonic click — implementation plan

**Prerequisites:** Complete [Project 2](../project2/README.md) (joystick on **VRx**, shared ground, LabJack **FIO4 → D2**, Connect streaming). Read [LEARNINGS.md](../project2/LEARNINGS.md) for why tests and wiring contracts matter.

This README is the **build plan** for the next bench: use the joystick to **move the Mac cursor**, use an **HC-SR04 ultrasonic** for **proximity click** (hand closer = click), and stream **everything through Nominal Connect**.

**Implemented software (streaming + mouse v2):** All sensor plots come from the **LabJack** only (`joystick_x`, `joystick_y`, `distance`). When **System on** is armed, the script moves the Mac cursor from the joystick and fires proximity left-clicks from ultrasonic distance. Live tuning via Connect sliders (`mouse_speed`, dead zone, near/far thresholds).

---

## Table of contents

1. [Goals](#1-goals)
2. [What you are building](#2-what-you-are-building)
3. [Why both LabJack and Arduino?](#3-why-both-labjack-and-arduino)
4. [Signal types (joystick vs ultrasonic)](#4-signal-types-joystick-vs-ultrasonic)
5. [Pin plan](#5-pin-plan)
6. [Wiring](#6-wiring)
7. [Data streams in Connect](#7-data-streams-in-connect)
8. [Software components (to implement)](#8-software-components-to-implement)
9. [Proximity click logic](#9-proximity-click-logic)
10. [Mouse movement (later phase)](#10-mouse-movement-later-phase)
11. [Implementation phases](#11-implementation-phases)
12. [Tests (TestWorkflow)](#12-tests-testworkflow)
13. [macOS permissions](#13-macos-permissions)
14. [Troubleshooting](#14-troubleshooting)
15. [File map (planned)](#15-file-map-planned)

---

## 1. Goals

| # | Goal |
|---|------|
| G1 | **Mouse X/Y** from joystick **VRx** and **VRy** |
| G2 | **LabJack** reads stick voltages → Connect plots + automated tests (primary for analog) |
| G3 | **Arduino** also reads stick + ultrasonic → serial telemetry for **cross-check** and firmware-side logic |
| G4 | **Ultrasonic distance** on **both** LabJack (FIO timing) and Arduino (HC-SR04 library) → two streams to compare |
| G5 | **Proximity click** when hand crosses into “near” range (debounced edge, not fist detection) |
| G6 | Optional: keep Project 2–style **enable** on **FIO4 → D2** to arm mouse + clicks |

**Non-goals (for v1):** Webcam / fist detection; wireless; production-polished mouse driver.

---

## 2. What you are building

```
┌──────────────────────────────────────────────────────────────────────┐
│  Nominal Connect (app.connect)                                        │
│  • Plots: joystick_x, joystick_y, distance_lj, distance_arduino, click │
│  • Tests: rails, dual-axis motion, distance agreement, proximity click  │
│  • Optional: System on (message bus) → FIO4 enable                    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ USB
┌───────────────────────────────▼──────────────────────────────────────┐
│  mouse-control.py  (@connect_python.main)                             │
│  • LabJack: AIN0/AIN1, FIO4, FIO5/FIO6 (ultrasonic)                   │
│  • Serial:  parse Arduino lines → cross-check + backup distance         │
│  • Stream all channels; optional pynput/pyautogui mouse + click         │
└───────────────┬──────────────────────────────┬─────────────────────────┘
                │ USB                          │ USB serial
       ┌────────▼────────┐            ┌────────▼────────┐
       │  LabJack T4     │            │  Arduino UNO    │
       │  AIN0 ← VRx     │            │  A0 ← VRx       │
       │  AIN1 ← VRy     │            │  A1 ← VRy       │
       │  FIO4 → D2      │            │  D2 ← FIO4      │
       │  FIO5 → Trig    │            │  D7  → Trig     │
       │  FIO6 ← Echo    │            │  D8  ← Echo     │
       └────────┬────────┘            └────────┬────────┘
                │                            │
                └──────────┬─────────────────┘
                           │
              ┌────────────▼────────────┐
              │  Joystick (GND,+5V,VRx,VRy) │
              │  HC-SR04 (VCC,GND,Trig,Echo)│
              └─────────────────────────────┘
```

**Operator experience (when fully built):**

- Move stick → cursor moves (after mouse phase); **joystick_x / joystick_y** plots update live.
- Bring hand into ultrasonic range → **click** (one per approach); **distance_*** plots drop.
- Compare **distance_lj** vs **distance_arduino** in Connect — they should track (validates both paths).

---

## 3. Why both LabJack and Arduino?

This is intentional **redundant sensing**, not duplication for its own sake.

| Path | Joystick | Ultrasonic | Best for |
|------|----------|------------|----------|
| **LabJack** | **AIN0**, **AIN1** | **FIO5/FIO6** + timing in Python/LJM | Connect plots, high-rate logging, `plant_tests`-style contracts |
| **Arduino** | **A0**, **A1** | **D7/D8** + `NewPing` or similar | Reliable µs timing, kit tutorials, serial debug |

| Benefit | Explanation |
|---------|-------------|
| **Cross-check** | If `joystick_x` (LJ) moves but `a0` (Arduino) does not → wiring row problem |
| **Cross-check** | If `distance_lj` and `distance_arduino` disagree → HC-SR04 **Trig**/**Echo** wiring or LabJack FIO timing issue |
| **Learning** | Same lesson as Project 2: two views of one physical quantity |
| **Connect** | One script streams **four** sensor families; tests encode “they should agree” |

**Connect does not care** which device measured first — it only sees what `mouse-control.py` streams.

**Rule:** Only **one** program owns the LabJack at a time (`mouse-control.py` **or** `arduino-plant.py` **or** `plant_tests.py`).

---

## 4. Signal types (joystick vs ultrasonic)

### Joystick — analog (same as Project 2)

| Pin | Voltage | LabJack | Arduino |
|-----|---------|---------|---------|
| **VRx** | ~0–5 V | **AIN0** | **A0** |
| **VRy** | ~0–5 V | **AIN1** | **A1** |
| **GND** | 0 V | − rail | GND |
| **+5V** | 5 V | — (power from Arduino **5V** → breadboard **+ rail**; see [§6.2.1](#621-shared-5-v-on-the--rail-recommended)) | **+ rail** (same as joystick) |

Centered stick ≈ **~2.5 V**, not **5.0 V** (see [LEARNINGS.md](../project2/LEARNINGS.md)).

### HC-SR04 — digital timing (not AIN)

The **HC-SR04** is a small ultrasonic distance board with **four pins** printed on it (usually in a row): **VCC**, **GND**, **Trig**, **Echo**. Those names refer to **pins on the sensor module**, not LabJack or Arduino pin names.

The module does **not** output distance as a single analog voltage. Your code talks to it with two digital lines:

| Pin on **HC-SR04 module** | Direction (from the sensor’s view) | What happens |
|---------------------------|-------------------------------------|----------------|
| **Trig** | Input to the sensor | Host sends a short HIGH pulse to start a measurement |
| **Echo** | Output from the sensor | Sensor drives HIGH; pulse **width ∝ distance** |

Wire each module pin to a **host** pin on the LabJack and/or Arduino:

| HC-SR04 module pin | LabJack (host) | Arduino (host) |
|--------------------|----------------|----------------|
| **VCC** | Optional **VS** *or* breadboard **+ rail** (same 5 V as joystick) | **+ rail** (not a signal row) |
| **GND** | − rail | − rail |
| **Trig** | **FIO5** (LabJack **output**) | **D7** (**output**) |
| **Echo** | **FIO6** (LabJack **input**) | **D8** (**input**) |

**Important (LabJack safety):** T4 **FIO** inputs are **3.3 V** logic. With the HC-SR04 on **5 V** (your normal bench setup), **Echo** pulses at about **5 V**. Wire **Echo → Arduino D8** directly, but **never Echo → FIO6 directly** — use the **1 kΩ + 2 kΩ voltage divider** in [§6.3.1](#631-echo-voltage-divider-for-fio6-required-at-5-v). Arduino **D8** on UNO usually tolerates 5 V echo; **verify your module datasheet**.

**Why people still use Arduino for ultrasonic:** libraries handle µs timing reliably. **Why still use LabJack:** one Connect script logs **distance_lj** next to **AIN** data for tests and plots.

---

## 5. Pin plan

### LabJack T4 (screw terminals you use)

| Terminal | Function |
|----------|----------|
| **GND** | Common ground |
| **AIN0** | Joystick **VRx** |
| **AIN1** | Joystick **VRy** |
| **FIO4** | Enable → Arduino **D2** (optional, from Project 2) |
| **FIO5** | To HC-SR04 **Trig** pin on the module (LabJack drives trigger) |
| **FIO6** | From divider **tap** between 1 kΩ / 2 kΩ (scaled Echo — see §6.3.1) |

Do **not** use **FIO0** on the T4 screw block — labels are **FIO4–FIO7** only.

### Arduino UNO

| Pin | Function |
|-----|----------|
| **A0** | Joystick **VRx** (same row as **AIN0**) |
| **A1** | Joystick **VRy** (same row as **AIN1**) |
| **D2** | Enable from **FIO4** |
| **D7** | To HC-SR04 **Trig** pin on the module (Arduino drives trigger) |
| **D8** | From HC-SR04 **Echo** pin on the module (Arduino reads echo) |
| **5V**, **GND** | Power / ground (joystick + sensor) |

### Joystick (unchanged from Project 2 + one new wire)

| Pin | Connect |
|-----|---------|
| **GND** | Breadboard **− rail** (shared with Arduino GND, LabJack GND, HC-SR04) |
| **+5V** | Breadboard **+ rail** (fed once from Arduino **5V**; see §6.2.1) |
| **VRx** | Row → **AIN0** + **A0** |
| **VRy** | Row → **AIN1** + **A1** |
| **SW** | Optional later (physical click) |

---

## 6. Wiring

**Power off** USB while wiring.

### 6.1 Keep all Project 2 connections

- Shared **GND** on breadboard **− rail** (LabJack, Arduino, joystick)  
- Shared **5 V** on breadboard **+ rail** from Arduino **5V** (joystick **+5V** on **+ rail**)  
- **VRx** row: **AIN0**, **A0**  
- **FIO4 → D2** (if using enable)  
- Joystick **GND** wired (you fixed this in Project 2)

### 6.2 Add joystick Y

| From | To |
|------|-----|
| Joystick **VRy** | New breadboard row |
| Arduino **A1** | Same row |
| LabJack **AIN1** | Same row |

#### 6.2.1 Shared 5 V on the **+ rail** (recommended)

If you finished Project 2 with the joystick powered from the breadboard **+ rail** (red line), keep that layout and add the ultrasonic sensor the same way.

**How it works (you are not “splitting” 5 V):**

- Run **one** jumper: Arduino pin **5V** → breadboard **+ rail** (entire red line is ~5 V).
- Run **one** shared ground: Arduino **GND** → breadboard **− rail** (entire blue line is 0 V).
- Add a jumper from **+ rail** → joystick pin **+5V**.
- Add another jumper from **+ rail** → HC-SR04 pin **VCC**.

That is **parallel power**: joystick and sensor both see the same ~5 V relative to **− rail**. It does **not** divide or corrupt the voltage on the stick’s **VRx** / **VRy** rows, because those rows carry **signals only** — never stick **+5V** or sensor **VCC** on them.

```text
Arduino 5V ──► + rail ──┬── joystick +5V
                        └── HC-SR04 VCC

Arduino GND ─► − rail ──┬── joystick GND
                        ├── HC-SR04 GND
                        └── LabJack GND
```

**Current draw:** Joystick and HC-SR04 together are well within what USB → Arduino **5V** can supply on a bench build. If 5 V were overloaded you might see resets or nonsense readings — uncommon here.

**Do not:**

- Put **+5V** or **VCC** on the same breadboard **row** as **VRx** or **VRy** (those rows are only for the analog voltage signal).
- Tie Arduino **5V** to LabJack **VS** unless you deliberately want two supplies (for v1, **Arduino 5V → + rail only** is enough).

**Alternative (also fine):** Two separate jumpers from Arduino **5V** — one to joystick **+5V**, one to **VCC** — with no **+ rail**. Electrically the same; the **+ rail** is just neater when you add more parts.

### 6.3 Add HC-SR04 (both LabJack and Arduino)

Plug the HC-SR04 into the breadboard so you can reach all four **module** pins: **VCC**, **GND**, **Trig**, **Echo** (the silkscreen labels on the sensor board).

You will connect **one physical sensor** to **two hosts** (LabJack + Arduino). Power and ground go to both; the two signal pins are shared:

1. **Power** — **VCC** → breadboard **+ rail** (same **+ rail** as joystick **+5V**; **+ rail** fed once from Arduino **5V** — see [§6.2.1](#621-shared-5-v-on-the--rail-recommended)). **GND** → breadboard **− rail** (shared with joystick, LabJack, Arduino).
2. **Trig** (on the **module**) — one breadboard row or jumper fan-out to **both** LabJack **FIO5** and Arduino **D7**. Both hosts can drive the same trigger line in parallel when they pulse.
3. **Echo** (on the **module**) — see [§6.3.1](#631-echo-voltage-divider-for-fio6-required-at-5-v): **D8** connects to **full-strength Echo**; **FIO6** connects only through the **divider** (scaled down from 5 V).

| Pin on HC-SR04 **module** | Connect to LabJack | Connect to Arduino |
|---------------------------|--------------------|--------------------|
| **VCC** | Optional **VS** *or* **+ rail** only | **+ rail** (parallel with joystick **+5V**) |
| **GND** | − rail | − rail |
| **Trig** | **FIO5** | **D7** |
| **Echo** | **FIO6** via divider (§6.3.1) | **D8** direct from Echo bus row |

**Do not confuse module pins with host pins:** “**Trig**” in the table above is the pin **on the HC-SR04**; **FIO5** / **D7** are where you attach that wire on the LabJack and Arduino.

#### 6.3.1 Echo voltage divider for FIO6 (required at 5 V)

When the sensor runs from the breadboard **+ rail** (~5 V), **Echo** is a **5 V** digital pulse. The LabJack T4 **FIO6** input must see about **3.3 V or less**. A **voltage divider** (two resistors) scales Echo down before **FIO6**. The **HC-SR04 is not harmed** by this — Echo is an output, and kΩ resistors are a normal load.

**Parts (same Elegoo Super Starter Kit as Project 2)**

| Part | Value | Use in this step |
|------|-------|------------------|
| Resistor | **1 kΩ** | Upper leg (Echo → tap) — bands **brown, black, red** |
| Resistor | **2 kΩ** | Lower leg (tap → GND) — bands **red, black, red** |
| Breadboard | — | Same board as joystick |
| Jumper wires | male–male | Echo bus, tap → **FIO6**, **D8** |

Find **1 kΩ** and **2 kΩ** on the kit’s resistor strip (paper tape labeled **102** = 1 kΩ, **202** or **2K** = 2 kΩ if present). If your strip uses words, pick the values in the table above.

**Target voltage:** With **1 kΩ** on top and **2 kΩ** to ground, the tap is roughly **5 V × 2/(1+2) ≈ 3.3 V** when Echo is high — safe for **FIO6**.

**Circuit (what you are building)**

```text
HC-SR04 Echo ──►  "echo bus" row on breadboard
                      │
                      ├── jumper ──────────────► Arduino D8   (full 5 V echo — OK on UNO)
                      │
                      └── 1 kΩ resistor ──►  "FIO tap" row
                                                │
                                                ├── jumper ──► LabJack FIO6
                                                │
                                                └── 2 kΩ resistor ──► breadboard − rail (GND)
```

Only **one** wire goes to **FIO6**, and it comes from the **FIO tap** row (between the two resistors), **not** from the echo bus row.

**Step-by-step (power off)**

1. **Echo bus row** — Plug a jumper from the HC-SR04 **Echo** pin into a **new empty breadboard row** (not the **+ rail**, not **VRx/VRy**). This row is the **echo bus**.
2. **Arduino D8** — Jumper from the **same echo bus row** to Arduino **D8**.
3. **Upper resistor (1 kΩ)** — One leg in the **echo bus** row, other leg in a **new empty row** (**FIO tap** row). The resistor body can bridge the gap between rows; each metal leg must sit in its own row (or same 5-hole group on one side of the board).
4. **Lower resistor (2 kΩ)** — One leg in the **FIO tap** row, other leg in the breadboard **− rail** (shared GND with LabJack, Arduino, sensor).
5. **LabJack FIO6** — Jumper from the **FIO tap** row (the node between the two resistors) to screw terminal **FIO6**. **Do not** jumper echo bus → **FIO6** without the divider.
6. **Double-check before USB power**
   - [ ] **Echo** → echo bus → **D8** (direct)
   - [ ] **Echo** → echo bus → **1 kΩ** → FIO tap → **FIO6**
   - [ ] FIO tap → **2 kΩ** → **− rail**
   - [ ] No wire from echo bus to **FIO6** except through **1 kΩ** + tap
7. **Trig** and power — Wire **Trig**, **VCC**, **GND** as in §6.3 steps 1–2. You can complete **Phase B** (Arduino **D7/D8** only, no **FIO5/FIO6**) before adding the divider and LabJack ultrasonic lines.

**Breadboard tip:** On a typical mini breadboard, holes **a–e** in one row are connected, and **f–j** in that row are connected; the **center trench** separates left and right. Put the **echo bus** on one side (e.g. row 20, column **e**) and the **FIO tap** on another hole in a different row (e.g. row 22, column **e**), with resistors spanning between rows as needed.

**Phase order (safest)**

| Phase | Echo wiring |
|-------|-------------|
| **B** (Arduino ultrasonic first) | Echo bus → **D8** only; leave **FIO6** unwired |
| **C** (add LabJack) | Add **1 kΩ / 2 kΩ** divider and jumper FIO tap → **FIO6**; keep **D8** on echo bus |

**Quick test after wiring**

- With Connect/serial showing `distance_arduino`, wave a hand in front of the sensor — plot should move.
- After **FIO6** is connected through the divider, `distance_lj` should track `distance_arduino` within a few cm. If **distance_lj** is always wrong or flat, re-check: **FIO6** on **tap** row, **2 kΩ** to **− rail**, not echo bus → **FIO6** direct.

### 6.4 Checklist

- [ ] **VRy** on same row as **AIN1** and **A1**  
- [ ] **VRx** still on row with **AIN0** and **A0**  
- [ ] Arduino **5V** → breadboard **+ rail** (one feed)  
- [ ] Joystick **+5V** and HC-SR04 **VCC** on **+ rail** (not on VRx/VRy rows)  
- [ ] Joystick **GND** on − rail  
- [ ] HC-SR04 **GND** on − rail  
- [ ] HC-SR04 module **Trig** pin wired to **FIO5** and **D7**  
- [ ] Echo bus → **D8** (direct)  
- [ ] Echo bus → **1 kΩ** → FIO tap → **FIO6**; FIO tap → **2 kΩ** → **− rail** (§6.3.1)  
- [ ] **No** direct jumper from Echo / echo bus to **FIO6**  
- [ ] No **+5V** on the analog signal rows  

---

## 7. Data streams in Connect

Stream IDs from `mouse-control.py` (match `app.connect` plots):

| Stream | Unit | Source | Purpose |
|--------|------|--------|---------|
| `joystick_x` | V | LabJack **AIN0** | X axis + mouse mapping |
| `joystick_y` | V | LabJack **AIN1** | Y axis + mouse mapping |
| `distance` | cm | LabJack **FIO5/6** | Ultrasonic distance + proximity click |
| `system_on` | 0/1 | UI / FIO4 | Arm switch for enable + mouse/click |
| `enable_out` | 0/1 | LabJack **FIO4** | Echo of enable line |
| `mouse_dx` | px | Script | Cursor delta X (debug) |
| `mouse_dy` | px | Script | Cursor delta Y (debug) |
| `click` | 0/1 | Script | Spike on each proximity left-click |
| `near_state` | 0/1 | Script | Hand in near zone (tuning aid) |

---

## 8. Software components

### 8.1 `project3_connect/sensor_node/sensor_node.ino` (Arduino)

**Responsibilities (implemented):**

- Read **D2** enable from LabJack **FIO4**  
- Pin **13** LED: solid when enabled, slow blink when idle  
- **Does not** read joystick or ultrasonic (LabJack does that)  
- **Does not** use USB serial for Connect

### 8.2 `project3_connect/mouse-control.py` (Nominal Connect script)

**Responsibilities (implemented):**

1. Open LabJack via **labjack-ljm** (single handle)
2. Each loop (~20 Hz): read **AIN0/AIN1**, **FIO5/FIO6** ultrasonic, stream all channels
3. Message bus `system_on` → drive **FIO4** (Arduino enable + LED)
4. When **System on**: map joystick volts → **pynput** relative cursor move; proximity edge → left-click
5. Read Connect UI sliders live (`mouse_speed`, `dead_zone_v`, `near_cm`, `far_cm`, `stable_ms`, `invert_y`)
6. On exit: **FIO4** low, close LabJack

### 8.3 `project3_connect/mouse_tests.py` (TestWorkflow)

See [§12](#12-tests-testworkflow). Uses NominalDAQ for joystick tests; LJM for ultrasonic (releases DAQ handle briefly).

### 8.4 `app.connect`

Script **Project 3 — Mouse control**, Test Workflow **mouse_tests**, sensor plots, **click** / **near_state** plots, **System on** checkbox, and tuning sliders (`mouse_speed` default 80 px/V, dead zone, invert Y, near/far cm, stable ms).

### 8.5 Python dependencies

```text
nominal-instro[daq]
labjack-ljm
pynput
```

---

## 9. Proximity click logic

Use **approach edge** + **hysteresis** + **debounce** (not “hold near = repeat”).

Suggested constants (tune on bench):

| Constant | Example | Meaning |
|----------|---------|---------|
| `NEAR_CM` | 15 | Enter “near” below this |
| `FAR_CM` | 22 | Leave “near” above this (hysteresis) |
| `STABLE_MS` | 100 | Distance stable before arming edge |
| `USE_DISTANCE` | `distance_lj` or `distance_arduino` | Which stream drives click (or require both agree) |

**Logic (pseudocode):**

```text
near = distance < NEAR_CM
far = distance > FAR_CM
if near and not was_near and stable:
    click_once()
was_near = near if near else (was_near and not far)
```

Stream `click=1` for one sample on each click for the plot spike.

**v1 recommendation:** drive click from **`distance_arduino`** until **`distance_lj`** is validated; then require both within **5 cm** for a click.

---

## 10. Mouse movement (implemented)

When **System on** is armed:

1. Map voltage → cursor delta with **dead zone** (center ≈ 2.5 V)
2. Scale **VRx** → ΔX, **VRy** → ΔY (`invert_y` checkbox in Connect)
3. **pynput** relative move each loop (~20 Hz)
4. **`mouse_speed`** slider (default **80 px/V**) tunes feel live in Connect

**macOS:** System Settings → Privacy & Security → **Accessibility** → allow your Connect / Python host.

---

## 11. Implementation phases

Do these **in order**. Each phase has a verifiable win in Connect.

### Phase A — Dual analog (joystick X + Y)

| Step | Action | Pass when |
|------|--------|-----------|
| A1 | Wire **VRy** → **AIN1** + **A1** | — |
| A2 | Extend `sensor_node.ino` to print `a0`, `a1` | Serial shows both changing |
| A3 | `mouse-control.py` streams `joystick_x/y` from LJ + `*_arduino` from serial | Four plots move when stick moves |
| A4 | Add plots to `app.connect` | Live UI |

### Phase B — Ultrasonic on Arduino

| Step | Action | Pass when |
|------|--------|-----------|
| B1 | Wire HC-SR04 to **D7/D8**, power/GND | — |
| B2 | Firmware reports `distance_cm` | Serial sane (2–400 cm) |
| B3 | Stream `distance_arduino` | Plot moves when hand approaches |
| B4 | Proximity click from `distance_arduino` | `click` spikes; Mac clicks (if enabled) |

### Phase C — Ultrasonic on LabJack

| Step | Action | Pass when |
|------|--------|-----------|
| C1 | **Trig** → **FIO5** + **D7**; **Echo** → **D8** + divider → **FIO6** (§6.3.1) | — |
| C2 | Implement LJM pulse read in `mouse-control.py` | `distance_lj` tracks hand |
| C3 | Stream `distance_delta` | Usually &lt; few cm vs Arduino |
| C4 | Click requires both agree (optional) | Fewer false clicks |

### Phase D — Tests + mouse

| Step | Action | Pass when |
|------|--------|-----------|
| D1 | `mouse_tests.py` in Test Workflow | Suite passes on good bench |
| D2 | Mouse mapping + enable gate | Stick moves cursor when armed |
| D3 | Update [LEARNINGS.md](../project2/LEARNINGS.md) or `project3_connect/LEARNINGS.md` | — |

---

## 12. Tests (TestWorkflow)

Planned tests in `mouse_tests.py`:

| Test | Checks |
|------|--------|
| `test_labjack_joystick_x_not_on_rail` | **AIN0** not ~0 or ~5 V at center |
| `test_labjack_joystick_y_not_on_rail` | **AIN1** same |
| `test_joystick_x_motion` | Sweep X span &gt; threshold |
| `test_joystick_y_motion` | Sweep Y span &gt; threshold |
| `test_ultrasonic_in_range` | `distance` via **FIO5/FIO6** in 2–400 cm |
| `test_enable_off_after_tests` | **FIO4** left low |

Reuse patterns from [plant_tests.py](../project2/plant_tests.py) (`RAIL_HIGH_V`, `addComment`, rail hints).

---

## 13. macOS permissions

| Feature | Permission |
|---------|------------|
| Mouse move / click via **pynput** | **Accessibility** |
| LabJack | Driver / Kipling not running during script |

---

## 14. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| **AIN0 or AIN1 stuck at ~5 V** | Missing joystick **GND** or signal on **+5V** row |
| **Y flat, X works** | **VRy** not on **AIN1** row |
| **`distance` flat / NaN** | **FIO6** on divider **tap** (not echo bus); **2 kΩ** to GND; stop other LabJack scripts |
| **`distance` wrong** | Echo wired **direct** to **FIO6** (5 V — fix per §6.3.1); bad divider; aim sensor |
| **No click** | Threshold; use **FAR/NEAR** hysteresis; hand too far |
| **Too many clicks** | Lower sensitivity; edge-only; aim away from desk clutter |
| **LabJack busy** | Stop other scripts using T4 |

---

## 15. File map (planned)

| File | Status | Purpose |
|------|--------|---------|
| `project3_connect/README.md` | **This file** | Implementation plan |
| `project3_connect/sensor_node/sensor_node.ino` | **Built** | Arduino enable + LED only |
| `project3_connect/mouse-control.py` | **Built** | Connect: LabJack streams + mouse/click |
| `project3_connect/mouse_tests.py` | **Built** | TestWorkflow |
| `project3_connect/TESTING.md` | **Built** | Connect UI + mouse bench steps |
| `project3_connect/app.connect` | **Built** | Scripts, plots, tuning sliders, tests |
| `requirements.txt` | **Built** | `nominal-instro`, `labjack-ljm`, `pynput` |

**Project 2 files stay as-is** — they remain your reference bench for enable + single-axis bring-up.

---

## Relation to Project 2

| Project 2 | Project 3 (this plan) |
|-----------|-------------------------|
| One analog axis (**VRx**) | Two axes (**VRx**, **VRy**) |
| `joystick_voltage` | `joystick_x`, `joystick_y` |
| No ultrasonic | **`distance`** on LabJack **FIO5/FIO6** |
| Plant LED behavior | Optional; focus on mouse + click |
| `plant_tests.py` | `mouse_tests.py` + cross-check tests |

You already proved Connect + LabJack + Arduino + tests work. This project **extends** that stack with a second axis, dual distance paths, and operator-facing mouse/click behavior — with **graphs and tests for all of it**.

---

*Run **Project 3 — Mouse control** in Connect. Confirm sensor plots, then arm **System on** to move the cursor and trigger proximity clicks. See [TESTING.md](TESTING.md) for the bench checklist.*
