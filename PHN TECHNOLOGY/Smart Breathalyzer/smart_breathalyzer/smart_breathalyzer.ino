#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <Firebase_ESP_Client.h>

const char* WIFI_SSID      = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD  = "YOUR_WIFI_PASSWORD";
const char* FIREBASE_HOST  = "YOUR_PROJECT_ID.firebaseio.com";
const char* FIREBASE_AUTH  = "YOUR_DATABASE_SECRET";

const int mq3Pin     = 34;
const int readButton = 15;

Adafruit_SSD1306 display(128, 64, &Wire, -1);
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

FirebaseData   firebaseData;
FirebaseAuth   firebaseAuth;
FirebaseConfig firebaseConfig;


void setup() {
  Serial.begin(115200);
  pinMode(readButton, INPUT_PULLUP);

  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED not found");
    while (true);
  }
  display.clearDisplay();

  // connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  showMessage("Connecting...", "");
  while (WiFi.status() != WL_CONNECTED) delay(500);
  showMessage("WiFi connected", "");

  // connect to Firebase
  firebaseConfig.host           = FIREBASE_HOST;
  firebaseConfig.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&firebaseConfig, &firebaseAuth);
  Firebase.reconnectWiFi(true);

  showMessage("ASVI Ready", "Booze It, Lose It");
  delay(1500);
}


void showMessage(String line1, String line2) {
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setTextSize(1);
  display.setCursor(0, 10);
  display.println(line1);
  display.setCursor(0, 35);
  display.println(line2);
  display.display();
}


String getGPSLocation() {
  unsigned long start = millis();
  while (millis() - start < 2000) {
    while (gpsSerial.available()) gps.encode(gpsSerial.read());
  }
  if (gps.location.isValid()) {
    return String(gps.location.lat(), 6) + "," + String(gps.location.lng(), 6);
  }
  return "0.0,0.0";
}


void loop() {
  int rawReading      = analogRead(mq3Pin);
  int concentration   = map(rawReading, 0, 4095, 0, 1000);

  // show the concentration reading on display
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(1);
  display.println("breath alcohol");
  display.setCursor(0, 20);
  display.setTextSize(2);
  display.print(concentration);
  display.setTextSize(1);
  display.setCursor(0, 50);
  if (concentration > 400) {
    display.println("alcohol detected!");
  } else {
    display.println("clear");
  }
  display.display();

  // when officer presses button, push reading to Firebase
  if (digitalRead(readButton) == LOW) {
    String location = getGPSLocation();

    FirebaseJson json;
    json.set("concentration", concentration);
    json.set("location",      location);

    if (Firebase.RTDB.setJSON(&firebaseData, "/latest_reading", &json)) {
      showMessage("Reading sent!", "BAC: " + String(concentration));
      Serial.println("pushed to Firebase: " + String(concentration));
    } else {
      showMessage("Send failed", firebaseData.errorReason().c_str());
    }
    delay(2000);
  }

  delay(500);
}
