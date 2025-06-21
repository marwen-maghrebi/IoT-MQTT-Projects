#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// Wi-Fi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT server and credentials
const char* mqtt_server = "192.168.1.21"; // Updated server address
const char* mqtt_username = "user";       // MQTT username
const char* mqtt_password = "user";       // MQTT password

// MQTT topic
const char* mqtt_topic = "arduino/MPU6050";

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_MPU6050 mpu;

unsigned long lastMsg = 0;

// System state
bool systemActive = false;

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
  // Handle status request message

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
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    // Connect with username and password
    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected");
      client.subscribe("mqtt/request");  // Add this line to subscribe to status requests
      client.subscribe ("mqtt/response");
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
  Serial.begin(115200);

  // Connect to Wi-Fi
  setup_wifi();

  // Configure MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  // Initialize MPU6050 sensor
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  // Set up MPU6050 configurations
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);   // Accelerometer range: ±8g
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);        // Gyroscope range: ±500°/s
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);     // Filter bandwidth: 21 Hz

  delay(100);
}

void loop() {
  // Reconnect to MQTT if disconnected
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  if (systemActive){
    // Read and publish sensor data every 2 seconds
    unsigned long now = millis();
    if (now - lastMsg > 1000) {
      lastMsg = now;

      // Get new sensor events
      sensors_event_t a, g, temp;
      mpu.getEvent(&a, &g, &temp);

      // Convert accelerometer data from m/s² to g
      float accel_x_g = a.acceleration.x / 9.81;
      float accel_y_g = a.acceleration.y / 9.81;
      float accel_z_g = a.acceleration.z / 9.81;

      // Convert gyroscope data from rad/s to °/sec
      float gyro_x_deg = g.gyro.x * (180.0 / PI);
      float gyro_y_deg = g.gyro.y * (180.0 / PI);
      float gyro_z_deg = g.gyro.z * (180.0 / PI);

      // Create a JSON-like string with sensor data and units
      String sensorData = "{";
      sensorData += "\"accelX\":" + String(accel_x_g, 2) + ",";
      sensorData += "\"accelY\":" + String(accel_y_g, 2) + ",";
      sensorData += "\"accelZ\":" + String(accel_z_g, 2) + ",";
      sensorData += "\"gyroX\":" + String(gyro_x_deg, 2) + ",";
      sensorData += "\"gyroY\":" + String(gyro_y_deg, 2) + ",";
      sensorData += "\"gyroZ\":" + String(gyro_z_deg, 2) + ",";
      sensorData += "\"temp\":" + String(temp.temperature, 2);
      sensorData += "}";

      // Publish the sensor data to the MQTT topic
      client.publish(mqtt_topic, sensorData.c_str());

      // Print the data to the Serial Monitor for debugging
      Serial.println(sensorData);
    }
  }
  
}