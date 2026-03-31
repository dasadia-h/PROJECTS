# Gesture Controlled Car

A gesture controlled car that translates hand tilt movements into real-time wireless driving commands. Built as a final year project at Khalsa College of Arts, Commerce & Science, Mumbai.

## How It Works

An ADXL335 accelerometer mounted on a glove detects the tilt direction of the hand. An Arduino LilyPad reads the X and Y axis values and encodes the direction command using an HT12E encoder IC, which is then broadcast wirelessly via an RF433 transmitter module.

On the car side, an RF433 receiver picks up the signal through a hand-wound copper antenna coil and passes it to an HT12D decoder IC. The decoded output drives an L293DNE motor driver IC which controls the two DC motors.

| Hand Tilt | Car Action |
|-----------|------------|
| Forward   | Move forward |
| Backward  | Reverse |
| Left      | Turn left |
| Right     | Turn right |
| Neutral   | Stop |

## Hardware Components

**Transmitter (Glove)**
- Arduino LilyPad
- ADXL335 Accelerometer
- HT12E Encoder IC
- RF433 MHz Transmitter Module

**Receiver (Car)**
- Arduino (Uno or compatible)
- HT12D Decoder IC
- RF433 MHz Receiver Module with copper antenna coil
- L293DNE Motor Driver IC
- 2x DC Motors

## Project Structure

```
gesture_controlled_car/
├── gesture_controlled_car/
│   └── gesture_controlled_car.ino    (upload this to the Arduino LilyPad on the glove)
├── Rx_1080.jpg                        (receiver circuit diagram)
├── TX_1080.jpg                        (transmitter circuit diagram)
└── README.md
```

There is only one Arduino in this project, on the glove/transmitter side. The receiver side is entirely hardware: RX433 receiver feeds into the HT12D decoder, whose outputs drive the L293D motor driver directly with no microcontroller involved.

## Setup

1. Install the **Arduino IDE** from https://www.arduino.cc/en/software
2. Open `gesture_controlled_car.ino` and upload it to the Arduino LilyPad on the glove
3. Open the Serial Monitor (9600 baud) to verify tilt readings and direction commands
4. Adjust `tiltThreshold` in the sketch if the car is too sensitive or not responsive enough to your hand movements

## Tech Stack
Arduino, Embedded C, ADXL335 Accelerometer, RF433 Wireless Communication, HT12E/HT12D Encoder-Decoder ICs, L293DNE Motor Driver
