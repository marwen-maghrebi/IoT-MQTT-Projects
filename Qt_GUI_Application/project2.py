# ========================
#         Imports
# ========================
from data import MQTT_TOPIC_WATHER,MQTT_TOPIC_WATHER_THRESHOLD , MQTT_TOPIC_WATHER_ALERTS, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot
from datetime import datetime
import json


class Tem_hum_Sensor(QObject):
    # ============================================================================
    # SIGNALS DEFINITION
    # ============================================================================
    update_tempC = pyqtSignal(str)
    update_tempF = pyqtSignal(str)
    update_hum = pyqtSignal(str)
    update_board_status = pyqtSignal(str, str, str)  # board_name, status, color
    update_led_status = pyqtSignal(str)              # color
    log_action = pyqtSignal(str)
    log_alert = pyqtSignal(str)
    update_threshold_values = pyqtSignal(float, float)  # temp, hum
    status_message = pyqtSignal(str)                   # Separate signal for status messages

    # ============================================================================
    # INITIALIZATION METHODS
    # ============================================================================
    def __init__(self, mqtt_client, ui):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.ui = ui
        self.status_received = False
        
        # Initialize all components
        self._connect_signals()
        self._setup_mqtt()
        self._init_sensor_display()
        self._init_status_display()
        self._init_thresholds()
        self._setup_ui_connections()

    def _connect_signals(self):
        """Connect all signals to their slots"""
        self.update_tempC.connect(self._update_tempC)
        self.update_tempF.connect(self._update_tempF)
        self.update_hum.connect(self._update_hum)
        self.update_board_status.connect(self._update_board_status)
        self.update_led_status.connect(self._update_led_status)
        self.log_action.connect(self._log_action)
        self.log_alert.connect(self._log_alert)
        self.update_threshold_values.connect(self._update_threshold_values)
        self.status_message.connect(self._status_message)

    def _setup_mqtt(self):
        """Initialize MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_message2)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_WATHER, self.handle_weather_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_WATHER_ALERTS, self.handle_alert_message)

    def _init_sensor_display(self):
        """Initialize sensor display with default values"""
        self.update_tempC.emit("--")
        self.update_tempF.emit("--")
        self.update_hum.emit("--")

    def _init_status_display(self):
        """Initialize board status display"""
        self.ui.lab_board_SW.setText("Unknown")
        self.ui.lab_mqtt_broker_SW.setText(self.ui.host_lineEdit.text())

    def _init_thresholds(self):
        """Initialize threshold values and UI"""
        self.threshold_temp = self.ui.temp_spinbox.value()
        self.threshold_hum = self.ui.humidity_spinbox.value()

    def _setup_ui_connections(self):
        """Connect UI buttons to their handlers"""
        self.ui.refrech_btn_SW.clicked.connect(self.request_board_status)
        self.ui.apply_btn.clicked.connect(self.update_thresholds)

    # ============================================================================
    # UI UPDATE METHODS (SLOTS)
    # ============================================================================
    @pyqtSlot(str)
    def _update_tempC(self, value):
        """Thread-safe temperature update (Celsius)"""
        self.ui.tempC_val_label.setText(f"{value} °C")

    @pyqtSlot(str)
    def _update_tempF(self, value):
        """Thread-safe temperature update (Fahrenheit)"""
        self.ui.tempF_val_label.setText(f"{value} °F")

    @pyqtSlot(str)
    def _update_hum(self, value):
        """Thread-safe humidity update"""
        self.ui.hum_val_label.setText(f"{value} %")

    @pyqtSlot(str, str, str)
    def _update_board_status(self, board_name, status, color):
        """Thread-safe board status update"""
        self.ui.lab_board_SW.setText(board_name)
        self.ui.lab_board_status_SW.setText(status)
        self._apply_board_status_style(color)

    @pyqtSlot(str)
    def _update_led_status(self, color):
        """Thread-safe LED status update"""
        self._apply_led_style(color)

    @pyqtSlot(str)
    def _log_action(self, message):
        """Thread-safe action logging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.action_log.append(f"[{timestamp}] {message}")

    @pyqtSlot(str)
    def _log_alert(self, message):
        """Thread-safe alert logging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.alert_log.append(f'<span style="color:white;">[{timestamp}] {message}</span>')
    
    @pyqtSlot(str)
    def _status_message(self, message):
        """Separate handler for status messages (not logged to action log)"""
        print(message)

    @pyqtSlot(float, float)
    def _update_threshold_values(self, temp, hum):
        """Thread-safe threshold value update"""
        self.threshold_temp = temp
        self.threshold_hum = hum

    # ============================================================================
    # STYLE MANAGEMENT
    # ============================================================================
    def _apply_board_status_style(self, color):
        """Apply styling to board status display"""
        style = ""
        if color == "green":
            style = """
                color: rgb(0, 255, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """
        elif color == "red":
            style = """
                color: rgb(255, 0, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """
        self.ui.lab_board_status_SW.setStyleSheet(style)

    def _apply_led_style(self, color):
        """Apply styling to LED indicator"""
        style = ""
        if color == "green":
            style = """
                background-color: rgb(0, 255, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(0, 102, 0);
            """
        elif color == "red":
            style = """
                background-color: rgb(255, 0, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(128, 0, 0);
            """
        self.ui.led_boardST_2.setStyleSheet(style)

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_weather_message(self, topic, payload):
        """Handle incoming weather sensor data"""
        self.status_message.emit(f"[WEATHER] Received data - Topic: {topic}, Payload: {payload}")

        if topic == MQTT_TOPIC_WATHER:
            try:
                if "Temperature:" in payload and "Humidity:" in payload:
                    # Extract Celsius temperature
                    tempC_part = payload.split("Temperature: ")[1].split(",")[0]
                    tempC = tempC_part.replace("°C", "").strip()
                    self.update_tempC.emit(tempC)

                    # Extract Fahrenheit temperature
                    tempF_part = payload.split("Temperature: ")[2].split(",")[0]
                    tempF = tempF_part.replace("°F", "").strip()
                    self.update_tempF.emit(tempF)

                    # Extract humidity
                    hum_part = payload.split("Humidity: ")[1].replace("%", "").strip()
                    self.update_hum.emit(hum_part)
                else:
                    self.status_message.emit("[WEATHER] Invalid payload format - missing Temperature or Humidity")
            except Exception as e:
                self.status_message.emit(f"[WEATHER] Error processing message: {e}")
        else:
            self.status_message.emit(f"[WEATHER] Unexpected topic: {topic} (expected: {MQTT_TOPIC_WATHER})")

    def handle_status_message2(self, topic, payload):
        """Process board status messages from response topic"""
        try:
            self.status_message.emit(f"[STATUS] Received message on {topic}: {payload}")
            
            if payload.strip() == "status_request":
                self.status_message.emit("[STATUS] Ignoring our own status_request message")
                return
                
            if "Board :" in payload and "Status :" in payload:
                board_part, status_part = payload.split("Status :")
                board_name = board_part.replace("Board :", "").strip()
                status = status_part.strip().lower()
                
                if status == "connected":
                    self.update_board_status.emit(board_name, "Connected", "green")
                    self.update_led_status.emit("green")
                    self.status_received = True
                else:
                    self.update_board_status.emit(board_name, status.capitalize(), "red")
                    self.update_led_status.emit("red")
                    
        except Exception as e:
            self.status_message.emit(f"[STATUS] Error processing message: {e}")

    def handle_alert_message(self, topic, payload):
        """Handle alert messages"""
        self.log_alert.emit(payload)

    # ============================================================================
    # BOARD STATUS MANAGEMENT
    # ============================================================================
    def request_board_status(self):
        """Send status request to request topic with timeout fallback"""
        self.status_received = False
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "status_request")
        self.status_message.emit(f"[STATUS] Sent status request to {MQTT_TOPIC_MQTT_Rq}")
        
        QTimer.singleShot(2000, self.check_status_response)

    def check_status_response(self):
        """Check if we received a valid response"""
        if not self.status_received:
            self.status_message.emit("[STATUS] No response received within timeout period")
            self.update_board_status.emit("Unknown", "Disconnected", "red")
            self.update_led_status.emit("red")

    # ============================================================================
    # THRESHOLD MANAGEMENT
    # ============================================================================
    def update_thresholds(self):
        """Send thresholds as JSON to single topic"""
        temp_val = self.ui.temp_spinbox.value()
        hum_val = self.ui.humidity_spinbox.value()
        
        # Update threshold values through signal
        self.update_threshold_values.emit(temp_val, hum_val)
        
        thresholds = {
            "temp": temp_val,
            "hum": hum_val
        }
        self.log_action.emit(f"Thresholds sent: {thresholds}")
        payload = json.dumps(thresholds)
        self.mqtt_client.publish(MQTT_TOPIC_WATHER_THRESHOLD, payload)
    
    # ============================================================================
    # CLEANUP
    # ============================================================================
    def deactivate(self):
        """Cleanly deactivate the sensor project and unsubscribe from MQTT topics."""
        print("deactivate P2")
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

        try:
            # Unsubscribe from all relevant MQTT topics
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_WATHER)
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_WATHER_ALERTS)
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)

            # Optional: disconnect UI button signals if needed
            self.ui.refrech_btn_SW.clicked.disconnect()
            self.ui.apply_btn.clicked.disconnect()

            # Clear logs
            self.ui.action_log.clear()
            self.ui.alert_log.clear()

            # Optional: reset display
            self.update_tempC.emit("--")
            self.update_tempF.emit("--")
            self.update_hum.emit("--")
            self.update_board_status.emit("Unknown", "Disconnected", "red")
            self.update_led_status.emit("red")

            print("[SENSOR] Project deactivated successfully.")

        except Exception as e:
            print(f"[SENSOR] Error during deactivation: {e}")

