/*
 * Project 3: Arduino enable node (LabJack is the only sensor path to Connect)
 *
 * Pin roles:
 *   D2  (ENABLE)  — input from LabJack FIO4 (HIGH = system on)
 *   D13 (LED)     — solid ON when enabled, slow blink when idle
 *
 * Joystick and HC-SR04 are read by the LabJack (AIN0/AIN1, FIO5/FIO6), not here.
 *
 * Board: Arduino UNO
 */

const int ENABLE_PIN = 2;
const int STATUS_LED = 13;

void setup() {
  pinMode(ENABLE_PIN, INPUT);
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
}

void loop() {
  bool enabled = digitalRead(ENABLE_PIN) == HIGH;

  if (enabled) {
    digitalWrite(STATUS_LED, HIGH);
  } else {
    bool blink = ((millis() / 500) % 2) == 0;
    digitalWrite(STATUS_LED, blink ? HIGH : LOW);
  }

  delay(20);
}
