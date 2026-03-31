import cv2
import numpy as np
import urllib.request
import argparse
import os


# YOLO V3 model files — download links in the README
WEIGHTS_FILE = "yolov3.weights"
CONFIG_FILE  = "yolov3.cfg"
LABELS_FILE  = "coco.names"

CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD        = 0.4

# Colour per class so bounding boxes are easy to tell apart
np.random.seed(42)


def load_yolo_model():
    if not os.path.exists(WEIGHTS_FILE):
        print(f"Missing {WEIGHTS_FILE} — see README for download link")
        exit(1)
    if not os.path.exists(CONFIG_FILE):
        print(f"Missing {CONFIG_FILE} — see README for download link")
        exit(1)

    net    = cv2.dnn.readNet(WEIGHTS_FILE, CONFIG_FILE)
    labels = open(LABELS_FILE).read().strip().split("\n")
    colors = np.random.randint(0, 255, size=(len(labels), 3), dtype="uint8")

    layer_names    = net.getLayerNames()
    output_layers  = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

    print(f"YOLO V3 loaded — {len(labels)} classes")
    return net, labels, colors, output_layers


def run_yolo_detection(frame, net, labels, colors, output_layers):
    height, width = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []

    for output in layer_outputs:
        for detection in output:
            scores    = detection[5:]
            class_id  = np.argmax(scores)
            confidence = scores[class_id]

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            box    = detection[:4] * np.array([width, height, width, height])
            cx, cy, w, h = box.astype("int")
            x = int(cx - w / 2)
            y = int(cy - h / 2)

            boxes.append([x, y, int(w), int(h)])
            confidences.append(float(confidence))
            class_ids.append(class_id)

    # Non-max suppression to remove overlapping boxes
    kept = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)

    if len(kept) > 0:
        for i in kept.flatten():
            x, y, w, h = boxes[i]
            label      = labels[class_ids[i]]
            confidence = confidences[i]
            color      = [int(c) for c in colors[class_ids[i]]]

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                f"{label} {confidence:.2f}",
                (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )

    return frame


def main(stream_url):
    net, labels, colors, output_layers = load_yolo_model()

    print(f"Connecting to stream: {stream_url}")
    stream = urllib.request.urlopen(stream_url)

    byte_buffer = b""

    print("Running — press Q to quit")

    while True:
        byte_buffer += stream.read(4096)

        # Find JPEG boundaries in the MJPEG stream
        start = byte_buffer.find(b"\xff\xd8")
        end   = byte_buffer.find(b"\xff\xd9")

        if start == -1 or end == -1:
            continue

        jpg_data   = byte_buffer[start:end + 2]
        byte_buffer = byte_buffer[end + 2:]

        frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue

        frame = run_yolo_detection(frame, net, labels, colors, output_layers)

        cv2.imshow("Drone Feed — YOLO V3", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO V3 Object Detection on ESP32 Drone Stream")
    parser.add_argument(
        "--stream",
        type=str,
        default="http://192.168.1.100/stream",
        help="ESP32 stream URL (printed in serial monitor after boot)"
    )
    args = parser.parse_args()
    main(args.stream)
