#include <Servo.h>

// motor driver pins
const int leftForward   = 2;
const int leftBackward  = 3;
const int rightForward  = 4;
const int rightBackward = 5;
const int leftSpeed     = 9;
const int rightSpeed    = 10;

// fixed front and rear ultrasonic sensor pins
const int frontTrig = 6;
const int frontEcho = 7;
const int rearTrig  = 8;
const int rearEcho  = 13;

// sweeping left and right ultrasonic sensor pins
const int leftTrig  = A2;
const int leftEcho  = A3;
const int rightTrig = A4;
const int rightEcho = A5;

// servo pins
const int leftServoPin  = A0;
const int rightServoPin = A1;

Servo leftServo;
Servo rightServo;

// servo angle positions
const int facingForward = 90;
const int facingSide    = 135;
const int facingRear    = 180;

// anything closer than this is treated as an obstacle
const int safeDistance = 25;

const int driveSpeed = 180;
const int turnSpeed  = 150;


void setup() {
  pinMode(leftForward,   OUTPUT);
  pinMode(leftBackward,  OUTPUT);
  pinMode(rightForward,  OUTPUT);
  pinMode(rightBackward, OUTPUT);
  pinMode(leftSpeed,     OUTPUT);
  pinMode(rightSpeed,    OUTPUT);

  pinMode(frontTrig, OUTPUT); pinMode(frontEcho, INPUT);
  pinMode(rearTrig,  OUTPUT); pinMode(rearEcho,  INPUT);
  pinMode(leftTrig,  OUTPUT); pinMode(leftEcho,  INPUT);
  pinMode(rightTrig, OUTPUT); pinMode(rightEcho, INPUT);

  leftServo.attach(leftServoPin);
  rightServo.attach(rightServoPin);

  // start both sweeping sensors facing forward
  leftServo.write(facingForward);
  rightServo.write(facingForward);

  stopCar();
  Serial.begin(9600);
  Serial.println("PATS car ready");
}


// read distance from a single ultrasonic sensor in cm
float readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  return (duration * 0.034) / 2.0;
}


bool isObstacle(float distance) {
  return (distance > 0 && distance < safeDistance);
}


void moveForward() {
  analogWrite(leftSpeed,  driveSpeed);
  analogWrite(rightSpeed, driveSpeed);
  digitalWrite(leftForward,   HIGH); digitalWrite(leftBackward,  LOW);
  digitalWrite(rightForward,  HIGH); digitalWrite(rightBackward, LOW);
}


void moveBackward() {
  analogWrite(leftSpeed,  driveSpeed);
  analogWrite(rightSpeed, driveSpeed);
  digitalWrite(leftForward,   LOW); digitalWrite(leftBackward,  HIGH);
  digitalWrite(rightForward,  LOW); digitalWrite(rightBackward, HIGH);
}


void turnLeft() {
  analogWrite(leftSpeed,  turnSpeed);
  analogWrite(rightSpeed, turnSpeed);
  digitalWrite(leftForward,   LOW);  digitalWrite(leftBackward,  HIGH);
  digitalWrite(rightForward,  HIGH); digitalWrite(rightBackward, LOW);
}


void turnRight() {
  analogWrite(leftSpeed,  turnSpeed);
  analogWrite(rightSpeed, turnSpeed);
  digitalWrite(leftForward,   HIGH); digitalWrite(leftBackward,  LOW);
  digitalWrite(rightForward,  LOW);  digitalWrite(rightBackward, HIGH);
}


void stopCar() {
  analogWrite(leftSpeed,  0);
  analogWrite(rightSpeed, 0);
  digitalWrite(leftForward,  LOW); digitalWrite(leftBackward,  LOW);
  digitalWrite(rightForward, LOW); digitalWrite(rightBackward, LOW);
}


// sweep both side sensors through 3 positions and return true if that side is blocked
bool scanLeftSide() {
  bool blocked = false;
  int angles[] = {facingForward, facingSide, facingRear};

  for (int i = 0; i < 3; i++) {
    leftServo.write(angles[i]);
    delay(120);
    float dist = readDistance(leftTrig, leftEcho);
    Serial.print("left angle "); Serial.print(angles[i]);
    Serial.print(": "); Serial.println(dist);
    if (isObstacle(dist)) blocked = true;
  }

  leftServo.write(facingForward);
  delay(100);
  return blocked;
}


// right servo mirrors left, sweeping from forward to rear in the opposite direction
bool scanRightSide() {
  bool blocked = false;
  int angles[] = {facingForward, 180 - facingSide, 180 - facingRear};

  for (int i = 0; i < 3; i++) {
    rightServo.write(angles[i]);
    delay(120);
    // small gap before reading to avoid interference with left sensor
    delay(15);
    float dist = readDistance(rightTrig, rightEcho);
    Serial.print("right angle "); Serial.print(angles[i]);
    Serial.print(": "); Serial.println(dist);
    if (isObstacle(dist)) blocked = true;
  }

  rightServo.write(facingForward);
  delay(100);
  return blocked;
}


void loop() {
  float frontDist = readDistance(frontTrig, frontEcho);
  Serial.print("front: "); Serial.println(frontDist);

  // front is clear, keep moving forward
  if (!isObstacle(frontDist)) {
    moveForward();
    return;
  }

  // front is blocked, stop and scan both sides
  stopCar();
  Serial.println("front blocked, scanning sides");
  delay(200);

  bool leftBlocked  = scanLeftSide();
  bool rightBlocked = scanRightSide();

  Serial.print("left blocked: ");  Serial.println(leftBlocked);
  Serial.print("right blocked: "); Serial.println(rightBlocked);

  // pick the clearest side to turn towards
  if (!leftBlocked && rightBlocked) {
    Serial.println("turning left");
    turnLeft();
    delay(600);
    stopCar();
    return;
  }

  if (leftBlocked && !rightBlocked) {
    Serial.println("turning right");
    turnRight();
    delay(600);
    stopCar();
    return;
  }

  if (!leftBlocked && !rightBlocked) {
    // both sides clear, default to left
    Serial.println("both sides clear, turning left");
    turnLeft();
    delay(600);
    stopCar();
    return;
  }

  // front, left and right all blocked, try reversing
  Serial.println("all blocked, reversing");
  float rearDist = readDistance(rearTrig, rearEcho);
  Serial.print("rear: "); Serial.println(rearDist);

  if (!isObstacle(rearDist)) {
    moveBackward();
    delay(600);
    stopCar();

    // after reversing, turn to find a clear path
    Serial.println("turning right after reverse");
    turnRight();
    delay(600);
    stopCar();
  } else {
    // completely surrounded, spin in place until front clears
    Serial.println("completely surrounded, spinning");
    while (isObstacle(readDistance(frontTrig, frontEcho))) {
      turnRight();
      delay(200);
      stopCar();
      delay(100);
    }
  }
}
