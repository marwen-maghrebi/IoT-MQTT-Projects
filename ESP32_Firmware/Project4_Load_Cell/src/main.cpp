#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HX711_ADC.h>

// Load Cell pins
const int HX711_dout = 4; // MCU > HX711 dout pin
const int HX711_sck = 5;  // MCU > HX711 sck pin

// HX711 constructor
HX711_ADC LoadCell(HX711_dout, HX711_sck);

// System state
bool systemActive = false;

// Wi-Fi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT server and credentials
const char* mqtt_server = "192.168.1.21"; // Updated server address
const char* mqtt_username = "user";       // MQTT username
const char* mqtt_password = "user";       // MQTT password
const char* mqttTopicRequest = "mqtt/request";
const char* mqttTopicResponse = "mqtt/response";
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsg = 0;
float loadCellValue = 0;
const int numUpdates = 100; // Number of LoadCell.update() calls before publishing

void setup_wifi() {
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

void callback(char* topic, byte* payload, unsigned int length) {
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
        client.publish(mqttTopicResponse, "Board : ESP32 Status : Connected");
        Serial.println("System activated by status request");
    }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    // Connect with username and password
    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected");
      client.subscribe("mqtt/request");  // Add this line to subscribe to status requests
      client.subscribe ("mqtt/responce");
      client.subscribe("arduino/LoadCell"); // Subscribe to the LoadCell topic
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    } 
  }
}

void setup() {
  // Initialize serial communication
  Serial.begin(57600);
  Serial.println("Starting...");

  // Initialize Load Cell
  LoadCell.begin();
  unsigned long stabilizingtime = 2000; // Stabilizing time for the load cell
  boolean _tare = true; // Perform tare during startup
  LoadCell.start(stabilizingtime, _tare);

  if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
    Serial.println("Timeout, check MCU > HX711 wiring and pin designations");
    while (1);
  } else {
    LoadCell.setCalFactor(420.00); // Set your calibration value here (e.g., 420.00)
    Serial.println("Load Cell initialized");
  }

  // Connect to Wi-Fi
  setup_wifi();

  // Configure MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  // Reconnect to MQTT if disconnected
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
    if (systemActive) {
      // Read load cell data and publish after 5 updates
      unsigned long now = millis();
      if (now - lastMsg > 500) { // Check every 2 seconds
        lastMsg = now;

        // Call LoadCell.update() 5 times before reading the value
        for (int i = 0; i < numUpdates; i++) {
          LoadCell.update();
          delay(1); // Small delay between updates (optional)
        }

        // Get the smoothed value after 5 updates
        loadCellValue = LoadCell.getData();

        // Publish the load cell value to the topic "arduino/LoadCell"
        String payload = "Load: " + String(loadCellValue, 2) + " kg";
        client.publish("arduino/LoadCell", payload.c_str());
        Serial.print("Published: ");
        Serial.println(payload);
      }
    }
}