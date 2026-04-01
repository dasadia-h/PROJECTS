const int building1_underground_low  = 2;
const int building1_underground_high = 3;
const int building1_overhead_low     = 4;
const int building1_overhead_high    = 5;
const int building1_pump             = 6;

const int building2_underground_low  = 7;
const int building2_underground_high = 8;
const int building2_overhead_low     = 9;
const int building2_overhead_high    = 10;
const int building2_pump             = 11;

const int building3_underground_low  = 12;
const int building3_underground_high = 13;
const int building3_overhead_low     = A0;
const int building3_overhead_high    = A1;
const int building3_pump             = A2;


void setup() {
  // float sensor pins 
  int sensorPins[] = {
    building1_underground_low, building1_underground_high,
    building1_overhead_low,    building1_overhead_high,
    building2_underground_low, building2_underground_high,
    building2_overhead_low,    building2_overhead_high,
    building3_underground_low, building3_underground_high,
    building3_overhead_low,    building3_overhead_high
  };
  for (int i = 0; i < 12; i++) {
    pinMode(sensorPins[i], INPUT_PULLUP);
  }

  // pump relay pins 
  pinMode(building1_pump, OUTPUT);
  pinMode(building2_pump, OUTPUT);
  pinMode(building3_pump, OUTPUT);
  digitalWrite(building1_pump, LOW);
  digitalWrite(building2_pump, LOW);
  digitalWrite(building3_pump, LOW);

  Serial.begin(9600);
  Serial.println("flood water system ready");
}


// decide whether to run the pump for a single building
void managePump(int undergroundLow, int undergroundHigh, int overheadLow, int overheadHigh, int pump, String buildingName) {
  bool undergroundHasWater = digitalRead(undergroundHigh) == LOW;
  bool undergroundIsLow    = digitalRead(undergroundLow)  == HIGH;
  bool overheadIsFull      = digitalRead(overheadHigh)    == LOW;
  bool overheadNeedsWater  = digitalRead(overheadLow)     == HIGH;

  // run pump only if underground has water and overhead needs a top-up
  if (undergroundHasWater && overheadNeedsWater && !overheadIsFull) {
    digitalWrite(pump, HIGH);
    Serial.println(buildingName + ": pump ON");
  }
  // stop pump if underground is empty or overhead is full
  else if (undergroundIsLow || overheadIsFull) {
    digitalWrite(pump, LOW);
    Serial.println(buildingName + ": pump OFF");
  }
}


void loop() {
  managePump(
    building1_underground_low, building1_underground_high,
    building1_overhead_low,    building1_overhead_high,
    building1_pump,            "building 1"
  );

  managePump(
    building2_underground_low, building2_underground_high,
    building2_overhead_low,    building2_overhead_high,
    building2_pump,            "building 2"
  );

  managePump(
    building3_underground_low, building3_underground_high,
    building3_overhead_low,    building3_overhead_high,
    building3_pump,            "building 3"
  );

  delay(1000);
}
