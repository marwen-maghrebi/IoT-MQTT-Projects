#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

// Sensor Configuration
#define Pin (32)         // Analog input for MQ2

// LED and Buzzer Pins
#define GREEN_LED  12
#define YELLOW_LED 14
#define RED_LED    27
#define BUZZER_PIN 13

// Gas concentration range in ppm
#define MIN_PPM 300
#define MAX_PPM 1000

// Buzzer configuration
#define BUZZER_CHANNEL 0
#define BUZZER_FREQ 2000
#define BUZZER_RESOLUTION 8

// Wi-Fi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT server and credentials
const char* mqtt_server = "192.168.1.21";
const char* mqtt_username = "user";
const char* mqtt_password = "user";

WiFiClient espClient;
PubSubClient client(espClient);

int gas_value_ppm = 0;
float voltage_value = 0.0;
unsigned long lastMsg = 0;
bool systemActive = false;

// Simplified sensor reading function for Wokwi
int readGasSensor() {
  int raw_value = analogRead(Pin);
  
  // Add some noise simulation for more realistic readings
  raw_value += random(-50, 50);
  
  // Constrain to valid ADC range
  raw_value = constrain(raw_value, 0, 4095);
  
  return raw_value;
}

// Convert raw ADC value to PPM
int convertToPPM(int raw_value) {
  // Simple linear mapping from ADC range to PPM range
  return map(raw_value, 0, 4095, MIN_PPM, MAX_PPM);
}

// Convert raw ADC to voltage
float convertToVoltage(int raw_value) {
  return (raw_value * 3.3) / 4095.0;
}

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
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  // Convert payload to a string
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);  
  if (String(topic) == "mqtt/request"  && message == "TurnOFF") {
        systemActive = false;
        Serial.println("System Deactivated ");
    }
  if (String(topic) == "mqtt/request" && message == "status_request") {
    systemActive = true;

    client.publish("mqtt/response", "Board : ESP32 Status : Connected");
    return;  // Exit after handling the status request
  }
}

void reconnect() {
  // Check if the client is already connected
  if (client.connected()) {
    return; // Exit if already connected
  }
  Serial.print("Attempting MQTT connection...");
  String clientId = "ESP32Client-";
  clientId += String(random(0xffff), HEX);

  // Connect with username and password
  if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
    Serial.println("Connected");
    client.subscribe("mqtt/request");  // Subscribe to status requests
    client.subscribe("mqtt/respence");
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
    Serial.println(" try again in 5 seconds");
    delay(5000);
  }
}


void setup() {
  Serial.begin(9600);
  Serial.println("=== ESP32 Gas Detection System ===");
  
  // Initialize pins
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(Pin, INPUT);
  
  // Initialize buzzer
  ledcSetup(BUZZER_CHANNEL, BUZZER_FREQ, BUZZER_RESOLUTION);
  ledcAttachPin(BUZZER_PIN, BUZZER_CHANNEL);
  ledcWrite(BUZZER_CHANNEL, 0);
  
  Serial.println("Hardware initialized");
  
  // Test sensor reading
  int testReading = analogRead(Pin);
  Serial.print("Initial sensor reading: ");
  Serial.println(testReading);
  
  if (testReading == 0) {
    Serial.println("Warning: Sensor may not be connected properly");
  } else {
    Serial.println("Sensor connected successfully");
  }
  
  // Initialize Wi-Fi and MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  // Startup sequence - flash all LEDs
  for (int i = 0; i < 3; i++) {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(YELLOW_LED, HIGH);
    digitalWrite(RED_LED, HIGH);
    delay(200);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, LOW);
    delay(200);
  }
  
  Serial.println("=== System Ready ===");
}

void loop() {
  // Handle MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  if (systemActive) {
    // Read sensor data
    int raw_value = readGasSensor();
    gas_value_ppm = convertToPPM(raw_value);
    voltage_value = convertToVoltage(raw_value);
    
    // Publish data every second
    unsigned long now = millis();
    if (now - lastMsg > 1000) {
      lastMsg = now;
      
      // Create JSON payload
      String gasData = "{\"gas_ppm\":" + String(gas_value_ppm) + 
                ",\"voltage\":" + String(voltage_value, 2) + "}";
      
      // Publish to MQTT
      if (client.connected()) {
        client.publish("arduino/gas", gasData.c_str());
      }
      
      // Print to serial
      Serial.println("Gas Data: " + gasData);
    }
    
    // Control LEDs and buzzer based on gas levels
    if (gas_value_ppm > 900) {
      // HIGH DANGER - Red LED + Buzzer
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, LOW);
      digitalWrite(RED_LED, HIGH);
      ledcWrite(BUZZER_CHANNEL, 128); // 50% duty cycle
      Serial.println("ALERT: High gas concentration detected!");
    }
    else if (gas_value_ppm > 600) {
      // MEDIUM DANGER - Yellow LED
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, HIGH);
      digitalWrite(RED_LED, LOW);
      ledcWrite(BUZZER_CHANNEL, 0);
    }
    else {
      // SAFE - Green LED
      digitalWrite(GREEN_LED, HIGH);
      digitalWrite(YELLOW_LED, LOW);
      digitalWrite(RED_LED, LOW);
      ledcWrite(BUZZER_CHANNEL, 0);
    }
  } else {
    // System inactive - turn off all indicators
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, LOW);
    ledcWrite(BUZZER_CHANNEL, 0);
  }
  
  delay(500);
}