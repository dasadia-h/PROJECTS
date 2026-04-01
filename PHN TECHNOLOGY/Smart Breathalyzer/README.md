# ASVI — Smart Breathalyzer
### Booze It, Lose It

A breathalyzer system that detects breath alcohol concentration, displays it live on an OLED screen, and pushes the reading to Firebase. An Android app (ASVI) receives the reading in real time, lets the officer enter the driver's details, and manages violations on a three strike basis — sending warning emails for the first two offenses and a court summons on the third.

## How It Works

The MQ3 reads breath alcohol concentration and shows it live on the OLED. When the officer presses the button, the ESP32 pushes the concentration and GPS location to Firebase. The Android app auto-fills the concentration field from Firebase. The officer fetches the driver's existing details using their license number, fills in any missing info, and hits Submit.

| Strike | Action |
|--------|--------|
| 1st offense | Warning email sent |
| 2nd offense | Final warning email sent |
| 3rd offense | Court summons sent + entry moves to Violations screen |

## App Screens

- **Splash** — ASVI branding
- **Data Entry** — license number, name, surname, vehicle number, email, concentration (auto-filled from sensor). Fetch pulls existing details, Submit logs the entry.
- **Records** — full history of all flagged entries
- **Violations** — only people caught 3 or more times

## Project Structure

```
smart_breathalyzer/
├── smart_breathalyzer/
│   └── smart_breathalyzer.ino     (flash onto the ESP32)
├── android_app/
│   ├── SplashActivity.java
│   ├── DrawerActivity.java
│   ├── DataEntryFragment.java
│   ├── RecordsFragment.java
│   ├── ViolationsFragment.java
│   ├── RecordAdapter.java
│   └── Record.java
└── README.md
```

## Hardware

- ESP32
- MQ3 Gas Sensor
- GPS Module (UART on pins 16/17)
- SSD1306 OLED Display (I2C)
- Push Button on GPIO 15

## Setup

**Firebase**
1. Create a Firebase project at console.firebase.google.com
2. Enable Realtime Database
3. Copy your project host and database secret into `smart_breathalyzer.ino`
4. Add the `google-services.json` file to your Android project

**ESP32**
1. Install libraries in Arduino IDE: `Adafruit SSD1306`, `Adafruit GFX`, `TinyGPS++`, `Firebase ESP Client`
2. Update `WIFI_SSID`, `WIFI_PASSWORD`, `FIREBASE_HOST`, `FIREBASE_AUTH`
3. Flash to ESP32

**Android App**
1. Open in Android Studio
2. Add Firebase to the project using `google-services.json`
3. Add dependencies to `build.gradle`: Firebase Realtime Database, JavaMail API (`com.sun.mail:android-mail:1.6.7`)
4. Update sender email and app password in `DataEntryFragment.java`
5. Build and install on device

## Tech Stack
ESP32, MQ3 Gas Sensor, GPS, SSD1306 OLED, Firebase Realtime Database, Android Studio, Java, JavaMail API
