FROM nvcr.io/nvidia/l4t-base:r32.6.1

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-opencv \
    python3-numpy \
    libopencv-dev \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    Pillow \
    Adafruit-SSD1306 \
    Jetson.GPIO

WORKDIR /app
COPY . .

CMD ["python3", "main.py"]
