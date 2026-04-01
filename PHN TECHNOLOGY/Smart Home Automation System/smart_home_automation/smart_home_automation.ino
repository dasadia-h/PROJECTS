#include <Servo.h>
#include <IRremote.h>

const int irPin = 2;    // pin no can be different based on where the component is connected

Servo switches[6];
const int servoPins[] = {3, 5, 6, 9, 10, 11};

// angle when the switch is flipped on and off
const int onAngle  = 120;   // these angles can be changed based on the type of switch being used
const int offAngle = 60;    // these angles can be changed based on the type of switch being used

// track the current state of each switch
bool switchState[6] = {false, false, false, false, false, false};

IRrecv irReceiver(irPin);
decode_results irResult;

// run ir_code_finder.ino first to get the codes for each button on the IR Remote
const unsigned long irCodes[] = {
  0x00000000,   // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 1
  0x00000000,   // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 2
  0x00000000,   // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 3
  0x00000000,   // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 4
  0x00000000,   // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 5
  0x00000000    // Replace the given code with the code you got for the IR Remote Button that you want to assign to Switch 6
};


void setup() {
  Serial.begin(9600);

  for (int i = 0; i < 6; i++) {
    switches[i].attach(servoPins[i]);
    switches[i].write(offAngle);
  }

  irReceiver.enableIRIn();
  Serial.println("smart home ready");
}


// flip a switch servo to its on or off position
void toggleSwitch(int index) {
  if (index < 0 || index > 5) return;
  switchState[index] = !switchState[index];
  switches[index].write(switchState[index] ? onAngle : offAngle);
  Serial.print("switch "); Serial.print(index + 1);
  Serial.println(switchState[index] ? ": ON" : ": OFF");
}


// set a switch to a specific state
void setSwitch(int index, bool state) {
  if (index < 0 || index > 5) return;
  switchState[index] = state;
  switches[index].write(state ? onAngle : offAngle);
  Serial.print("switch "); Serial.print(index + 1);
  Serial.println(state ? ": ON" : ": OFF");
}


// handle commands from the Bluetooth app
void handleBluetoothCommand(char cmd) {
  switch (cmd) {
    case '1': toggleSwitch(0); break;
    case '2': toggleSwitch(1); break;
    case '3': toggleSwitch(2); break;
    case '4': toggleSwitch(3); break;
    case '5': toggleSwitch(4); break;
    case '6': toggleSwitch(5); break;
    case 'A': setSwitch(0, true);  break;
    case 'a': setSwitch(0, false); break;
    case 'B': setSwitch(1, true);  break;
    case 'b': setSwitch(1, false); break;
    case 'C': setSwitch(2, true);  break;
    case 'c': setSwitch(2, false); break;
    case 'D': setSwitch(3, true);  break;
    case 'd': setSwitch(3, false); break;
    case 'E': setSwitch(4, true);  break;
    case 'e': setSwitch(4, false); break;
    case 'F': setSwitch(5, true);  break;
    case 'f': setSwitch(5, false); break;
    case 'X': for (int i = 0; i < 6; i++) setSwitch(i, false); break;
  }
}


// check IR remote input and toggle the matching switch
void handleIRInput() {
  if (!irReceiver.decode(&irResult)) return;

  unsigned long code = irResult.value;
  for (int i = 0; i < 6; i++) {
    if (code == irCodes[i]) {
      toggleSwitch(i);
      break;
    }
  }
  irReceiver.resume();
}


void loop() {
  // check for Bluetooth commands
  if (Serial.available()) {
    char cmd = Serial.read();
    handleBluetoothCommand(cmd);
  }

  // check for IR remote commands
  handleIRInput();

  delay(50);
}
