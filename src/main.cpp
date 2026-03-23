#include <Arduino.h>
#include <string>

#include <DHT.h>

#define DHTTYPE DHT11
const uint8_t DHT_PIN = 13; // GPIO13
DHT dht(DHT_PIN, DHTTYPE);

// put function declarations here:
void processInput();
void initialConnection();
float readDHT11Temperature();
bool isConnected = false;
const char returnConnection[] = "<PONG:PICO_OK>" ;
const char initConnection[] = "<PING>" ;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  dht.begin();
  Serial.onReceive(processInput);
}

void loop() {
  // put your main code here, to run repeatedly:
}

void processInput()
{
  if(Serial.available())
  {
    String input = Serial.readStringUntil('\n');
    input.trim(); // Remove any leading/trailing whitespace
    Serial.println(readDHT11Temperature());
    if (input == initConnection)
    {
      initialConnection();
    }
    else
    {
      Serial.println("Received: " + input);
    }
  }
}

void initialConnection()
{
  Serial.println(returnConnection);
  isConnected = true;
}

float readDHT11Temperature()
{
  float t = dht.readTemperature(); // Celsius
  if (isnan(t)) {
    return NAN;
  }
  return t;
}