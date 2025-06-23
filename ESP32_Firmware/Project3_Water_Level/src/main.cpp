#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

// System state
bool systemActive = false;

// Wi-Fi Configuration
const char* ssid = "Wokwi-GUEST";          // Replace with your Wi-Fi SSID
const char* password = "";                 // Replace with your Wi-Fi password

// MQTT Configuration
const char* mqttServer = "192.168.1.21";   // MQTT Broker IP
const int mqttPort = 1883;                 // MQTT Broker Port
const char* mqttTopicRequest = "mqtt/request";
const char* mqttTopicResponse = "mqtt/response";
const char* mqttTopicSensor = "arduino/sensor"; // MQTT Topic for Sensor Data
const char* mqttTopicSensorControl = "arduino/sensor_Control";
// MQTT Authentication
const char* mqttUsername = "demo";         // MQTT Username
const char* mqttPassword = "azerty";         // MQTT Password

// Hardware pins
const int relayIn  = 17;  // Fill valve relay
const int relayOut = 16;  // Drain valve relay
const int trigPin  = 22;  // Ultrasonic sensor trigger
const int echoPin  = 23;  // Ultrasonic sensor echo

// MQTT client
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Last publish time for rate limiting
unsigned long lastPublishTime = 0;
const int publishInterval = 500;  // 500ms between publishes

void Fill() {
    digitalWrite(relayIn, HIGH);   // Turn on fill valve
    digitalWrite(relayOut, LOW);   // Turn off drain valve
}

void Drain() {
    digitalWrite(relayIn, LOW);    // Turn off fill valve
    digitalWrite(relayOut, HIGH);  // Turn on drain valve
}

void FillDrain_OFF() {
    digitalWrite(relayIn, LOW);    // Turn off fill valve
    digitalWrite(relayOut, LOW);   // Turn off drain valve
}

void handleMQTTCallback(char* topic, byte* payload, unsigned int length) {
    String topicStr = String(topic);
    String message = "";
    
    // Convert payload to string
    for (unsigned int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.print("Message arrived [");
    Serial.print(topicStr);
    Serial.print("] ");
    Serial.println(message);
    
    // Handle status request message
    if (String(topic) == mqttTopicRequest && message == "TurnOFF") {
        systemActive = false;
        Serial.println("System Deactivated ");
    }
    if (topicStr == mqttTopicRequest && message == "status_request") {
        systemActive = true;
        mqttClient.publish(mqttTopicResponse, "Board : ESP32 Status : Connected");
        Serial.println("System activated by status request");
    } 
    if(systemActive){
      // Handle control commands
      if (topicStr == mqttTopicSensorControl) {
          if (message == "FILL_ON DRAIN_OFF") {
              Fill();
              Serial.println("Command: Fill ON, Drain OFF");
          } else if (message == "FILL_OFF DRAIN_ON") {
              Drain();
              Serial.println("Command: Fill OFF, Drain ON");
          } else if (message == "FILL_DRAIN_OFF") {
              FillDrain_OFF();
              Serial.println("Command: Fill OFF, Drain OFF");
          }
      }
    }
}

void setupWiFi() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nConnected to WiFi");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nFailed to connect to WiFi");
    }
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        String clientId = "ESP32Client-" + String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str(), mqttUsername, mqttPassword)) {
            Serial.println("Connected to MQTT broker");
            mqttClient.subscribe(mqttTopicSensorControl);
            mqttClient.subscribe(mqttTopicSensor);
            mqttClient.subscribe(mqttTopicRequest);
            mqttClient.publish(mqttTopicResponse, "Board : ESP32 Status : Connected");
        } else {
            Serial.print("Failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" retrying in 2 seconds");
            delay(2000);
        }
    }
}

void measureAndPublishWaterLevel() {
    // Trigger ultrasonic pulse
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    // Measure echo duration
    long duration = pulseIn(echoPin, HIGH);
    
    // Calculate distance in cm
    int distance = duration * 0.034 / 2;
    
    // Convert to water level percentage (400cm=0%, 0cm=100%)
    int waterLevelPercent = constrain(100 - (distance * 100 / 400), 0, 100);
    
    // Prepare and publish MQTT message
    char sensorMessage[50];
    snprintf(sensorMessage, sizeof(sensorMessage), "Water Level: %d", waterLevelPercent);
    mqttClient.publish(mqttTopicSensor, sensorMessage);
}

void setup() {
    Serial.begin(9600);
    
    // Set pin modes
    pinMode(relayIn, OUTPUT);
    pinMode(relayOut, OUTPUT);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    
    // Ensure relays are off at startup
    FillDrain_OFF();
    
    // Setup WiFi and MQTT
    setupWiFi();
    mqttClient.setServer(mqttServer, mqttPort);
    mqttClient.setCallback(handleMQTTCallback);
}

void loop() {
    // Handle MQTT connection
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();
    
    // Measure and publish water level if system is active
    if (systemActive) {
        unsigned long currentMillis = millis();
        if (currentMillis - lastPublishTime >= publishInterval) {
            measureAndPublishWaterLevel();
            lastPublishTime = currentMillis;
        }
    }
}