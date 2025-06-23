#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

bool systemActive = false;

// LED pins
const int RED_LED1_PIN = 2;
const int RED_LED2_PIN = 0;
const int RED_LED3_PIN = 4;
const int RED_LED4_PIN = 16;
const int RED_LED5_PIN = 17;

// Green LED pins
const int GREEN_LED1_PIN = 5;
const int GREEN_LED2_PIN = 18;
const int GREEN_LED3_PIN = 19;
const int GREEN_LED4_PIN = 21;
const int GREEN_LED5_PIN = 22;

// Button pins
const int buttonPins[] = {12, 14, 27, 26, 25}; // Button 1 to Button 5
const int numButtons = 5;

// Wi-Fi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT server and credentials
const char* mqtt_server = "192.168.1.21"; // Updated server address
const char* mqtt_username = "demo";       // MQTT username
const char* mqtt_password = "azerty";       // MQTT password

WiFiClient espClient;
PubSubClient client(espClient);

// Variables to store the previous state of the buttons
bool lastButtonState[numButtons] = {HIGH, HIGH, HIGH, HIGH, HIGH};

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
  
  if (String(topic) == "mqtt/request" && message == "TurnOFF") {
    systemActive = false;
    Serial.println("System Deactivated ");
  }
  if (String(topic) == "mqtt/request" && message == "status_request") {
    systemActive = true;
    client.publish("mqtt/response", "Board : ESP32 Status : Connected");               
    Serial.println("System activated by status request");
  }
  
    // Handle LED control messages
  if (String(topic) == "arduino/Led") {
    const int redLedPins[] = {RED_LED1_PIN, RED_LED2_PIN, RED_LED3_PIN, RED_LED4_PIN, RED_LED5_PIN};
    const int greenLedPins[] = {GREEN_LED1_PIN, GREEN_LED2_PIN, GREEN_LED3_PIN, GREEN_LED4_PIN, GREEN_LED5_PIN};

    // Expecting message format: "ledRED{n}_ON", "ledRED{n}_OFF", "ledGREEN{n}_ON", or "ledGREEN{n}_OFF"
    if ((message.startsWith("ledRED") || message.startsWith("ledGREEN")) &&
        (message.endsWith("_ON") || message.endsWith("_OFF"))) {

      //int ledNumber = message.charAt(6) - '1'; // '1' to '5' becomes 0 to 4
      int ledNumber = message.startsWith("ledRED") ? message.charAt(6) - '1' : message.charAt(8) - '1';

      int state = message.endsWith("_ON") ? HIGH : LOW;

      if (ledNumber >= 0 && ledNumber < 5) {
        if (message.startsWith("ledRED")) {
          digitalWrite(redLedPins[ledNumber], state);
        } else if (message.startsWith("ledGREEN")) {
          digitalWrite(greenLedPins[ledNumber], state);
        }
      }
    }
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
    client.subscribe("arduino/Led");
    client.subscribe("mqtt/request");  // Add this line to subscribe to status requests
    client.subscribe ("mqtt/response");
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
    Serial.println(" try again in 5 seconds");
    delay(5000);
  }
}

void setup() {
  // Initialize LED pins as outputs
  pinMode(RED_LED1_PIN, OUTPUT);
  pinMode(RED_LED2_PIN, OUTPUT);
  pinMode(RED_LED3_PIN, OUTPUT);
  pinMode(RED_LED4_PIN, OUTPUT);
  pinMode(RED_LED5_PIN, OUTPUT);

  // Initialize green LED pins as outputs
  pinMode(GREEN_LED1_PIN, OUTPUT);
  pinMode(GREEN_LED2_PIN, OUTPUT);
  pinMode(GREEN_LED3_PIN, OUTPUT);
  pinMode(GREEN_LED4_PIN, OUTPUT);
  pinMode(GREEN_LED5_PIN, OUTPUT);

  // Initialize button pins as inputs with pull-up resistors
  for (int i = 0; i < numButtons; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }

  // Initialize serial communication
  Serial.begin(115200);

  // Connect to Wi-Fi
  setup_wifi();

  // Configure MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  // Reconnect to MQTT only if disconnected
  if (!client.connected()) {
    reconnect();
  }
  
  client.loop();

  if (systemActive) {
    // Check the state of each button
    for (int i = 0; i < numButtons; i++) {
      bool currentButtonState = digitalRead(buttonPins[i]);

      // Check if the button state has changed
      if (currentButtonState != lastButtonState[i]) {
        // Button pressed (active low)
        if (currentButtonState == LOW) {
          String message = "leds" + String(i + 1) + " ON";
          client.publish("arduino/Led", message.c_str());
          Serial.println("Button " + String(i + 1) + " pressed: " + message);

          // Turn on the corresponding green LED
          switch (i) {
            case 0:
              digitalWrite(GREEN_LED1_PIN, HIGH);
              digitalWrite(RED_LED1_PIN, HIGH);
              break;
            case 1:
              digitalWrite(GREEN_LED2_PIN, HIGH);
              digitalWrite(RED_LED2_PIN, HIGH);
              break;
            case 2:
              digitalWrite(GREEN_LED3_PIN, HIGH);
              digitalWrite(RED_LED3_PIN, HIGH);
              break;
            case 3:
              digitalWrite(GREEN_LED4_PIN, HIGH);
              digitalWrite(RED_LED4_PIN, HIGH);
              break;
            case 4:
              digitalWrite(GREEN_LED5_PIN, HIGH);
              digitalWrite(RED_LED5_PIN, HIGH);

              break;
          }
        }
        // Button released
        else {
          String message = "leds" + String(i + 1) + " OFF";
          client.publish("arduino/Led", message.c_str());
          Serial.println("Button " + String(i + 1) + " released: " + message);

          // Turn off the corresponding green LED
          switch (i) {
            case 0:
              digitalWrite(GREEN_LED1_PIN, LOW);
              digitalWrite(RED_LED1_PIN, LOW);
              break;
            case 1:
              digitalWrite(GREEN_LED2_PIN, LOW);
              digitalWrite(RED_LED2_PIN, LOW);
              break;
            case 2:
              digitalWrite(GREEN_LED3_PIN, LOW);
              digitalWrite(RED_LED3_PIN, LOW);
              break;
            case 3:
              digitalWrite(GREEN_LED4_PIN, LOW);
              digitalWrite(RED_LED4_PIN, LOW);
              break;
            case 4:
              digitalWrite(GREEN_LED5_PIN, LOW);
              digitalWrite(RED_LED5_PIN, LOW);
              break;
          }
        }

        // Update the last button state
        lastButtonState[i] = currentButtonState;

        // Debounce delay
        delay(50);
      }
    }
  }

}
