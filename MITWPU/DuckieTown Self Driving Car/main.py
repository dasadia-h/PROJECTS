import cv2
import socket
import threading
import time

from Adafruit_SSD1306 import SSD1306_128_32
from PIL import Image, ImageDraw, ImageFont
from lane_detection import process_frame
from duck_detection import detect_ducks, draw_ducks, duck_in_path

import Jetson.GPIO as GPIO


# Motor driver pins
LEFT_FORWARD  = 11
LEFT_BACKWARD = 13
RIGHT_FORWARD = 15
RIGHT_BACKWARD= 16
MOTOR_ENABLE  = 18

# WiFi settings — other Duckietown vehicles broadcast on this port
WIFI_PORT    = 5005
WIFI_HOST    = "0.0.0.0"

# How long to wait when a duck is spotted before moving again
DUCK_STOP_SECONDS = 2


# Motor control helpers
def setup_motors():
    GPIO.setmode(GPIO.BOARD)
    pins = [LEFT_FORWARD, LEFT_BACKWARD, RIGHT_FORWARD, RIGHT_BACKWARD, MOTOR_ENABLE]
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
    GPIO.output(MOTOR_ENABLE, GPIO.HIGH)


def move_forward():
    GPIO.output(LEFT_FORWARD,   GPIO.HIGH)
    GPIO.output(LEFT_BACKWARD,  GPIO.LOW)
    GPIO.output(RIGHT_FORWARD,  GPIO.HIGH)
    GPIO.output(RIGHT_BACKWARD, GPIO.LOW)


def move_backward():
    GPIO.output(LEFT_FORWARD,   GPIO.LOW)
    GPIO.output(LEFT_BACKWARD,  GPIO.HIGH)
    GPIO.output(RIGHT_FORWARD,  GPIO.LOW)
    GPIO.output(RIGHT_BACKWARD, GPIO.HIGH)


def turn_left():
    GPIO.output(LEFT_FORWARD,   GPIO.LOW)
    GPIO.output(LEFT_BACKWARD,  GPIO.HIGH)
    GPIO.output(RIGHT_FORWARD,  GPIO.HIGH)
    GPIO.output(RIGHT_BACKWARD, GPIO.LOW)


def turn_right():
    GPIO.output(LEFT_FORWARD,   GPIO.HIGH)
    GPIO.output(LEFT_BACKWARD,  GPIO.LOW)
    GPIO.output(RIGHT_FORWARD,  GPIO.LOW)
    GPIO.output(RIGHT_BACKWARD, GPIO.HIGH)


def stop_motors():
    for pin in [LEFT_FORWARD, LEFT_BACKWARD, RIGHT_FORWARD, RIGHT_BACKWARD]:
        GPIO.output(pin, GPIO.LOW)


def apply_direction(direction):
    if direction == "forward":
        move_forward()
    elif direction == "turn_left":
        turn_left()
    elif direction == "turn_right":
        turn_right()
    else:
        stop_motors()


# OLED display helpers
def setup_display():
    display = SSD1306_128_32(rst=None)
    display.begin()
    display.clear()
    display.display()
    return display


def update_display(display, line1, line2=""):
    image  = Image.new("1", (display.width, display.height))
    draw   = ImageDraw.Draw(image)
    font   = ImageFont.load_default()
    draw.text((0, 0),  line1, font=font, fill=255)
    draw.text((0, 16), line2, font=font, fill=255)
    display.image(image)
    display.display()


# Listen for status broadcasts from other Duckietown vehicles on the network
nearby_vehicles = {}

def start_wifi_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((WIFI_HOST, WIFI_PORT))

    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode("utf-8")
                nearby_vehicles[addr[0]] = message
            except Exception:
                pass

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()


# Broadcast our own status to other vehicles
def broadcast_status(status):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(status.encode("utf-8"), ("<broadcast>", WIFI_PORT))
    sock.close()


# Main loop
def main():
    setup_motors()
    display = setup_display()
    start_wifi_listener()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera")
        return

    print("Duckietown car is running")
    update_display(display, "Duckietown", "Starting...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break

            # Run lane detection
            direction, annotated_frame = process_frame(frame)

            # Run duck detection
            ducks = detect_ducks(frame)
            annotated_frame = draw_ducks(annotated_frame, ducks)

            # If a duck is in the path, stop and wait
            if duck_in_path(ducks, frame.shape[1], frame.shape[0]):
                stop_motors()
                update_display(display, "Duck ahead!", "Waiting...")
                broadcast_status("STOPPED: duck in path")
                time.sleep(DUCK_STOP_SECONDS)
                continue

            # Otherwise follow the lane
            apply_direction(direction)
            update_display(display, f"Dir: {direction}", f"Vehicles: {len(nearby_vehicles)}")
            broadcast_status(f"MOVING: {direction}")

            # Show the annotated feed for debugging (comment out when running headless)
            cv2.imshow("Duckietown View", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        stop_motors()
        GPIO.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        update_display(display, "Stopped", "")
        print("Shutdown complete")


if __name__ == "__main__":
    main()
