# Humanoid Prototype (ARIA)
### Autonomous Responsive Intelligent Assistant

A fully functional voice-controlled humanoid robot with 22 servo motors, capable of natural language interaction, autonomous obstacle-aware navigation, and Bluetooth-based manual control. Built at PHN Technology (Army Public School).

## How It Works

The Raspberry Pi captures voice input via a USB microphone, transcribes it using OpenAI Whisper, and sends it to GPT to determine whether the instruction is a movement command or a conversational response. Movement commands are sent over serial to the Arduino Nano, which drives the 22 servo motors through two PCA9685 servo drivers. Four ultrasonic sensors on the robot's head continuously scan all directions and send obstacle warnings back to the Pi.

In Bluetooth mode, the BLE Controller app (available on Google Play Store) connects directly to the HC-05 module on the Arduino and sends movement commands. The Pi suspends all voice input and obstacle detection and announces the switch audibly.

## Two Modes

| Mode | How it works |
|------|-------------|
| Voice Mode | Pi captures audio → Whisper → GPT → serial command → Arduino → servos |
| Bluetooth Mode | BLE Controller app → HC-05 → Arduino → servos. Pi suspended. |

## Hardware

**Raspberry Pi side**
- Raspberry Pi (any model with USB)
- USB Microphone
- Speaker Module

**Arduino Nano side**
- Arduino Nano
- 2x PCA9685 Servo Drivers (I2C addresses 0x40 and 0x41)
- 22x Servo Motors
- 4x Ultrasonic Sensors (front, back, left, right)
- HC-05 Bluetooth Module

## Project Structure

```
humanoid_prototype/
├── raspberry_pi/
│   ├── main.py              (run this on the Raspberry Pi)
│   └── requirements.txt
├── arduino_nano/
│   └── arduino_nano.ino     (flash this onto the Arduino Nano)
└── README.md
```

## Setup

**Raspberry Pi**
1. Connect to internet via mobile hotspot
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Update `SERIAL_PORT`, `WIFI_SSID`, `WIFI_PASSWORD`, and `openai.api_key` in `main.py`
4. Run:
```bash
python3 main.py
```

**Arduino Nano**
1. Install libraries in Arduino IDE: `Adafruit PWM Servo Driver`
2. Flash `arduino_nano.ino` to the Arduino Nano
3. Connect HC-05 TX to Nano RX and HC-05 RX to Nano TX

**Bluetooth Mode**
1. Download **BLE Controller - Arduino ESP32** from Google Play Store
2. Pair your phone with the HC-05 module
3. Say "bluetooth mode" to the robot to switch modes, or say "voice mode" to switch back

## Commands (Voice Mode)

| Say | Action |
|-----|--------|
| "move forward" | walks forward |
| "move backward" | walks backward |
| "turn left" | turns left |
| "turn right" | turns right |
| "wave" | waves hand |
| "stop" | returns to neutral |
| "bluetooth mode" | switches to Bluetooth mode |
| "voice mode" | switches back to voice mode |

## Tech Stack
Raspberry Pi, Arduino Nano, OpenAI Whisper, GPT API, Speech Recognition, NLP, Motor Control, Obstacle Avoidance, Bluetooth Communication, PCA9685 Servo Driver, Python, Embedded C
