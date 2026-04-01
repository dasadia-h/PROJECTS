# Smart Home Automation System

A switchboard-mounted automation system that controls physical switches remotely using servo motors, without requiring any rewiring or infrastructure changes. Built at PHN Technology (SSRVM).

## How It Works

Servo motors are positioned directly over each switch on an existing switchboard and physically flip them on or off. The Arduino accepts commands from two sources in parallel — an IR remote via an IR receiver, and a mobile app via the HC-05 Bluetooth module.

## Hardware

- Arduino Uno
- 6x Servo Motors
- IR Receiver Module
- HC-05 Bluetooth Module

## Pin Mapping

| Component | Pin |
|-----------|-----|
| Servo 1 (Switch 1) | D3 |
| Servo 2 (Switch 2) | D5 |
| Servo 3 (Switch 3) | D6 |
| Servo 4 (Switch 4) | D9 |
| Servo 5 (Switch 5) | D10 |
| Servo 6 (Switch 6) | D11 |
| IR Receiver | D2 |
| HC-05 TX | D0 (RX) |
| HC-05 RX | D1 (TX) |

## Project Structure

```
smart_home_automation/
├── smart_home_automation/
│   └── smart_home_automation.ino    (main sketch)
├── ir_code_finder/
│   └── ir_code_finder.ino           (run this first to find your remote's codes)
└── README.md
```

## Getting Started

### Step 1 — Find your IR remote's button codes

Every IR remote sends different hex codes for each button. Before uploading the main sketch you need to find out what codes your specific remote sends.

1. Open `ir_code_finder/ir_code_finder.ino` in Arduino IDE
2. Upload it to your Arduino with the IR receiver connected to pin 2
3. Open Serial Monitor at **9600 baud**
4. Point your remote at the IR receiver and press each button one at a time
5. Each button press will print something like:
```
button code: 0xFF30CF
press the next button...
```
6. Write down the code for each button you want to use, in order

### Step 2 — Update the main sketch

Open `smart_home_automation/smart_home_automation.ino` and replace the placeholder values in the `irCodes[]` array with your actual codes:

```cpp
const unsigned long irCodes[] = {
  0xFF30CF,   // button that controls switch 1
  0xFF18E7,   // button that controls switch 2
  0xFF7A85,   // button that controls switch 3
  0xFF10EF,   // button that controls switch 4
  0xFF38C7,   // button that controls switch 5
  0xFF5AA5    // button that controls switch 6
};
```

The order matters — the first code in the array controls switch 1, the second controls switch 2, and so on.

### Step 3 — Upload the main sketch

Upload `smart_home_automation.ino` to your Arduino and open Serial Monitor at 9600 baud to see switch state changes as you press buttons.

## Bluetooth App

Download **BLE Controller - Arduino ESP32** from the Google Play Store. Pair your phone with the HC-05 module and use the following commands:

| Command | Action |
|---------|--------|
| `1` to `6` | toggle switch 1-6 |
| `A` to `F` | turn switch 1-6 ON |
| `a` to `f` | turn switch 1-6 OFF |
| `X` | turn all switches OFF |

## Libraries Required

Install these via Arduino IDE Library Manager:
- **IRremote** by shirriff
- **Servo** (built-in, no install needed)

## Tech Stack
Arduino, Servo Motor Control, PWM Signal Control, IR Signal Processing, Bluetooth Communication, Embedded C
