/*
  IR Remote Code Finder
  use this sketch to find the "hex code" for each button on your IR remote.
  once you have the codes of the buttons you need, update the irCodes[] array 
  in smart_home_automation.ino accordingly.
*/

#include <IRremote.h>

const int irPin = 2;    // pin no can vary based on which pin the components are connected on
IRrecv irReceiver(irPin);
decode_results result;


void setup() {
  Serial.begin(9600);
  irReceiver.enableIRIn();
  Serial.println("IR code finder ready");
  Serial.println("point your remote at the receiver and press any button");
}


void loop() {
  if (irReceiver.decode(&result)) {
    Serial.print("button code: 0x");
    Serial.println(result.value, HEX);
    Serial.println("press the next button...");
    irReceiver.resume();
    delay(500);
  }
}
