/*
  RFID Card UID Finder
  use this sketch to find the UID of your RFID card.
  once you have the UID, update the registeredUID variable in
  rfid_security_system.ino accordingly.
*/

#include <SPI.h>
#include <MFRC522.h>

const int rfidSS  = 10;
const int rfidRST = 9;

MFRC522 rfid(rfidSS, rfidRST);


void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID UID finder ready");
  Serial.println("tap your card on the reader...");
}


void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  Serial.print("card UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) Serial.print(" ");
  }
  Serial.println();
  Serial.println("copy this UID into registeredUID in rfid_security_system.ino");
  Serial.println("tap another card to read its UID...");

  rfid.PICC_HaltA();
  delay(1000);
}
