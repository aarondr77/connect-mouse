/*
 * Project 2: "Arduino plant" for Nominal Connect + LabJack T4
 *
 * Pin roles:
 *   D2  (ENABLE)  — input from LabJack FIO4 (HIGH = system on; T4 screw terminal)
 *   D13 (LED)     — built-in LED: solid ON when running, slow blink when off
 *   D9  (PWM)     — process output (optional LED on breadboard for visual feedback)
 *   A0            — joystick VRx (X axis, 0–5 V)
 *
 * Install: Arduino IDE → File → Open → this file → Upload
 * Board:   Arduino UNO
 * Port:    your USB serial port (e.g. /dev/cu.usbmodem… on Mac)
 */

const int ENABLE_PIN = 2;
const int STATUS_LED = 13;
const int PWM_OUT = 9;
const int JOYSTICK_X_PIN = A0;

void setup() {
  pinMode(ENABLE_PIN, INPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(PWM_OUT, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
  analogWrite(PWM_OUT, 0);
}

void loop() {
  bool enabled = digitalRead(ENABLE_PIN) == HIGH;

  if (enabled) {
    int stickX = analogRead(JOYSTICK_X_PIN);
    int pwm = map(stickX, 0, 1023, 0, 255);
    analogWrite(PWM_OUT, pwm);
    digitalWrite(STATUS_LED, HIGH);
    delay(20);
  } else {
    analogWrite(PWM_OUT, 0);
    // Slow blink = "plant is idle, waiting for enable"
    bool blink = ((millis() / 500) % 2) == 0;
    digitalWrite(STATUS_LED, blink ? HIGH : LOW);
  }
}
