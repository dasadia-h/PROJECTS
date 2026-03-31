import cv2
import numpy as np


# Crop the bottom half of the frame since lane markings are always on the ground
def get_region_of_interest(frame):
    height, width = frame.shape[:2]
    mask = np.zeros_like(frame)
    region = np.array([[
        (0, height),
        (0, height // 2),
        (width, height // 2),
        (width, height)
    ]], dtype=np.int32)
    cv2.fillPoly(mask, region, 255)
    return cv2.bitwise_and(frame, mask)


# Detect white lane markings and return a binary mask
def detect_white_lines(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 30, 255])
    return cv2.inRange(hsv, lower_white, upper_white)


# Find lines in the frame using Hough transform
def get_hough_lines(binary_frame):
    edges = cv2.Canny(binary_frame, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=20,
        maxLineGap=10
    )
    return lines


# Separate lines into left edge and center dashed lines based on slope
def classify_lines(lines, frame_width):
    left_lines   = []
    center_lines = []

    if lines is None:
        return left_lines, center_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)

        # Left edge line sits on the left side of the frame
        if x1 < frame_width // 2 and x2 < frame_width // 2:
            left_lines.append(line)
        # Center dashed line sits around the middle
        elif abs(x1 - frame_width // 2) < 100:
            center_lines.append(line)

    return left_lines, center_lines


# Figure out what steering direction the car should take
def get_steering_direction(left_lines, center_lines, frame_width):
    has_left   = len(left_lines) > 0
    has_center = len(center_lines) > 0

    if has_left and has_center:
        return "forward"
    elif has_left and not has_center:
        return "turn_right"
    elif not has_left and has_center:
        return "turn_left"
    else:
        return "stop"


# Draw detected lines onto the frame for debugging
def draw_lines(frame, lines, color=(0, 255, 0)):
    if lines is None:
        return frame
    overlay = frame.copy()
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(overlay, (x1, y1), (x2, y2), color, 3)
    return overlay


# Main function — takes a raw frame and returns the steering direction + annotated frame
def process_frame(frame):
    roi           = get_region_of_interest(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    white_mask    = detect_white_lines(frame)
    masked        = cv2.bitwise_and(roi, white_mask)
    lines         = get_hough_lines(masked)
    left, center  = classify_lines(lines, frame.shape[1])
    direction     = get_steering_direction(left, center, frame.shape[1])

    annotated = draw_lines(frame, left,   color=(0, 255, 0))
    annotated = draw_lines(annotated, center, color=(255, 0, 0))
    cv2.putText(annotated, direction, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)

    return direction, annotated
