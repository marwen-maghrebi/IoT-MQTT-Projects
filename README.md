# IoT-MQTT-Projects: Complete ESP32 & Desktop Control System

[![ESP32](https://img.shields.io/badge/ESP32-Compatible-green)](https://www.espressif.com/en/products/socs/esp32)
[![Python](https://img.shields.io/badge/Python-3.7+-blue)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-GUI-green)](https://www.riverbankcomputing.com/software/pyqt/)
[![MQTT](https://img.shields.io/badge/MQTT-Protocol-red)](https://mqtt.org/)
[![Wokwi](https://img.shields.io/badge/Wokwi-Simulation%20Ready-orange)](https://wokwi.com/)
[![PlatformIO](https://img.shields.io/badge/PlatformIO-Compatible-blue)](https://platformio.org/)

## 📋 Project Overview

A comprehensive IoT monitoring and control system featuring **6 ESP32-based sensor projects** with a **professional PyQt5 desktop dashboard**. The system enables real-time monitoring, device control, and data visualization through MQTT communication protocol.

## 🏗️ System Architecture

```
┌───────────────────────────────────────────────────────┐
│                    PyQt5 Desktop Dashboard            │
│           ┌─────────────┐  ┌─────────────┐            │
│           │   Project   │  │    MQTT     │            │
│           │  Modules    │  │   Client    │            │
│           │   (1-6)     │  │  Manager    │            │
│           └─────────────┘  └─────────────┘            │
└───────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   MQTT Broker     │
                    │   (Mosquitto)     │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────┴─────────────────────────────┐
│                    ESP32 Device Network                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐│
│  │ LED/BTN │ │ Weather │ │  Water  │ │  Load   │ │Motion ││
│  │ Control │ │ Monitor │ │  Level  │ │  Cell   │ │ & Gas ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘│
└───────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
IoT-MQTT-Projects/
├── ESP32_Firmware/                    # Firmware for 6 ESP32 devices
│   ├── Project1_LED_Button/           # LED/Button system
│   │   ├── src/
│   │   │   └── main.cpp              # LED control firmware
│   │   ├── diagram.json              # Wokwi circuit diagram
│   │   └── platformio.ini            # PlatformIO configuration
│   ├── Project2_Temp_Humidity/       # DHT22 sensor
│   │   ├── src/
│   │   │   └── main.cpp              # Weather monitoring firmware
│   │   ├── diagram.json              # Wokwi circuit diagram
│   │   └── platformio.ini            # PlatformIO configuration
│   ├── Project3_Water_Level/         # Ultrasonic control
│   │   ├── src/
│   │   │   └── main.cpp              # Water level firmware
│   │   ├── diagram.json              # Wokwi circuit diagram
│   │   └── platformio.ini            # PlatformIO configuration
│   ├── Project4_Load_Cell/           # HX711 weight system
│   │   ├── src/
│   │   │   └── main.cpp              # Load cell firmware
│   │   ├── diagram.json              # Wokwi circuit diagram
│   │   └── platformio.ini            # PlatformIO configuration
│   ├── Project5_Accelerometer/       # MPU6050 motion tracker
│   │   ├── src/
│   │   │   └── main.cpp              # Motion sensing firmware
│   │   ├── diagram.json              # Wokwi circuit diagram
│   │   └── platformio.ini            # PlatformIO configuration
│   └── Project6_Gas_Sensor/          # MQ2 safety system
│       ├── src/
│       │   └── main.cpp              # Gas detection firmware
│       ├── diagram.json              # Wokwi circuit diagram
│       └── platformio.ini            # PlatformIO configuration
│
├── Qt_GUI_Application/                   # Python Control Center
│   ├── main.py                       # Application entry point
│   ├── mainwindow.py                 # UI definition (Qt Designer)
│   ├── Mqtt.py                       # MQTT client wrapper
│   ├── data.py                       # Configuration constants
│   ├──custom_switch/                    # Custom_switch Library
│   │  ├── __init__.py                # Custom switch init
│   │  └── custom_switch.py           # Custom switch widget
│   ├── project1.py                   # LED control module
│   ├── project2.py                   # Weather monitoring module
│   ├── project3.py                   # Water level module
│   ├── project4.py                   # Load cell module
│   ├── project5.py                   # Motion monitoring module
│   └── project6.py                   # Gas detection module
│
├── README.md                         # This file
└── LICENSE                          # MIT License
```

## 🎯 ESP32 Project Modules

### 1. **LED Control & Button Interface System**
**Hardware:** ESP32 + 10 LEDs + 5 Push Buttons  
**Purpose:** Interactive LED control with manual and remote operation

**Features:**
- 5 Red LEDs with button control
- 5 Green LEDs with remote MQTT control
- Real-time button state publishing
- System activation/deactivation control
- Board status reporting

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Control: `arduino/Led`


### 2. **Weather Monitoring & Alert System**
**Hardware:** ESP32 + DHT22 + Buzzer  
**Purpose:** Environmental monitoring with threshold-based alerting

**Features:**
- Temperature and humidity sensing (±0.5°C, ±2-5% RH)
- Configurable alert thresholds via JSON
- Audio alerts when thresholds exceeded
- Real-time weather data publishing
- Heat index and dew point calculations

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Weather Data: `arduino/Weather`
- Alerts: `arduino/weather_alerts`
- threshold: `arduino/Weather_threshold`

### 3. **Water Level Monitoring & Control System**
**Hardware:** ESP32 + HC-SR04 + 2 Relays  
**Purpose:** Automated water tank management

**Features:**
- Ultrasonic distance measurement (2-400cm range)
- Water level percentage calculation (0-100%)
- Dual relay control for fill/drain valves
- Remote valve control via MQTT
- Tank geometry compensation

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Level Data: `arduino/sensor`
- Valve Control: `arduino/sensor_Control`

### 4. **Load Cell Weight Measurement System**
**Hardware:** ESP32 + HX711 + Load Cell  
**Purpose:** Precision weight measurement

**Features:**
- 24-bit ADC for high-resolution measurements
- Load cell calibration support
- Real-time weight data in kilograms
- Data smoothing with multiple readings
- Tare functionality

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Weight Data: `arduino/LoadCell`

### 5. **Motion & Orientation Monitoring System**
**Hardware:** ESP32 + MPU6050  
**Purpose:** 6-axis motion sensing and analysis

**Features:**
- 3-axis accelerometer (±2/±4/±8/±16g)
- 3-axis gyroscope (±250/±500/±1000/±2000°/s)
- Temperature measurement
- JSON data format for easy parsing
- Configurable sensor ranges

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Motion Data: `arduino/MPU6050`

### 6. **Gas Detection & Safety Alert System**
**Hardware:** ESP32 + MQ2 + 3 LEDs + Buzzer  
**Purpose:** Industrial gas monitoring with safety protocols

**Features:**
- Multi-gas detection (LPG, propane, methane, alcohol, hydrogen, smoke)
- Three-tier safety system with color-coded LEDs
- Audio alarm for dangerous gas levels
- Real-time PPM concentration measurement
- Voltage output monitoring

**Safety Thresholds:**
- **Safe (Green LED):** < 600 PPM
- **Caution (Yellow LED):** 600-900 PPM
- **Danger (Red LED + Buzzer):** > 900 PPM

**MQTT Topics:**
- Status: `mqtt/response`
- Requests: `mqtt/request`
- Gas Data: `arduino/gas`

## 🖥️ PyQt5 Desktop Dashboard

### Core Features
- **Modern UI:** Frameless window with custom title bar and drag functionality
- **Real-time Monitoring:** Live sensor data with thread-safe updates
- **Interactive Controls:** Custom switches, buttons, and LED indicators
- **Virtual Keyboard:** Touch-friendly on-screen keyboard with multi-mode support
- **Project Management:** Clean switching between 6 project modules
- **MQTT Integration:** Robust connection management with automatic reconnection

### Project Control Modules

#### Module 1: LED & Button Control Interface
**Class:** `LED_and_Button`
- Control 10 LEDs (5 red via buttons, 5 green via switches)
- Real-time board status monitoring
- Custom toggle switches with smooth animations
- Thread-safe UI updates using PyQt5 signals/slots

#### Module 2: Environmental Monitoring Dashboard
**Class:** `Tem_hum_Sensor`
- Dual temperature display (Celsius/Fahrenheit)
- Humidity monitoring with percentage display
- Configurable threshold management
- Time-stamped action and alert logging

#### Module 3: Water Level Management
**Class:** `WaterLevelControllerWindow`
- Tank level visualization (0-100%)
- Dual valve control interface
- Level history tracking
- Safety interlock management

#### Module 4: Precision Weight Monitoring
**Class:** `LOADCELL`
- High-precision weight display
- Calibration wizard interface
- Real-time data smoothing
- Tare function support

#### Module 5: Motion Analytics
**Class:** `AccelerometerGyroscopeController`
- 6-axis motion data visualization
- Real-time acceleration and gyroscope readings
- Temperature monitoring
- Motion pattern analysis

#### Module 6: Gas Safety Monitor
**Class:** `GasSensorController`
- Multi-gas concentration display
- Three-tier safety alert system
- PPM measurement with color-coded indicators
- Emergency response protocols

## 🚀 Quick Start Guide

### Prerequisites

#### For ESP32 Development:
- **PlatformIO IDE** or **Arduino IDE** with ESP32 support
- **Wokwi Account** (for simulation)
- ESP32 development boards (6 units for physical implementation)
- Electronic components (sensors, LEDs, resistors, etc.)

#### For Desktop Application:
- **Python 3.7+**
- **PyQt5**
- **Paho MQTT Client**
- **MQTT Broker** (Mosquitto recommended)

### Installation Steps

#### 1. Clone Repository
```bash
git clone <repository-url>
cd IoT-MQTT-Projects
```

#### 2. Set Up MQTT Broker
📺 *You can also follow this video guide:* [Set Up Mosquitto MQTT on Windows](https://youtu.be/hyJhKWhxAxA?si=_qVtR59dgmXFbdNU)
##### 1. Download and Install Mosquitto
1. Visit [https://mosquitto.org/download/](https://mosquitto.org/download/)
2. Under the **Windows** section, download the `.exe` installer (e.g., `mosquitto-2.0.15-install-windows-x64`)
3. Run the installer and make sure to:
   - Install the **service**
   - Install **dependencies** (OpenSSL, pthreads, etc.)

##### 2. Configure Mosquitto
Open Command Prompt as Administrator and run:

```cmd
cd "C:\Program Files\mosquitto"
copy mosquitto.conf mosquitto.conf.bak
notepad mosquitto.conf
```

##### 3.At the end of the mosquitto.conf file, add:
```
listener 1883 0.0.0.0 
allow_anonymous false
password_file C:\Program Files\mosquitto\passwd
```

#### 3. ESP32 Firmware Setup

**For Wokwi Simulation:**
1. Open [Wokwi.com](https://wokwi.com)
2. Import project `diagram.json` files from each ESP32 project folder
3. Load corresponding firmware code
4. Configure WiFi and MQTT settings
5. Start simulation

**For Physical Hardware:**
```bash
# Install PlatformIO
pip install platformio

# Navigate to project folder
cd ESP32_Firmware/Project1_LED_Button

# Build and upload
pio run --target upload

```

#### 4. Desktop Application Setup
```bash
# Navigate to dashboard folder
cd Qt_GUI_Application

# Install dependencies
pip install PyQt5>=5.15.0
pip install paho-mqtt>=1.6.0
pip install pyqtgraph

# Run application
python main.py
```

#### 5. Network Configuration
Update network settings in ESP32 firmware:
```cpp
const char* ssid = "your_wifi_network";
const char* password = "your_wifi_password";
const char* mqtt_server = "192.168.1.21";  // Your MQTT broker IP
const char* mqtt_username = "demo";
const char* mqtt_password = "azert";
```

## 🔍 Troubleshooting

### Common ESP32 Issues

#### 1. MQTT Connection Issues
```cpp
// MQTT diagnostics
Serial.println("MQTT State: " + String(mqtt.state()));
Serial.println("Broker IP: " + String(mqtt_server));
```
**Solutions:**
- Verify broker IP and port
- Check authentication credentials
- Test with MQTT client tools

#### 2. Sensor Reading Anomalies
- **DHT22:** Allow 2-second intervals between readings
- **HC-SR04:** Ensure 5V power supply
- **HX711:** Shield from electromagnetic interference
- **MPU6050:** Perform calibration on startup
- **MQ2:** Allow 24-48 hour burn-in period

### Common Desktop Application Issues

#### 1. PyQt5 Import Errors
```bash
# Install PyQt5 properly
pip uninstall PyQt5
pip install PyQt5>=5.15.11
```
#### 2. MQTT Connection Failed
- Verify broker IP in application settings
- Check firewall settings
- Test broker with mosquitto_pub/sub tools


📘 Refer to the official [Mosquitto documentation](https://mosquitto.org/documentation/) for advanced configuration.
