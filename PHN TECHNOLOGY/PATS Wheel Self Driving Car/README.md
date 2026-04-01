# PATS Wheel Self Driving Car

A self-driving car mounted on PATS wheels — a 3D-printable TPU wheel designed to climb stairs and navigate uneven surfaces. Built at PHN Technology (SSRVM).

## How It Works

The car uses 4 ultrasonic sensors total. A fixed front sensor continuously checks for obstacles while driving forward. When something is detected, two servo-mounted side sensors sweep left and right to find the clearest path. A fixed rear sensor guards the car while reversing.

## Sensor Setup

| Sensor | Mount | Purpose |
|--------|-------|---------|
| Front ultrasonic | Fixed | detects obstacles while moving forward |
| Rear ultrasonic | Fixed | detects obstacles while reversing |
| Left ultrasonic | Servo motor | sweeps left side when front is blocked |
| Right ultrasonic | Servo motor | sweeps right side when front is blocked |

## Movement Logic

| Situation | Action |
|-----------|--------|
| Front clear | keep moving forward |
| Front blocked, left clear | turn left |
| Front blocked, right clear | turn right |
| Front blocked, both sides clear | turn left by default |
| Front, left and right blocked, rear clear | reverse then turn right |
| All directions blocked | spin right until front clears |

## Sweep Pattern

When an obstacle is detected at the front, each side sensor sweeps through 3 positions:
- Facing forward (90°)
- Facing sideways (135° left / 45° right)
- Facing rear (180° left / 0° right)

If any position in the sweep detects an obstacle, that side is marked as blocked.

## Hardware

- Arduino Uno
- 4x HC-SR04 Ultrasonic Sensors
- 2x Servo Motors (for left and right side sensors)
- L298N Motor Driver
- 2x DC Motors
- PATS Wheels (3D printed in TPU)
- 9V Battery

## Pin Mapping

| Component | Pin |
|-----------|-----|
| Left Motor IN1 | D2 |
| Left Motor IN2 | D3 |
| Right Motor IN1 | D4 |
| Right Motor IN2 | D5 |
| Left Motor Speed (PWM) | D9 |
| Right Motor Speed (PWM) | D10 |
| Front Ultrasonic Trig | D6 |
| Front Ultrasonic Echo | D7 |
| Rear Ultrasonic Trig | D8 |
| Rear Ultrasonic Echo | D13 |
| Left Ultrasonic Trig | A2 |
| Left Ultrasonic Echo | A3 |
| Right Ultrasonic Trig | A4 |
| Right Ultrasonic Echo | A5 |
| Left Servo | A0 |
| Right Servo | A1 |

## Tuning

```cpp
// minimum distance in cm before the car treats something as an obstacle
const int safeDistance = 25;

// motor speeds (0 to 255)
const int driveSpeed = 180;
const int turnSpeed  = 150;
```

## Libraries Required

Install via Arduino IDE Library Manager:
- **Servo** (built-in, no install needed)

## Setup

1. Open `pats_wheel_car.ino` in Arduino IDE
2. Upload to Arduino Uno
3. Open Serial Monitor at 9600 baud to watch distance readings and decisions live

## PATS Wheel

PATS (Passive Adaptive Terrain System) wheels are 3D printed in TPU, a flexible filament that allows the wheel spokes to deform and grip over stairs and uneven terrain. STL files: https://www.thingiverse.com/thing:4823849

## Tech Stack
Arduino, Ultrasonic Sensing, Servo Motor Control, Autonomous Navigation, Motor Control (L298N), 3D Printing (TPU), Obstacle Avoidance, Embedded C
