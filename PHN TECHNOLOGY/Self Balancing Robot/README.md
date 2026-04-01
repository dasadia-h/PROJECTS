# Self Balancing Bot

A three-layered self-balancing robot that continuously detects tilt and counters it in real time to stay upright. Built as a teaching project at PHN Technology (Army Public School).

## How It Works

The MPU6050 on the top layer reads the robot's tilt angle using a complementary filter that blends accelerometer and gyroscope data for a stable, noise-free reading. The Arduino runs a PID control loop on that angle — when the robot tilts forward, the motors drive forward to chase the center of gravity back into balance, and vice versa. The L298N in the middle layer drives the two BO motors at the base.

## Three Layer Structure

| Layer | Component |
|-------|-----------|
| Top | MPU6050 IMU |
| Middle | L298N Motor Driver |
| Base | 2x BO Motors + Wheels |

## PID Tuning

The three constants at the top of the sketch control balance behaviour:

| Constant | Default | Effect |
|----------|---------|--------|
| `kp` | 21.0 | how aggressively it reacts to tilt |
| `ki` | 0.8 | corrects for steady lean over time |
| `kd` | 0.9 | dampens oscillation |

Start with `ki` and `kd` at 0 and tune `kp` first until the robot roughly balances, then bring the others in gradually.

## Pin Mapping

| Component | Pin |
|-----------|-----|
| Motor A IN1 | D5 |
| Motor A IN2 | D6 |
| Motor A Enable (PWM) | D9 |
| Motor B IN1 | D7 |
| Motor B IN2 | D8 |
| Motor B Enable (PWM) | D10 |
| MPU6050 SDA | A4 |
| MPU6050 SCL | A5 |

## Setup

1. Open `self_balancing_bot.ino` in Arduino IDE
2. Install the `MPU6050` library by ElectronicCats via the Library Manager
3. Upload to Arduino
4. Open Serial Monitor at 9600 baud to watch live tilt angle and PID output
5. Adjust `targetAngle` if the robot leans slightly at rest — set it to whatever angle reads when the robot is physically upright

## Tech Stack
Arduino, MPU6050, Complementary Filter, PID Control, L298N Motor Driver, Embedded C
