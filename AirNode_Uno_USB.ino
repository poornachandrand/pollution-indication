/*
 * ============================================================
 * AirNode — Arduino Uno Sketch (USB Direct Mode)
 * ============================================================
 * WIRING:
 *   DHT11 DATA pin  → Uno D7  (+ 10kΩ pull-up to 5V)
 *   DHT11 VCC       → 5V
 *   DHT11 GND       → GND
 *   MQ135 AOUT      → A0
 *   MQ135 VCC       → 5V
 *   MQ135 GND       → GND
 *   Green LED       → D4  (via 220Ω)
 *   Yellow LED      → D5  (via 220Ω)
 *   Red LED         → D6  (via 220Ω)
 *   Buzzer (+)      → D9
 *   All LED cathodes→ GND
 *
 * NO NodeMCU needed. NO WiFi needed.
 * Just plug Uno into PC via USB.
 *
 * REQUIRED LIBRARIES:
 *   - DHT sensor library (Adafruit)
 *   - Adafruit Unified Sensor
 *
 * OUTPUT: one CSV line every 2 seconds on Serial (9600 baud)
 *   temp,humidity,airQuality,ledState
 *   e.g.  24.00,61.00,342,green
 * ============================================================
 */

#include <DHT.h>

// ── Pin Definitions ─────────────────────────────────────────
#define DHT_PIN       7
#define DHT_TYPE      DHT11    // Change to DHT22 if using DHT22
#define MQ135_PIN     A0
#define LED_GREEN     4
#define LED_YELLOW    5
#define LED_RED       6
#define BUZZER_PIN    9

// ── Air Quality Thresholds (MQ135 raw ADC 0–1023) ──────────
#define THRESHOLD_CAUTION   300
#define THRESHOLD_DANGER    600

// ── Read interval ───────────────────────────────────────────
#define READ_INTERVAL_MS    2000

// ── Objects ─────────────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastReadTime = 0;

void setup() {
  Serial.begin(9600);
  
  pinMode(LED_GREEN,  OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED,    OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  dht.begin();

  // Boot flash
  setLEDs(HIGH, HIGH, HIGH);
  delay(500);
  setLEDs(LOW, LOW, LOW);

  // Send header so Python knows stream started
  Serial.println(F("AIRNODE_START"));
}

void loop() {
  unsigned long now = millis();

  if (now - lastReadTime >= READ_INTERVAL_MS) {
    lastReadTime = now;

    float humidity    = dht.readHumidity();
    float temperature = dht.readTemperature();

    if (isnan(humidity) || isnan(temperature)) {
      Serial.println(F("ERROR,DHT_READ_FAILED"));
      return;
    }

    int airQuality = analogRead(MQ135_PIN);
    String ledState;

    if (airQuality >= THRESHOLD_DANGER) {
      ledState = "red";
      setLEDs(LOW, LOW, HIGH);
      digitalWrite(BUZZER_PIN, HIGH);
    } else if (airQuality >= THRESHOLD_CAUTION) {
      ledState = "yellow";
      setLEDs(LOW, HIGH, LOW);
      digitalWrite(BUZZER_PIN, LOW);
    } else {
      ledState = "green";
      setLEDs(HIGH, LOW, LOW);
      digitalWrite(BUZZER_PIN, LOW);
    }

    // CSV line → read by Python bridge
    Serial.print(temperature, 2);
    Serial.print(",");
    Serial.print(humidity, 2);
    Serial.print(",");
    Serial.print(airQuality);
    Serial.print(",");
    Serial.println(ledState);
  }
}

void setLEDs(int g, int y, int r) {
  digitalWrite(LED_GREEN,  g);
  digitalWrite(LED_YELLOW, y);
  digitalWrite(LED_RED,    r);
}
