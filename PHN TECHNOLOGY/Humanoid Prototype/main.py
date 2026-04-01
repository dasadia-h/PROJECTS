import serial
import time
import openai
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import pyttsx3
import tempfile
import os

# update these to match your hotspot credentials
WIFI_SSID     = "YOUR_HOTSPOT_SSID"
WIFI_PASSWORD = "YOUR_HOTSPOT_PASSWORD"

# your OpenAI API key
openai.api_key = "YOUR_OPENAI_API_KEY"

# Check the serial port of the Arduino Nano
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE   = 9600

# audio recording settings
SAMPLE_RATE    = 16000
RECORD_SECONDS = 4

speaker = pyttsx3.init()
arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

bluetooth_mode = False


def speak(text):
    print(f"speaking: {text}")
    speaker.say(text)
    speaker.runAndWait()


def send_to_arduino(command):
    arduino.write((command + "\n").encode())
    print(f"sent to arduino: {command}")


def record_audio():
    print("listening...")
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()
    return audio


def transcribe_audio(audio):
    # save audio to a temp file and send it to whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav.write(tmp.name, SAMPLE_RATE, audio)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)

    os.unlink(tmp_path)
    return transcript["text"]


def interpret_command(text):
    # ask GPT whether this is a movement command or a conversational response
    prompt = f"""
You are controlling a humanoid robot. The user said: "{text}"

If this is a movement command, respond with one of these exact words only:
FORWARD, BACKWARD, LEFT, RIGHT, WAVE, STOP

If this is a conversational question or statement that needs a spoken response,
respond with: SPEAK: <your response here>

Only respond with one of the above formats, nothing else.
"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def check_arduino_messages():
    # read any messages the Arduino sends back (like obstacle warnings)
    while arduino.in_waiting:
        message = arduino.readline().decode().strip()
        if message == "OBSTACLE":
            speak("obstacle detected, stopping")
            send_to_arduino("STOP")
        elif message == "BT_MODE_ON":
            global bluetooth_mode
            bluetooth_mode = True
        elif message == "BT_MODE_OFF":
            bluetooth_mode = False


def switch_to_bluetooth_mode():
    global bluetooth_mode
    bluetooth_mode = True
    send_to_arduino("BT_ON")
    speak("bluetooth mode activated. obstacle detection stopped. verbal commands suspended. you now have full control.")
    print("switched to bluetooth mode")


def switch_to_voice_mode():
    global bluetooth_mode
    bluetooth_mode = False
    send_to_arduino("BT_OFF")
    speak("voice mode activated. obstacle detection resumed.")
    print("switched to voice mode")


def main():
    speak("humanoid ready")
    print("humanoid online")

    while True:
        check_arduino_messages()

        if bluetooth_mode:
            # in bluetooth mode the BLE Controller app sends commands directly
            # to the Arduino over bluetooth, so the Pi just waits
            time.sleep(0.5)
            continue

        # record and process a voice command
        audio      = record_audio()
        text       = transcribe_audio(audio)
        print(f"heard: {text}")

        if not text.strip():
            continue

        # check if the user wants to switch modes
        if "bluetooth mode" in text.lower():
            switch_to_bluetooth_mode()
            continue
        if "voice mode" in text.lower():
            switch_to_voice_mode()
            continue

        response = interpret_command(text)
        print(f"GPT response: {response}")

        if response.startswith("SPEAK:"):
            spoken_text = response.replace("SPEAK:", "").strip()
            speak(spoken_text)
        else:
            send_to_arduino(response)


if __name__ == "__main__":
    main()
