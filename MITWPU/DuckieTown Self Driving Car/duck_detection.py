import cv2
import numpy as np


# Rubber ducks in Duckietown are yellow, so we isolate yellow in HSV
def detect_ducks(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    yellow_mask  = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Clean up noise with morphological operations
    kernel       = np.ones((5, 5), np.uint8)
    yellow_mask  = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN,  kernel)
    yellow_mask  = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)

    contours, _  = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ducks = []
    for contour in contours:
        area = cv2.contourArea(contour)
        # Ignore very small blobs that are just noise
        if area < 500:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        ducks.append((x, y, w, h))

    return ducks


# Draw bounding boxes around detected ducks
def draw_ducks(frame, ducks):
    for (x, y, w, h) in ducks:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(frame, "Duck!", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    return frame


# Returns True if a duck is close enough to be a hazard
def duck_in_path(ducks, frame_width, frame_height):
    for (x, y, w, h) in ducks:
        duck_center_x = x + w // 2
        duck_bottom   = y + h
        # Duck is in the center lane and in the lower half of the frame
        if (frame_width // 4 < duck_center_x < 3 * frame_width // 4 and
                duck_bottom > frame_height // 2):
            return True
    return False
