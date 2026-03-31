# Duckietown Self Driving Car

A self-driving car built on the Duckietown platform that navigates a miniature city environment using real-time computer vision for lane following and pedestrian detection. Built as a 2-person team project at MITWPU during the PG Diploma in AI & ML.

## How It Works

The Jetson Nano reads live video from the onboard camera and runs two parallel detection pipelines:

**Lane Detection** identifies white edge lines and broken center lines using HSV colour filtering, Canny edge detection, and Hough line transforms. Based on which lines are visible, it decides whether to go forward, turn left, turn right, or stop.

**Duck Detection** isolates yellow blobs in the frame using HSV masking. If a rubber duck (pedestrian) is detected in the car's path, the car stops and waits before continuing.

The car also broadcasts its status over WiFi to other Duckietown vehicles on the same network and listens for their broadcasts, giving each car awareness of surrounding traffic. An onboard OLED display shows the current direction and number of nearby vehicles in real time.

## Hardware

- Jetson Nano
- Camera Module
- SSD1306 OLED Display (I2C)
- Motor Driver
- 2x DC Motors
- WiFi (onboard Jetson Nano)

## Project Structure

```
duckietown_self_driving_car/
├── main.py              (main loop, motor control, OLED, WiFi)
├── lane_detection.py    (white line detection and steering logic)
├── duck_detection.py    (yellow duck/pedestrian detection)
├── requirements.txt
├── Dockerfile
└── README.md
```

## Running with Docker

This project was deployed using Docker for consistent execution across environments.

Build and run on the Jetson Nano:
```bash
docker build -t duckietown-car .
docker run --runtime nvidia --privileged -e DISPLAY=$DISPLAY duckietown-car
```

## Running without Docker

```bash
pip3 install -r requirements.txt
python3 main.py
```

## Tech Stack
Python, OpenCV, Jetson Nano, Docker, Adafruit SSD1306, Jetson.GPIO, WiFi UDP Broadcasting
