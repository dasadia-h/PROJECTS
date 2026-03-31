# Object Detection Drone

A custom-built drone with two independently functioning systems running in parallel. The flight control system is handled entirely by hardware — a joystick remote transmits commands via radio to a receiver onboard the drone, which feeds into the flight controller and drives the ESCs and brushless motors.

Separately, an ESP32-CAM module onboard the drone captures live footage and streams it over WiFi as an MJPEG stream. A Python script on the laptop receives this stream and runs YOLO V3 object detection in real time, drawing bounding boxes and labels around detected objects.

## Project Structure

```
object_detection_drone/
├── esp32_firmware/
│   └── esp32_firmware.ino     (flash this onto the ESP32-CAM on the drone)
├── laptop_detection/
│   ├── detect.py              (run this on the laptop to view the stream with YOLO)
│   └── requirements.txt
└── README.md
```

## Hardware

**Drone (Control System)**
- Joystick Remote Controller
- Radio Transmitter and Receiver
- Flight Controller
- ESCs (Electronic Speed Controllers)
- Brushless Motors

**Drone (Vision System)**
- ESP32-CAM Module

**Laptop**
- Any laptop on the same WiFi network as the drone

## YOLO V3 Model Files

The model files are too large for GitHub. Download them separately and place them in the `laptop_detection/` folder before running:

| File | Download Link |
|------|--------------|
| `yolov3.weights` | https://pjreddie.com/media/files/yolov3.weights |
| `yolov3.cfg` | https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg |
| `coco.names` | https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names |

## Setup and Running

**Step 1 — Flash the ESP32**
1. Install the Arduino IDE and add ESP32 board support
2. Open `esp32_firmware/esp32_firmware.ino`
3. Update `WIFI_SSID` and `WIFI_PASSWORD` to match your network
4. Select board: `AI Thinker ESP32-CAM` and flash
5. Open the Serial Monitor (115200 baud) — it will print the stream URL once connected

**Step 2 — Run detection on the laptop**
```bash
cd laptop_detection
pip install -r requirements.txt
python detect.py --stream http://<ESP32_IP>/stream
```
Replace `<ESP32_IP>` with the IP address printed in the Serial Monitor.

Press `Q` to quit.

## Tech Stack
ESP32-CAM, Arduino, C++, Python, OpenCV, YOLO V3, WiFi MJPEG Streaming
