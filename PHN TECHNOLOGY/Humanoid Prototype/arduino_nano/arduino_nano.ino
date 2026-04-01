#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// two PCA9685 servo drivers 
Adafruit_PWMServoDriver driver1 = Adafruit_PWMServoDriver(0x40);
Adafruit_PWMServoDriver driver2 = Adafruit_PWMServoDriver(0x41);

// ultrasonic sensor pins (front, back, left, right)
const int frontTrig = 2,  frontEcho = 3;
const int backTrig  = 4,  backEcho  = 5;
const int leftTrig  = 6,  leftEcho  = 7;
const int rightTrig = 8,  rightEcho = 9;

const int safeDistance = 20;

bool bluetoothMode = false;


void setup() {
  Serial.begin(9600);

  driver1.begin();
  driver1.setPWMFreq(50);
  driver2.begin();
  driver2.setPWMFreq(50);

  // ultrasonic trigger pins as output, echo pins as input
  int trigPins[] = {frontTrig, backTrig, leftTrig, rightTrig};
  int echoPins[] = {frontEcho, backEcho, leftEcho, rightEcho};
  for (int i = 0; i < 4; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }

  centerAllServos();
  Serial.println("ready");
}


// read distance from one ultrasonic sensor 
float readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  return (duration * 0.034) / 2.0;
}


// set a servo on driver1 or driver2 to the required angle
void setServo(int driverNum, int channel, int angle) {
  int pulse = map(angle, 0, 180, 150, 600);
  if (driverNum == 1) driver1.setPWM(channel, 0, pulse);
  else                driver2.setPWM(channel, 0, pulse);
}


// bring all 22 servos to their neutral standing position
void centerAllServos() {
  for (int i = 0; i < 16; i++) setServo(1, i, 90);
  for (int i = 0; i < 6;  i++) setServo(2, i, 90);
}


void walkForward() {
  setServo(1, 0, 70);  setServo(1, 1, 110);
  delay(300);
  setServo(1, 0, 90);  setServo(1, 1, 90);
  delay(200);
  setServo(1, 2, 110); setServo(1, 3, 70);
  delay(300);
  setServo(1, 2, 90);  setServo(1, 3, 90);
  delay(200);
}


void walkBackward() {
  setServo(1, 0, 110); setServo(1, 1, 70);
  delay(300);
  setServo(1, 0, 90);  setServo(1, 1, 90);
  delay(200);
  setServo(1, 2, 70);  setServo(1, 3, 110);
  delay(300);
  setServo(1, 2, 90);  setServo(1, 3, 90);
  delay(200);
}


void turnLeft() {
  setServo(1, 4, 60);
  delay(400);
  setServo(1, 4, 90);
}


void turnRight() {
  setServo(1, 4, 120);
  delay(400);
  setServo(1, 4, 90);
}


void waveHand() {
  for (int i = 0; i < 3; i++) {
    setServo(2, 0, 45);
    delay(300);
    setServo(2, 0, 135);
    delay(300);
  }
  setServo(2, 0, 90);
}


// parse and execute a command string
void handleCommand(String cmd) {
  cmd.trim();
  if      (cmd == "FORWARD")  walkForward();
  else if (cmd == "BACKWARD") walkBackward();
  else if (cmd == "LEFT")     turnLeft();
  else if (cmd == "RIGHT")    turnRight();
  else if (cmd == "WAVE")     waveHand();
  else if (cmd == "STOP")     centerAllServos();
  else if (cmd == "BT_ON")    { bluetoothMode = true;  Serial.println("BT_MODE_ON"); }
  else if (cmd == "BT_OFF")   { bluetoothMode = false; Serial.println("BT_MODE_OFF"); }
}


void loop() {
  // check all four sensors and warn the Pi if anything is too close
  if (!bluetoothMode) {
    float front = readDistance(frontTrig, frontEcho);
    float back  = readDistance(backTrig,  backEcho);
    float left  = readDistance(leftTrig,  leftEcho);
    float right = readDistance(rightTrig, rightEcho);

    if (front < safeDistance || back < safeDistance ||
        left  < safeDistance || right < safeDistance) {
      Serial.println("OBSTACLE");
    }
  }

  // read incoming commands from serial (Pi in voice mode, or BLE app in bluetooth mode)
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handleCommand(cmd);
  }
}
