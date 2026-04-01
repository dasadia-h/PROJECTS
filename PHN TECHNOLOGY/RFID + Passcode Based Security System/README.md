# RFID + Password Based Security System

A smart door lock supporting two authentication methods — RFID card scan or keypad passcode. Built at PHN Technology (SSRVM).

## How It Works

Both the RFID reader and keypad are mounted outside the door. The LCD provides real-time feedback for every interaction. On successful authentication, a servo motor retracts the latch to unlock the door. An IR sensor on the door frame detects when the door closes and automatically re-locks. A push button mounted inside the room lets occupants exit without needing to authenticate.

## Authentication Methods

| Method | How to use |
|--------|-----------|
| RFID card | tap your registered card on the reader |
| Keypad passcode | type your PIN and press `#` to confirm, `*` to clear |
| Exit button | press the button inside the room to unlock from within |

## Hardware

- Arduino Uno
- RC522 RFID Reader
- 4x4 Keypad
- 16x2 LCD Display (I2C)
- Servo Motor (door latch)
- IR Sensor (door frame)
- Push Button (inside room)

## Pin Mapping

| Component | Pin |
|-----------|-----|
| RC522 SDA | D10 |
| RC522 SCK | D13 |
| RC522 MOSI | D11 |
| RC522 MISO | D12 |
| RC522 RST | D9 |
| Servo Motor | D6 |
| IR Sensor | D7 |
| Exit Button | D8 |
| Keypad Row 1-4 | A0, A1, A2, A3 |
| Keypad Col 1-4 | A4, A5, D2, D3 |
| LCD SDA | A4 |
| LCD SCL | A5 |

## Project Structure

```
rfid_security_system/
├── rfid_security_system/
│   └── rfid_security_system.ino    (main sketch)
├── rfid_uid_finder/
│   └── rfid_uid_finder.ino         (run this first to find your card's UID)
└── README.md
```

## Getting Started

### Step 1 — Find your RFID card's UID

Every RFID card has a unique ID. You need to find yours before the system can recognise it.

1. Open `rfid_uid_finder/rfid_uid_finder.ino` in Arduino IDE
2. Upload it to your Arduino
3. Open Serial Monitor at **9600 baud**
4. Tap your RFID card on the reader
5. The Serial Monitor will print something like:
```
card UID: A1 B2 C3 D4
copy this UID into registeredUID in rfid_security_system.ino
```
6. Copy that UID

### Step 2 — Update the main sketch

Open `rfid_security_system/rfid_security_system.ino`. At the top of the file you will find clearly marked sections for everything you need to configure:

**Set your passcode** — replace `YOUR_PASSCODE_HERE` with any combination of digits:
```cpp
const String correctPassword = "YOUR_PASSCODE_HERE";
```

**Set your RFID card UID** — paste the UID exactly as printed by the finder sketch:
```cpp
const String registeredUID = "A1 B2 C3 D4";
```

**Adjust servo angles if needed** — default is 0 for locked and 90 for unlocked. Change these if your latch mechanism needs a different range:
```cpp
const int lockedAngle   = 0;
const int unlockedAngle = 90;
```

**Adjust unlock duration if needed** — default is 5 seconds. Increase if you need more time to open the door:
```cpp
const int unlockDuration = 5000;
```

**Registering multiple cards** — if you want more than one RFID card to work, a commented-out multi-card example is included directly in the sketch. Uncomment it and add your card UIDs to the array.

### Step 3 — Upload the main sketch

Upload `rfid_security_system.ino` to your Arduino. The LCD will show "system ready" and you're good to go.

## Libraries Required

Install these via Arduino IDE Library Manager:
- **MFRC522** by GithubCommunity
- **LiquidCrystal I2C** by Frank de Brabander
- **Keypad** by Mark Stanley
- **Servo** (built-in, no install needed)

## Tech Stack
Arduino, RFID Authentication, Servo Motor Control, IR Sensing, Keypad Input, LCD Display, Embedded C
