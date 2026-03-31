const int xPin = A0;
const int yPin = A1;

const int forwardPin  = 10;
const int backwardPin = 11;
const int leftPin     = 12;
const int rightPin    = 13;

// Analog value at flat position, adjust if readings differ
const int centerValue   = 512;
const int tiltThreshold = 100;

void setup() {
  pinMode(forwardPin,  OUTPUT);
  pinMode(backwardPin, OUTPUT);
  pinMode(leftPin,     OUTPUT);
  pinMode(rightPin,    OUTPUT);

  stopAll();
  Serial.begin(9600);
  Serial.println("Gesture Controlled Car - Ready");
}

void loop() {
  int xVal = analogRead(xPin);
  int yVal = analogRead(yPin);

  Serial.print("X: "); Serial.print(xVal);
  Serial.print("  Y: "); Serial.println(yVal);

  stopAll();

  // Tilt forward
  if (yVal > centerValue + tiltThreshold) {
    digitalWrite(forwardPin, HIGH);
    Serial.println("Forward");
  }
  // Tilt backward
  else if (yVal < centerValue - tiltThreshold) {
    digitalWrite(backwardPin, HIGH);
    Serial.println("Backward");
  }
  // Tilt left
  else if (xVal < centerValue - tiltThreshold) {
    digitalWrite(leftPin, HIGH);
    Serial.println("Left");
  }
  // Tilt right
  else if (xVal > centerValue + tiltThreshold) {
    digitalWrite(rightPin, HIGH);
    Serial.println("Right");
  }
  else {
    Serial.println("Idle");
  }

  delay(100);
}

// Hand flat so car stops
void stopAll() {
  digitalWrite(forwardPin,  LOW);
  digitalWrite(backwardPin, LOW);
  digitalWrite(leftPin,     LOW);
  digitalWrite(rightPin,    LOW);
}
