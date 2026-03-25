#include <Arduino.h>
#include <string>
#include <DHT.h>

#define DHTTYPE DHT11
// Use a GPIO that supports bidirectional digital I/O (not input-only RTC pins)
const uint8_t DHT_PIN = 16; // GPIO16 (Next to ground next to VCC)
DHT dht(DHT_PIN, DHTTYPE);

// put function declarations here:
void processInput();
void initialConnection();
void sendTemperature(float time);
void performTemperatureSend();
float readDHT11Temperature();
bool isConnected = false;
unsigned long scheduledSendTime = 0;
bool sendScheduled = false;
const char returnConnection[] = "<PONG:PICO_OK>" ;
const char initConnection[] = "<PING>" ;
const char requestTemperature[] = "<SET_T:" ;
const char returnTemperature[] = "" ;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  dht.begin();
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
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" °C");
  }
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