#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <ArduinoJson.h>

// Hardware pins
const int DHT_PIN = 15;
const int BUZZER_PIN = 4;

// Network credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";
const char* mqtt_server = "192.168.1.21";
const char* mqtt_username = "user";
const char* mqtt_password = "user";

// MQTT Topics
const char* WEATHER_TOPIC = "arduino/Weather";
const char* STATUS_REQUEST_TOPIC = "mqtt/request";
const char* STATUS_RESPONSE_TOPIC = "mqtt/response";
const char* THRESHOLD_TOPIC = "arduino/Weather_threshold";
const char* ALERT_TOPIC = "arduino/weather_alerts";

// Global variables
DHTesp dht;
WiFiClient espClient;
PubSubClient client(espClient);

// Thresholds with safe defaults
float temp_threshold = 30.0;
float hum_threshold = 70.0;

// Buzzer control
unsigned long buzzerStartTime = 0;
const long buzzerDuration = 500;

// System control
bool systemActive = false;
unsigned long lastMsg = 0;

void setup_wifi(){
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  randomSeed(micros());

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

// Replace existing buzzer functions with:
void activate_buzzer() {
  ledcSetup(0, 1000, 8);      // Channel 0, 1kHz, 8-bit resolution
  ledcAttachPin(BUZZER_PIN, 0);
  ledcWriteTone(0, 1000);     // 1kHz tone
  buzzerStartTime = millis();
  Serial.println("ALERT: Buzzer activated");
}

void check_buzzer() {
  if (buzzerStartTime != 0 && (millis() - buzzerStartTime) > buzzerDuration) {
    ledcWriteTone(0, 0);      // Stop tone
    ledcDetachPin(BUZZER_PIN);
    buzzerStartTime = 0;
    Serial.println("Buzzer deactivated");
  }
}

void handle_threshold(String payload) {
  if (payload.length() == 0) {
    Serial.println("Received empty threshold payload");
    return;
  }

  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.print("Threshold JSON error: ");
    Serial.println(error.c_str());
    return;
  }

  if (doc["temp"].is<float>()) {
    temp_threshold = doc["temp"];
    Serial.printf("New temp threshold: %.1f°C", temp_threshold);
  }
  
  if (doc["hum"].is<float>()) {
    hum_threshold = doc["hum"];
    Serial.printf("New humidity threshold: %.1f%%", hum_threshold);
  }
}

void check_thresholds(float temp, float hum) {
  if (!systemActive) return;
  
  bool shouldAlert = false;
  String alertMessage = "";
  
  if (temp > temp_threshold) {
    alertMessage += "HighTemp:" + String(temp, 1) + " °C > " + String(temp_threshold, 1) + " °C";
    shouldAlert = true;
  }
  
  if (hum > hum_threshold) {
    alertMessage += "HighHum:" + String(hum, 1) + " % > " + String(hum_threshold, 1) + " %";
    shouldAlert = true;
  }

  if (shouldAlert) {
    client.publish(ALERT_TOPIC, alertMessage.c_str());
    Serial.println("Published alert: " + alertMessage);
    
    if (buzzerStartTime == 0) {
      activate_buzzer();
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i=0; i<length; i++) message += (char)payload[i];
  
  Serial.printf("Received [%s]: %s", topic, message.c_str());
  if (String(topic) == STATUS_REQUEST_TOPIC && message == "TurnOFF") {
    systemActive = false;
    Serial.println("System Deactivated ");
  }
  if (String(topic) == STATUS_REQUEST_TOPIC && message == "status_request") {
    systemActive = true;
    client.publish(STATUS_RESPONSE_TOPIC, "Board : ESP32 Status : Connected");
    Serial.println("System activated by status request");
  }
  else if (String(topic) == THRESHOLD_TOPIC) {
    handle_threshold(message);
  }

}

void reconnect() {
  while (!client.connected()) {
    Serial.print("MQTT connection...");
    if (client.connect("ESP32Client", mqtt_username, mqtt_password)) {
      Serial.println("connected!");
      client.subscribe(STATUS_REQUEST_TOPIC);
      client.subscribe(THRESHOLD_TOPIC);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5s...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  dht.setup(DHT_PIN, DHTesp::DHT22);
  
  Serial.println("System initialized (waiting for activation)");
  Serial.printf("Default Temp Threshold: %.1f°C", temp_threshold);
  Serial.printf("Default Hum Threshold: %.1f%%", hum_threshold);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  check_buzzer();

  // Only run main logic if system is active
  if (systemActive) {
    unsigned long now = millis();
    if (now - lastMsg > 1000) {
      lastMsg = now;
      
      TempAndHumidity data = dht.getTempAndHumidity();
      if (isnan(data.temperature) || isnan(data.humidity)) {
        Serial.println("Sensor error!");
        return;
      }

      String weatherData = "Temperature: " + String(data.temperature, 1) + "°C, " +
                        "Temperature: " + String((data.temperature * 9/5) + 32, 1) + "°F, " +
                        "Humidity: " + String(data.humidity, 1) + "%";
      client.publish(WEATHER_TOPIC, weatherData.c_str());
      
      check_thresholds(data.temperature, data.humidity);
    }
  }
}