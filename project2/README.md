# Project 2: Arduino + LabJack + Nominal Connect (full guide)

**Joystick edition** — for the Elegoo Super Starter Kit (no standalone potentiometer required).

This document walks you through everything from zero. If you completed **Step 1** (upload `plant.ino` and the 5V→D2 jumper test), you can jump to **Step 2** below.

---

## Table of contents

1. [What you are building](#1-what-you-are-building)
2. [Words worth knowing](#2-words-worth-knowing)
3. [Parts checklist](#3-parts-checklist)
4. [Step 1 — Arduino software and firmware](#4-step-1--arduino-software-and-firmware)
5. [Step 2 — Wiring (joystick + LabJack + Arduino)](#5-step-2--wiring-joystick--labjack--arduino)
6. [Step 3 — Nominal Connect UI](#6-step-3--nominal-connect-ui)
7. [Step 4 — Run the experiment](#7-step-4--run-the-experiment)
8. [Troubleshooting](#8-troubleshooting)
9. [File reference](#9-file-reference)

---

## 1. What you are building

You have three pieces working together:

| Piece | Role | Analogy |
|-------|------|---------|
| **Nominal Connect** (on your Mac) | On/off switch + live graphs | Control room |
| **LabJack T4** | Sends “run” to Arduino; reads stick voltage | Operator panel wired to the machine |
| **Arduino UNO** | Blinks or runs when told; reads joystick | The “machine” on the bench |

```
┌─────────────────┐     FIO4 (enable)      ┌──────────────────────────┐
│  LabJack T4     │ ─────────────────────► │  Arduino UNO             │
│                 │                        │  D2 = enable input       │
│                 │ ◄── AIN0 (voltage)     │  A0 = joystick X (VRx)   │
└────────┬────────┘                        └──────────────────────────┘
         │ USB                                      ▲
         ▼                                          │ joystick VRx
┌─────────────────┐                                 │
│  Nominal Connect │  toggle "System on"             │
└─────────────────┘  plot "joystick_voltage" ──────┘
```

**When “System on” is OFF:** Arduino built-in LED (pin 13) blinks slowly (~once per second).

**When “System on” is ON:** LED stays solid; moving the joystick **left/right** changes voltage on the plot (and optional LED on pin D9).

---

## 2. Words worth knowing

| Term | Meaning |
|------|---------|
| **GND / ground** | The 0 V reference. All voltages are measured relative to ground. |
| **Shared ground** | LabJack GND, Arduino GND, and joystick GND connected together with wires. **Required.** |
| **Digital pin** (e.g. **D2**) | On or off (HIGH / LOW). Used for **enable**. |
| **Analog pin** (e.g. **A0**) | Voltage level (~0–5 V). Used for **joystick X (VRx)**. |
| **FIO4** | LabJack digital output on the T4 screw terminals; drives Arduino D2 when the script turns the system on. |
| **AIN0** | LabJack analog **input**; reads the same voltage as Arduino A0. |
| **VRx** | Joystick **X axis** output (voltage changes as you move stick left/right). |
| **Jumper wire** | Short wire with a metal pin at each end for the breadboard. |
| **Breadboard** | Plastic board with holes; connects components without soldering. |
| **Row** | Five holes connected together (e.g. row 10: holes a10–e10 are one node). |
| **Rail** | Long strip along the edge (+ or −). We use the **−** rail for **GND**. |

---

## 3. Parts checklist

Gather these before Step 2:

| # | Item | What it looks like |
|---|------|---------------------|
| 1 | Arduino UNO R3 | Blue board, “ELEGOO” or “Arduino UNO” |
| 2 | LabJack T4 | Often in a clear/red case, USB to Mac |
| 3 | **Joystick module** | Small black PCB, **thumb stick** on top, **5 pins** on one side |
| 4 | Breadboard | White board with holes (mini size is fine) |
| 5 | Jumper wires | ~8 male–male wires |
| 6 | USB cables | One for UNO, one for LabJack |

**Optional:** LED + 220 Ω resistor on Arduino **D9** (extra brightness when running).

**You do NOT need:** a round twist potentiometer. The joystick replaces it.

### Identify your joystick

In the Super Starter Kit it is usually:

- Black plastic breakout board
- Metal stick you push with your thumb
- Pins labeled something like: **GND**, **+5V**, **VRx**, **VRy**, **SW**

We use **VRx** (X axis = left/right). **VRy** and **SW** stay unconnected for this project.

---

## 4. Step 1 — Arduino software and firmware

### 4.1 Install Arduino IDE (one-time)

1. Go to [https://www.arduino.cc/en/software](https://www.arduino.cc/en/software)
2. Download **Arduino IDE 2** for Mac
3. Install and open it

### 4.2 Plug in the Arduino and select board/port

1. Connect the UNO to your Mac with the USB cable
2. Menu **Tools → Board → Arduino AVR Boards → Arduino Uno**
3. Menu **Tools → Port** → select the **new** port that appeared when you plugged in  
   - Examples: `/dev/cu.usbmodem14101`, `/dev/cu.wchusbserial110`  
   - If no port appears: try another USB cable (some cables are charge-only)

### 4.3 Open and upload the project firmware

1. In Finder, open this file in Arduino IDE:  
   **`Nominal/projects/project2/plant/plant.ino`**
2. Click the **Upload** button (right arrow →)
3. Wait until the status bar says **Done uploading**

### 4.4 Quick test (proves the code works — no LabJack yet)

1. **Unplug the LabJack** from USB (only Arduino plugged in is OK)
2. Take **one** jumper wire:
   - One end → Arduino **5V** pin  
   - Other end → Arduino **D2** pin  
3. **Expected:** built-in LED near pin **13** turns **solid ON**
4. **Remove** that jumper completely
5. **Expected:** LED **blinks slowly** (about once per second)

✅ If that works, **Step 1 is done.**

> **Important:** After Step 2, you will connect **LabJack FIO4** (or another **FIO4–FIO7** terminal) to **D2**. Do **not** also leave the **5V → D2** test jumper in place at the same time.

---

## 5. Step 2 — Wiring (joystick + LabJack + Arduino)

Take your time. **Unplug USB** from both Arduino and LabJack while inserting wires (safer and less confusing).

### 5.1 What “shared ground” means (read this once)

Both the Arduino and LabJack measure voltage **between two points**. “5 V” means “5 V above **ground**.”

- Arduino has a **GND** pin  
- LabJack has a **GND** screw terminal  
- Joystick has a **GND** pin  

Those must be **the same 0 V**. You achieve that by wiring all of them to the **same breadboard − rail**:

```
LabJack GND ────┐
                ├──► breadboard − rail (GND)
Arduino GND ────┤
                │
joystick GND ───┘
```

**You do not** need to connect Arduino **5V** to LabJack **5V** for this project. The joystick gets power from the **Arduino 5V** pin only.

---

### 5.2 Breadboard basics (30 seconds)

```
     + rail  (we won't use for GND in this project)
     − rail  ◄── use this entire strip as GND
     
     a   b   c   d   e   |   f   g   h   i   j
     ●───●───●───●───●   |   ●───●───●───●───●  ← one "row"
```

- **− rail:** all holes along that blue (or −) line are connected — put every **GND** wire here  
- **One row** (e.g. a10–e10): use as a junction for **VRx + A0 + AIN0**  
- **Center trench:** plug the joystick **across** the trench so **each pin is in a different row**

---

### 5.3 Find pins on the Arduino UNO

Hold the board with the **USB connector at the bottom** (typical orientation).

| You need | Label on board | Notes |
|----------|----------------|--------|
| Ground | **GND** | There are 2–3; any works |
| Power for joystick | **5V** | |
| Joystick signal | **A0** | Under “ANALOG IN” |
| Enable from LabJack | **D2** | On the long **DIGITAL** row (pin 2) |
| Optional LED | **D9** | |

---

### 5.4 Find terminals on the LabJack T4

Use the screw terminals on the device (small flat screwdriver).

#### Why you see FIO4–FIO7, not “FIO0”

On the **LabJack T4**, the **screw terminals** for flexible I/O are labeled:

**FIO4**, **FIO5**, **FIO6**, **FIO7**

There is **no FIO0** on that screw-terminal block — that is normal for the T4, not a mistake in the guide. This project uses **FIO4** by default. You can use **FIO5**, **FIO6**, or **FIO7** instead if you prefer; just wire **that** terminal to Arduino **D2** and change `ENABLE_LABJACK_LINE` in `arduino-plant.py` to match (e.g. `"FIO5"`).

Analog inputs on the same edge are usually **AIN0**, **AIN1**, **AIN2**, **AIN3** (those names *do* appear on the T4).

| Terminal | Connect to |
|----------|------------|
| **GND** | Breadboard **−** rail |
| **FIO4** (or FIO5/FIO6/FIO7) | Arduino **D2** |
| **AIN0** | Same breadboard **row** as joystick **VRx** and Arduino **A0** |

Tighten screws so the wire is held firmly (copper in the jaw, not insulation only).

**Safety:** Do **not** connect Arduino **5V** to any **FIO** or **AIN** terminal. FIO is output (3.3 V); AIN is a measurement input.

---

### 5.5 Plug the joystick into the breadboard

1. Orient the module so the **pins point down** into the breadboard  
2. Straddle the **center gap** so each of the 5 pins goes into a **different row**  
3. Read the text printed on the PCB next to each pin  

Typical order (yours may differ — **trust the labels on your board**):

```
  GND   +5V   VRx   VRy   SW
   │     │     │     │     │
   ▼     ▼     ▼     ▼     ▼
  row   row   row   row   row  (five separate rows)
```

Leave **VRy** and **SW** in the breadboard with **nothing else** connected to those rows (that is fine).

---

### 5.6 Wire-by-wire instructions

Do these **in order**. Use any jumper colors; black/brown for GND is a nice habit.

---

#### Wire 1 — LabJack ground → breadboard

| From | To |
|------|-----|
| LabJack terminal **GND** | Any hole on breadboard **−** rail |

---

#### Wire 2 — Arduino ground → same breadboard ground

| From | To |
|------|-----|
| Arduino pin **GND** | Another hole on the **same − rail** as Wire 1 |

✅ LabJack and Arduino now **share ground**.

---

#### Wire 3 — Joystick ground → same breadboard ground

| From | To |
|------|-----|
| Joystick pin **GND** | Same breadboard **−** rail |

✅ Joystick is on the same ground as the other two.

---

#### Wire 4 — Joystick power

| From | To |
|------|-----|
| Joystick pin **+5V** (or **5V** or **VCC**) | Arduino pin **5V** |

This powers the electronics inside the joystick module.

---

#### Wires 5 & 6 & 7 — Joystick X signal (VRx) → Arduino and LabJack

Pick an empty row (example: row **10** — holes **a10, b10, c10, d10, e10** are all connected).

| From | To |
|------|-----|
| Joystick pin **VRx** | Any hole in row 10 (e.g. **e10**) |
| Arduino pin **A0** | **Same row 10** (e.g. **a10**) |
| LabJack terminal **AIN0** | **Same row 10** (e.g. **c10**) |

Three wires meet on **one row**. That voltage is what Nominal plots as **joystick_voltage**.

---

#### Wire 8 — Enable (LabJack tells Arduino to run)

| From | To |
|------|-----|
| LabJack terminal **FIO4** | Arduino pin **D2** |

When the Connect script turns the system on, FIO4 goes high (~3.3 V), which Arduino treats as ON.

> Using **FIO5** instead? Wire **FIO5 → D2** and set `ENABLE_LABJACK_LINE = "FIO5"` at the top of `arduino-plant.py`.

---

### 5.7 Optional — extra LED on pin D9

| From | To |
|------|-----|
| Arduino **D9** | 220 Ω resistor → LED **long leg (+)** |
| LED **short leg (−)** | Breadboard **−** rail (GND) |

When the system is ON, LED brightness follows stick left/right.

---

### 5.8 Full wiring diagram

```
                         LABJACK T4                          ARDUINO UNO
                         ┌─────────┐                         ┌─────────┐
              Wire 1 ────┤ GND     │                         │ GND     ├──── Wire 2 ───┐
                         │         │                         │ 5V      ├── Wire 4 ─┐ │
              Wire 8 ────┤ FIO4    ├─────────────────────────┤ D2      │           │ │
                         │         │                         │ A0      ├───┐       │ │
              Wire 7 ────┤ AIN0    ├─────┐                   │ (D9)    │   │       │ │
                         └─────────┘     │                   └─────────┘   │       │ │
                                         │                                 │       │ │
     BREADBOARD                          │                                 │       │ │
     ┌───────────────────────────────────┼─────────────────────────────────┼───────┼──┐
     │  − rail (GND) ◄───────────────────┼─────────────────────────────────┘       │  │
     │     ▲        ▲                    │                                         │  │
     │     │        │                    │                                         │  │
     │  LabJack   Arduino              row 10                                      │  │
     │   GND       GND              VRx + A0 + AIN0                                │  │
     │     ▲        ▲                    ▲                                         │  │
     │     │        │                    │                                         │  │
     │  joystick GND (Wire 3)            │                                         │  │
     │                                   │                                         │  │
     │  joystick +5V ────────────────────┴──────────────── Arduino 5V (Wire 4)   │  │
     │                                                                               │  │
     │  [ Joystick module:  GND | +5V | VRx | VRy | SW ]                             │  │
     │                              ▲                                                │  │
     │                              └── only VRx wired to row 10                   │  │
     └───────────────────────────────────────────────────────────────────────────────┘  │
```

---

### 5.9 Step 2 checklist (check every box)

- [ ] **Wire 1:** LabJack **GND** → breadboard **−** rail  
- [ ] **Wire 2:** Arduino **GND** → same **−** rail  
- [ ] **Wire 3:** Joystick **GND** → same **−** rail  
- [ ] **Wire 4:** Joystick **+5V** → Arduino **5V**  
- [ ] **VRx, A0, AIN0** all on the **same breadboard row**  
- [ ] **Wire 8:** LabJack **FIO4** (or your chosen FIO4–FIO7) → Arduino **D2**  
- [ ] **No** wire from Arduino **5V** to **D2** (remove Step 1 test jumper)  
- [ ] **VRy** and **SW** not connected to anything else  
- [ ] LabJack screws snug  
- [ ] USB plugged into **Arduino** and **LabJack**

---

### 5.10 After wiring — what should happen (before Connect)

1. Plug in **Arduino** USB → LED on pin 13 should **blink slowly** (system idle).  
2. Plug in **LabJack** USB.  
3. Moving the stick **without** Connect running does **not** change the blink yet — that is normal.  
4. You are ready for **Step 3**.

---

## 6. Step 3 — Nominal Connect UI (checkbox / toggle)

Nominal Connect does **not** call your Python script directly when you click a checkbox. Instead, the UI publishes a **message** on the **message bus**, and `arduino-plant.py` **subscribes** to that topic and turns the LabJack enable line on or off.

This matches [Nominal’s message bus docs](https://docs.nominal.io/connect/documentation/message-bus/message-bus): checkboxes and toggle switches use **`on_toggle_action`** to publish when you flip them.

### 6.1 What you are configuring (three pieces)

| Piece | Value for this project | Why |
|-------|------------------------|-----|
| **Widget id** | `system_on` | Identifies the checkbox; appears as `widget_id` in messages |
| **Message topic** | `script/project2/system_on` | Script subscribes to this exact string |
| **Message contents** | `enabled: $system_on` | Sends `true`/`false` when you toggle (variable expansion) |

The script constant `SYSTEM_ON_TOPIC` in `arduino-plant.py` must match your **topic** (`script/project2/system_on`).

---

### 6.2 Configure the checkbox in the Connect editor (GUI)

Your `app.connect` already has a **Form** pane with a checkbox. Finish configuring it as follows.

#### Step A — Open the app editor

1. Open **`Nominal/projects/app.connect`** in the **Nominal Connect** app editor (not just the runtime view).

#### Step B — Select the checkbox

1. Find the **Form** pane (next to the script table / table area).  
2. Click the **checkbox** widget (it may still say “Checkbox”).

#### Step C — Basic widget settings

In the widget properties panel:

| Field | Set to |
|-------|--------|
| **Id** (or widget id) | `system_on` |
| **Label** | `System on` |

The **id** must be exactly `system_on` (lowercase, underscore).

#### Step D — Message bus action on toggle

Find **On toggle action** (or **on_toggle_action**) — this is the message sent when the user checks/unchecks the box.

1. Add (or edit) an action of type **Message**.  
2. Set **Topic** to:

   ```
   script/project2/system_on
   ```

3. Set **Contents** (message payload) to include whether the system is on. Recommended setup using **variable expansion**:

   | Key | Value |
   |-----|--------|
   | `enabled` | `$system_on` |

   The `$` tells Connect to substitute the current value of the variable **`system_on`** when the message is published (see Nominal docs: *Variable Expansion*).

   Connect will also add **`widget_id`** automatically (you do not need to type that).

   **Example of what gets published when you turn the system on:**

   ```json
   {
     "widget_id": "system_on",
     "enabled": true
   }
   ```

4. Save the app.

#### Step E — Variable `system_on` (if the editor asks for one)

Some Connect versions link the checkbox to a **variable** with the same id:

- **Value id:** `system_on`  
- **Type:** boolean  

If your checkbox and `$system_on` in the message contents share that value id, toggling the box updates the variable **and** publishes the message with the correct `enabled` value.

If you cannot find a separate variables panel, configuring **id** + **on_toggle_action** + `$system_on` in contents is still the right pattern.

---

### 6.3 Alternative widgets (same idea)

| Widget | When it fires | Action field |
|--------|----------------|--------------|
| **Checkbox** | Each check/uncheck | `on_toggle_action` |
| **Toggle switch** | Each on/off | `on_toggle_action` |
| **Button** | Each click only | `on_click_action` (not ideal for on/off — prefer checkbox/toggle) |

For this lab, use a **checkbox** or **toggle switch**, not a momentary button.

---

### 6.4 What is already in `app.connect` (YAML)

If the editor loads the repo file successfully, the checkbox should already look like this (you can compare):

```yaml
- input: checkbox
  id: system_on
  label: System on
  on_toggle_action:
  - _kind: message
    topic: script/project2/system_on
    contents:
      enabled: $system_on
```

If your GUI shows empty **topic** or **id**, fill them in manually using §6.2.

---

### 6.5 How the script uses the message bus

While the script runs, it:

1. Opens `connect_python.MessageBus`  
2. Subscribes to `script/project2/system_on`  
3. On each loop, reads any pending UI messages and sets **on/off** from `enabled` in the message  
4. Drives LabJack **FIO4** and streams `system_on` / `joystick_voltage`

When you toggle **System on**, the script log should show something like:

```text
UI message: {'widget_id': 'system_on', 'enabled': True}
System ON (FIO4=1)
```

---

### 6.6 Verify the UI **before** running the full experiment

1. Open the Connect **runtime** (live app).  
2. Run **arduino-plant** from the script table.  
3. Toggle **System on** once.  
4. In the script **output / log**, look for `UI message:` with `enabled: true` or `false`.  

| Result | Meaning |
|--------|---------|
| You see `UI message:` when toggling | Message bus is wired correctly |
| No `UI message:` when toggling | Topic mismatch, or `on_toggle_action` not saved — recheck §6.2 |
| Message appears but LED unchanged | Wiring §5 (FIO4 → D2, shared GND), not the checkbox |

---

### 6.7 Other pieces already in the repo

| Item | Detail |
|------|--------|
| Script | `project2/arduino-plant.py` — **Project 2 — Arduino plant** |
| Plot | **Joystick voltage (V)** — `joystick_voltage` |
| Plot | **System on / enable** — `system_on` |
| Table | Bound to `arduino-plant` |

---

### 6.8 Close other LabJack programs

Before Step 4:

- Quit **Kipling** or any other app using the T4  
- Run only **arduino-plant**, not **hello-world**, at the same time

---

## 7. Step 4 — Run the experiment

### 7.1 Before you click Run

| Check | |
|-------|---|
| Step 1 | `plant.ino` uploaded; Step 1 LED test passed |
| Step 2 | Checklist in §5.9 complete; no 5V→D2 jumper |
| Step 3 | Checkbox configured (§6): topic `script/project2/system_on`, id `system_on` |
| Hardware | Arduino + LabJack USB connected |

### 7.2 Start the script

1. Open **Nominal Connect** with your `app.connect` app  
2. Find the **System on** control (leave it **OFF** at first)  
3. In **Script Controls**, click **Run** on **Project 2 — Arduino plant**  
4. Watch the script log for: `Project 2: Arduino plant — starting`  
5. If you see a LabJack connection error → see [§8 Troubleshooting](#8-troubleshooting)

### 7.3 What to try (in order)

| Step | You do | You should see |
|------|--------|----------------|
| 1 | Leave **System on** OFF | Arduino LED **blinks** slowly; plot `system_on` = **0** |
| 2 | Turn **System on** **ON** | LED **solid**; log may say `System ON (FIO4=1)` |
| 3 | Move joystick **left / right** | Plot **Joystick voltage (V)** goes up and down (~0–3.3 V or similar) |
| 4 | Turn **System on** OFF | LED **blinks** again; `system_on` returns to **0** |

**Note:** The plot may move slightly even when OFF, because the joystick is always powered and AIN0 is always wired. The important checks are **LED behavior** and **`system_on`** matching your toggle.

### 7.4 Stop the script

When finished, **stop** the script in Connect. The script sets **FIO4 LOW** so the plant is not left enabled.

### 7.5 Pass / fail summary

| Result | Meaning |
|--------|---------|
| ✅ PASS | Toggle controls LED; stick moves `joystick_voltage` when ON |
| ❌ Toggle does nothing | Wrong control id or script not running |
| ❌ LED never solid | FIO4→D2, shared GND, or 5V still on D2 |
| ❌ Plot flat | VRx not on same row as A0 and AIN0; or joystick +5V/GND |

---

## 8. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| `Failed to connect to LabJack` | USB, driver, or another app using T4 | Replug USB; quit Kipling; run only **arduino-plant** |
| Toggle does nothing | Topic or id mismatch | Topic must be `script/project2/system_on`; widget id `system_on`; see §6.6 |
| LED always solid | **5V → D2** test jumper still on | Remove jumper; use only **FIO4 → D2** |
| LED always blinking | Enable never reaches D2 | Check **FIO4 → D2**; turn **System on** ON while script runs |
| `joystick_voltage` flat | Wrong signal pin | Use **VRx**, not VRy; same row as **A0** and **AIN0** |
| Plot moves, LED won’t go solid | Ground or D2 | Verify §5.9 ground wires; FIO4 → D2 |
| Stick works on Y but not X | Using wrong output | Move stick **left/right**; or wire **VRy** to row 10 instead of VRx |
| Arduino port missing | Bad USB cable / driver | Try another cable; check **Tools → Port** |
| Script stops after 5 min | `DURATION_SECONDS = 300` in script | Normal; click Run again or increase timeout in `arduino-plant.py` |

---

## 9. File reference

| File | Purpose |
|------|---------|
| `plant/plant.ino` | Firmware — upload with Arduino IDE |
| `arduino-plant.py` | Nominal Connect script (LabJack + streaming) |
| `README.md` | This guide |
| `../app.connect` | Connect app layout, scripts, plots |

---

## What you learned

- Upload and test Arduino firmware  
- Share ground between two USB devices and a module  
- Use a joystick as an analog sensor (**VRx**)  
- Command hardware from Nominal Connect (`system_on` → FIO4)  
- Stream telemetry (`joystick_voltage`) to verify behavior  

**Next ideas:** wire **VRy** to a second analog channel; use joystick **SW** as a digital input; stream Arduino USB serial in Python.

---

*If you get stuck, note which step you are on and what the LED and plots are doing — that narrows it down quickly.*
