#include <Arduino.h>
#include <string>
#include <stdio.h>
#include <DHT.h>

#define DHTTYPE DHT11
// Use a GPIO that supports bidirectional digital I/O (not input-only RTC pins)
const uint8_t DHT_PIN = 12; // GPIO16 (Next to ground next to VCC)
// LED PWM pins (three separate ports). Adjust pins to your hardware if needed.
const uint8_t LED_R_PIN = 27; // Red channel
const uint8_t LED_G_PIN = 25; // Green channel
const uint8_t LED_B_PIN = 32; // Blue channel

// ESP32 LEDC PWM configuration
const uint8_t LEDC_CHANNEL_R = 0;
const uint8_t LEDC_CHANNEL_G = 1;
const uint8_t LEDC_CHANNEL_B = 2;
const uint32_t LEDC_FREQUENCY = 5000; // 5 kHz
const uint8_t LEDC_RESOLUTION = 8;   // 8-bit resolution (0-255)


DHT dht(DHT_PIN, DHTTYPE);

// Set to true to turn LEDs ON at boot, false to keep them OFF
const bool LED_BOOT_ON = false;

// put function declarations here:
void processInput();
void initialConnection();
void sendTemperature(float time);
void performTemperatureSend();
void setLEDs(uint8_t r, uint8_t g, uint8_t b);
float readDHT11Temperature();
bool isConnected = false;
unsigned long scheduledSendTime = 0;
bool sendScheduled = false;
const char returnConnection[] = "<PONG:PICO_OK>" ;
const char initConnection[] = "<PING>" ;
const char requestTemperature[] = "<SET_T:" ;
const char returnTemperature[] = "<DATA:" ;
const char setRGB[] = "<SET_RGB:" ;

void setup() {
  Serial.begin(9600);
  dht.begin();
  // Configure ESP32 LEDC PWM channels and attach pins, initialize to off
  ledcSetup(LEDC_CHANNEL_R, LEDC_FREQUENCY, LEDC_RESOLUTION);
  ledcSetup(LEDC_CHANNEL_G, LEDC_FREQUENCY, LEDC_RESOLUTION);
  ledcSetup(LEDC_CHANNEL_B, LEDC_FREQUENCY, LEDC_RESOLUTION);

  ledcAttachPin(LED_R_PIN, LEDC_CHANNEL_R);
  ledcAttachPin(LED_G_PIN, LEDC_CHANNEL_G);
  ledcAttachPin(LED_B_PIN, LEDC_CHANNEL_B);
  ledcWrite(LEDC_CHANNEL_R, 0);
  ledcWrite(LEDC_CHANNEL_G, 0);
  ledcWrite(LEDC_CHANNEL_B, 0);
  // Set LEDs according to LED_BOOT_ON at startup (no handler)
  if (LED_BOOT_ON) {
    setLEDs(255, 255, 255);
    delay(1000); // Keep LEDs on for 1 second at boot if enabled
    setLEDs(0, 0, 0); // Then turn off
  } else {
    setLEDs(0, 0, 0);
  }
  Serial.onReceive(processInput);
}

void loop() {
  // put your main code here, to run repeatedly:
  if (sendScheduled && millis() >= scheduledSendTime) {
    performTemperatureSend();
    sendScheduled = false;
  }
}

void processInput()
{
  if(Serial.available())
  {
    String input = Serial.readStringUntil('\n');
    input.trim(); // Remove any leading/trailing whitespace
    if (input == initConnection)
    {
      initialConnection();
    }
    else if (input.startsWith(requestTemperature))
    {
      String numberStr = input.substring(strlen(requestTemperature));
      float time = numberStr.toFloat();
      sendTemperature(time);
    }
    else if (input.startsWith(setRGB))
    {
      // Expect data in format "R,G,B>" after the prefix. No reply sent.
      String data = input.substring(strlen(setRGB));
      // Remove trailing '>' if present
      if (data.endsWith(">")) {
        data = data.substring(0, data.length() - 1);
      }
      int firstComma = data.indexOf(',');
      int secondComma = data.indexOf(',', firstComma + 1);
      if (firstComma > 0 && secondComma > firstComma) {
        int r = data.substring(0, firstComma).toInt();
        int g = data.substring(firstComma + 1, secondComma).toInt();
        int b = data.substring(secondComma + 1).toInt();
        // Clamp values to 0-255
        if (r < 0) r = 0; else if (r > 255) r = 255;
        if (g < 0) g = 0; else if (g > 255) g = 255;
        if (b < 0) b = 0; else if (b > 255) b = 255;
        setLEDs((uint8_t)r, (uint8_t)g, (uint8_t)b);
      }
    }
    else
    {
      Serial.println("Received: " + input);
    }
  }
}

/// @brief Sends a response to the host to confirm that the connection is established and ready for communication.
void initialConnection()
{
  Serial.println(returnConnection);
  isConnected = true;
}

void sendTemperature(float time)
{
  // Non-blocking scheduling: if time <= 0 send immediately, otherwise schedule
  if (time <= 0.0f) {
    performTemperatureSend();
  } else {
    scheduledSendTime = millis() + (unsigned long)time;
    sendScheduled = true;
  }
}

void performTemperatureSend()
{
  float temperature = readDHT11Temperature();
  if (isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
  } else {
    Serial.println(returnTemperature + String(temperature) + ">");
  }
}

// Set LED PWM values for R/G/B channels. Values expected 0-255.
void setLEDs(uint8_t r, uint8_t g, uint8_t b)
{
  // Use ESP32 LEDC channels (non-blocking). Values 0-255.
  ledcWrite(LEDC_CHANNEL_R, 255 - r);
  ledcWrite(LEDC_CHANNEL_G, 255 - g);
  ledcWrite(LEDC_CHANNEL_B, 255 - b);
}

/// @brief Reads the temperature from the DHT11 sensor and returns it as a float. If the reading fails, it returns NaN.
/// @return The temperature in Celsius, or NaN if the reading fails.
float readDHT11Temperature()
{
  float t = dht.readTemperature(); // Celsius
  if (isnan(t)) {
    return NAN;
  }
  return t;
}