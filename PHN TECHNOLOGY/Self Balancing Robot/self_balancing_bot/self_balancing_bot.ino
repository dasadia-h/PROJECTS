#include <Wire.h>
#include <MPU6050.h>

// motor A (left)
const int motorA1  = 5;
const int motorA2  = 6;
const int enableA  = 9;

// motor B (right)
const int motorB1  = 7;
const int motorB2  = 8;
const int enableB  = 10;

MPU6050 imu;

// PID tuning constants (adjust these to tune balance behaviour)
float kp = 21.0;
float ki = 0.8;
float kd = 0.9;

// the angle at which the robot is perfectly upright — calibrate for your build
float targetAngle = 0.0;

float previousError = 0;
float integral      = 0;
unsigned long previousTime = 0;

// complementary filter weight blends accelerometer and gyroscope readings
const float alpha = 0.98;
float tiltAngle   = 0.0;


void setup() {
  pinMode(motorA1, OUTPUT);
  pinMode(motorA2, OUTPUT);
  pinMode(enableA, OUTPUT);
  pinMode(motorB1, OUTPUT);
  pinMode(motorB2, OUTPUT);
  pinMode(enableB, OUTPUT);

  stopMotors();

  Wire.begin();
  imu.initialize();

  Serial.begin(9600);
  if (imu.testConnection()) {
    Serial.println("MPU6050 connected");
  } else {
    Serial.println("MPU6050 not found");
  }

  previousTime = millis();
}


// read tilt angle using a complementary filter combining accel and gyro
float getTiltAngle(float dt) {
  int16_t ax, ay, az, gx, gy, gz;
  imu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  float accelAngle = atan2(ay, az) * 180.0 / PI;
  float gyroRate   = gx / 131.0;

  tiltAngle = alpha * (tiltAngle + gyroRate * dt) + (1 - alpha) * accelAngle;
  return tiltAngle;
}


// run the PID calculation and return a motor speed value
float computePID(float currentAngle, float dt) {
  float error      = targetAngle - currentAngle;
  integral        += error * dt;
  float derivative = (error - previousError) / dt;
  previousError    = error;

  return (kp * error) + (ki * integral) + (kd * derivative);
}


// both motors forward 
void driveForward(int speed) {
  speed = constrain(speed, 0, 255);
  analogWrite(enableA, speed);
  analogWrite(enableB, speed);
  digitalWrite(motorA1, HIGH);
  digitalWrite(motorA2, LOW);
  digitalWrite(motorB1, HIGH);
  digitalWrite(motorB2, LOW);
}


// both motors backward
void driveBackward(int speed) {
  speed = constrain(speed, 0, 255);
  analogWrite(enableA, speed);
  analogWrite(enableB, speed);
  digitalWrite(motorA1, LOW);
  digitalWrite(motorA2, HIGH);
  digitalWrite(motorB1, LOW);
  digitalWrite(motorB2, HIGH);
}


void stopMotors() {
  analogWrite(enableA, 0);
  analogWrite(enableB, 0);
  digitalWrite(motorA1, LOW);
  digitalWrite(motorA2, LOW);
  digitalWrite(motorB1, LOW);
  digitalWrite(motorB2, LOW);
}


void loop() {
  unsigned long currentTime = millis();
  float dt = (currentTime - previousTime) / 1000.0;
  previousTime = currentTime;

  float angle  = getTiltAngle(dt);
  float output = computePID(angle, dt);

  Serial.print("angle: "); Serial.print(angle);
  Serial.print("  PID output: "); Serial.println(output);

  // if the robot has fallen too far, stop 
  if (abs(angle) > 45) {
    stopMotors();
    return;
  }

  // positive output means leaning forward, drive forward to correct
  if (output > 0) {
    driveForward((int)abs(output));
  } else {
    driveBackward((int)abs(output));
  }

  delay(5);
}
