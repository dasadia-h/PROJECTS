/*
  RFID + Password Based Security System
  Hardware: Arduino, RC522 RFID Reader, 4x4 Keypad, 16x2 LCD (I2C),
            Servo Motor, IR Sensor, Push Button
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Keypad.h>

// pin assignments
const int rfidSSPin    = 10;
const int rfidResetPin = 9;
const int latchPin     = 6;
const int doorSensor   = 7;
const int exitButton   = 8;

// how far the servo turns to lock and unlock the latch
// adjust these to match your physical latch mechanism
const int latchLocked   = 0;
const int latchUnlocked = 90;

// how long the door stays unlocked in milliseconds
// increase this if you need more time to open the door
const int unlockDuration = 5000;

// enter your passcode here, can be any combination of digits
const String correctPassword = "YOUR_PASSCODE_HERE";

// add your RFID card UIDs here
// run rfid_uid_finder.ino first to get each card's UID
// UIDs look something like "A1 B2 C3 D4"
// to add more cards, add a new line inside the array following the same format
// to remove a card, delete its line from the array
// update totalCards to match however many cards you have listed
String authorisedCards[] = {
  "XX XX XX XX",   // card 1
  "XX XX XX XX",   // card 2
  "XX XX XX XX"    // card 3
};
int totalCards = 3;    // update this number based on the number of cards you add or remove

MFRC522 rfidReader(rfidSSPin, rfidResetPin);
Servo doorLatch;
LiquidCrystal_I2C screen(0x27, 16, 2);

// keypad layout
const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
byte rowPins[ROWS] = {A0, A1, A2, A3};
byte colPins[COLS] = {A4, A5, 2, 3};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

String typedPassword = "";
bool isLocked = true;


void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfidReader.PCD_Init();

  doorLatch.attach(latchPin);
  doorLatch.write(latchLocked);

  pinMode(doorSensor, INPUT);
  pinMode(exitButton, INPUT_PULLUP);

  screen.init();
  screen.backlight();

  showMessage("system ready", "scan or enter pin");
  Serial.println("ready");
}


void showMessage(String top, String bottom) {
  screen.clear();
  screen.setCursor(0, 0);
  screen.print(top);
  screen.setCursor(0, 1);
  screen.print(bottom);
}


void unlock() {
  isLocked = false;
  doorLatch.write(latchUnlocked);
  showMessage("access granted", "door unlocked");
  Serial.println("unlocked");
}


void lock() {
  isLocked = true;
  doorLatch.write(latchLocked);
  showMessage("door locked", "scan or enter pin");
  Serial.println("locked");
}


void denyAccess() {
  showMessage("access denied", "try again");
  Serial.println("denied");
  delay(2000);
  showMessage("scan or enter pin", "");
}


// checks if the scanned card is in the authorised list
bool isRegisteredCard(String uid) {
  for (int i = 0; i < totalCards; i++) {
    if (uid == authorisedCards[i]) return true;
  }
  return false;
}


// reads the scanned card's UID and returns it as a string
String readCardUID() {
  String uid = "";
  for (byte i = 0; i < rfidReader.uid.size; i++) {
    if (rfidReader.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfidReader.uid.uidByte[i], HEX);
    if (i < rfidReader.uid.size - 1) uid += " ";
  }
  uid.toUpperCase();
  return uid;
}


// builds up the typed password and checks it when the user presses hash
void handleKeypad() {
  char key = keypad.getKey();
  if (!key) return;

  if (key == '*') {
    typedPassword = "";
    showMessage("cleared", "enter pin:");
    return;
  }

  if (key == '#') {
    if (typedPassword == correctPassword) {
      unlock();
      delay(unlockDuration);
      lock();
    } else {
      denyAccess();
    }
    typedPassword = "";
    return;
  }

  typedPassword += key;
  showMessage("enter pin:", String("*").repeat(typedPassword.length()));
}


void loop() {
  // exit button unlocks from inside without needing authentication
  if (digitalRead(exitButton) == LOW) {
    unlock();
    delay(unlockDuration);
    lock();
    return;
  }

  // door sensor detects when the door closes and auto locks
  if (!isLocked && digitalRead(doorSensor) == LOW) {
    delay(500);
    lock();
    return;
  }

  // check if an RFID card is being tapped
  if (rfidReader.PICC_IsNewCardPresent() && rfidReader.PICC_ReadCardSerial()) {
    String uid = readCardUID();
    Serial.println("card: " + uid);
    if (isRegisteredCard(uid)) {
      unlock();
      delay(unlockDuration);
      lock();
    } else {
      denyAccess();
    }
    rfidReader.PICC_HaltA();
    return;
  }

  handleKeypad();
}
