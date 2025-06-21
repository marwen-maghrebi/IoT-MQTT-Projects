# ========================
#         Imports
# ========================
from data import MQTT_TOPIC_GAS, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from datetime import datetime
import json
import pyqtgraph as pg


class GasSensorController(QObject):
    """Thread-safe gas sensor controller that works with PyQt5"""
    # ============================================================================
    # SIGNALS
    # ============================================================================
    gas_data_changed = pyqtSignal(float, float)          # gas_ppm, voltage
    led_status_changed = pyqtSignal(float)               # gas_ppm for LED control
    board_status_changed = pyqtSignal(str, str, str)     # board_name, status, color
    board_led_status_changed = pyqtSignal(str)           # color for board status LED
    plot_update_signal = pyqtSignal(float, float)        # gas_ppm, voltage
    error_state_signal = pyqtSignal()

    # ============================================================================
    # INITIALIZATION
    # ============================================================================
    def __init__(self, mqtt_client, ui):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.ui = ui
        self.status_received = False
        
        # Data buffers for plotting
        self.gas_data = []
        self.voltage_data = []
        self.time_data = []
        self.max_data_points = 100
        
        # Gas concentration thresholds
        self.danger_threshold = 900
        self.warning_threshold = 500
        
        # Initialize all components
        self.connect_signals()
        self.setup_mqtt()
        self.init_ui()
        self.setup_ui_connections()
    
    # ============================================================================
    # CORE METHODS
    # ============================================================================
    def connect_signals(self):
        """Connect all signals to their slots"""
        self.gas_data_changed.connect(self.update_gas_data_ui)
        self.led_status_changed.connect(self.update_gas_leds_ui)
        self.board_status_changed.connect(self.update_board_status_ui)
        self.board_led_status_changed.connect(self.update_board_led_ui)
        self.plot_update_signal.connect(self.update_plots_ui)
        self.error_state_signal.connect(self.show_error_state_ui)

    def setup_mqtt(self):
        """Initialize MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_GAS, self.handle_gas_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_response_message)

    def init_ui(self):
        """Initialize all UI components"""
        self.init_sensor_display()
        self.init_status_display()
        self.init_plots()
        self.init_led_indicators()
    def init_sensor_display(self):
        """Initialize sensor display with default values"""
        if hasattr(self.ui, 'lcdNumberGas'):
            self.ui.lcdNumberGas.display("--")
        if hasattr(self.ui, 'lcdNumberVolt'):
            self.ui.lcdNumberVolt.display("--")

    def init_status_display(self):
        """Initialize board status display"""
        if hasattr(self.ui, 'lab_board_GS'):
            self.ui.lab_board_GS.setText("Unknown")
        if hasattr(self.ui, 'lab_mqtt_broker_GS'):
            self.ui.lab_mqtt_broker_GS.setText(self.ui.host_lineEdit.text())
    
    def init_led_indicators(self):
        """Initialize LED indicators to default state"""
        self.apply_gas_led_styles("safe")

    def init_plots(self):
        """Initialize the gas and voltage plots"""
        # Set up gas plot
        if hasattr(self.ui, 'gas_plot_widget'):
            self.gas_plot = self.ui.gas_plot_widget
            self.gas_plot.setBackground(QColor(0, 0, 0, 100))
            self.gas_plot.setTitle("Gas Concentration (ppm)", color='w', size='14pt', bold=True)
            self.gas_plot.setLabel('left', 'Concentration (ppm)')
            self.gas_plot.setLabel('bottom', 'Time')
            self.gas_plot.addLegend()
            self.gas_plot.showGrid(x=True, y=True)

            # Create gas plot curve
            self.gas_curve = self.gas_plot.plot(pen='r', name="Gas PPM")

        # Set up voltage plot
        if hasattr(self.ui, 'volt_plot_widget'):
            self.voltage_plot = self.ui.volt_plot_widget
            self.voltage_plot.setBackground(QColor(0, 0, 0, 100))
            self.voltage_plot.setTitle("Sensor Voltage (V)", color='w', size='14pt', bold=True)
            self.voltage_plot.setLabel('left', 'Voltage (V)')
            self.voltage_plot.setLabel('bottom', 'Time')
            self.voltage_plot.addLegend()
            self.voltage_plot.showGrid(x=True, y=True)

            # Create voltage plot curve
            self.voltage_curve = self.voltage_plot.plot(pen='b', name="Voltage")

    def setup_ui_connections(self):
        """Connect UI buttons to their handlers"""
        if hasattr(self.ui, 'refrech_btn_GS'):
            self.ui.refrech_btn_GS.clicked.connect(self.request_board_status)

    # ============================================================================
    # UI UPDATE METHODS (SLOTS)
    # ============================================================================
    @pyqtSlot(float, float)
    def update_gas_data_ui(self, gas_ppm, voltage):
        """Thread-safe gas sensor data update"""
        if hasattr(self.ui, 'lcdNumberGas'):
            self.ui.lcdNumberGas.display(f"{gas_ppm:.0f}")
        if hasattr(self.ui, 'lcdNumberVolt'):
            self.ui.lcdNumberVolt.display(f"{voltage:.2f}")

    @pyqtSlot(float)
    def update_gas_leds_ui(self, gas_ppm):
        """Thread-safe LED status update based on gas concentration"""
        if gas_ppm > self.danger_threshold:
            self.apply_gas_led_styles("danger")
        elif gas_ppm > self.warning_threshold:
            self.apply_gas_led_styles("warning")
        else:
            self.apply_gas_led_styles("safe")

    @pyqtSlot(str, str, str)
    def update_board_status_ui(self, board_name, status, color):
        """Thread-safe board status update"""
        if hasattr(self.ui, 'lab_board_GS'):
            self.ui.lab_board_GS.setText(board_name)
        if hasattr(self.ui, 'lab_board_status_GS'):
            self.ui.lab_board_status_GS.setText(status)
        self.apply_board_status_style(color)

    @pyqtSlot(str)
    def update_board_led_ui(self, color):
        """Thread-safe board LED status update"""
        self.apply_board_led_style(color)

    @pyqtSlot(float, float)
    def update_plots_ui(self, gas_ppm, voltage):
        """Thread-safe plot update"""
        # Append new data
        self.gas_data.append(gas_ppm)
        self.voltage_data.append(voltage)
        self.time_data.append(len(self.time_data))

        # Trim data buffers if needed
        if len(self.time_data) > self.max_data_points:
            self.gas_data.pop(0)
            self.voltage_data.pop(0)
            self.time_data.pop(0)

        # Update plots if they exist
        if hasattr(self, 'gas_curve'):
            self.gas_curve.setData(self.time_data, self.gas_data)
        
        if hasattr(self, 'voltage_curve'):
            self.voltage_curve.setData(self.time_data, self.voltage_data)

    @pyqtSlot()
    def show_error_state_ui(self):
        """Thread-safe error state display"""
        error_text = "ERR"
        if hasattr(self.ui, 'lcdNumberGas'):
            self.ui.lcdNumberGas.display(error_text)
        if hasattr(self.ui, 'lcdNumberVolt'):
            self.ui.lcdNumberVolt.display(error_text)

    # ============================================================================
    # STYLE MANAGEMENT
    # ============================================================================
    def apply_gas_led_styles(self, status):
        """Apply styling to gas concentration LED indicators"""
        # Define LED styles
        led_styles = {
            "active_red": """
                QLabel {
                    background-color: qradialgradient(cx:0.5, cy:0.5, radius: 0.6,
                        fx:0.5, fy:0.5, stop:0 #FF0000, stop:1 #8B0000);
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """,
            "active_yellow": """
                QLabel {
                    background-color: qradialgradient(cx:0.5, cy:0.5, radius: 0.6,
                        fx:0.5, fy:0.5, stop:0 #FFFF00, stop:1 #CCCC00);
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """,
            "active_green": """
                QLabel {
                    background-color: qradialgradient(cx:0.5, cy:0.5, radius: 0.6,
                        fx:0.5, fy:0.5, stop:0 #00FF00, stop:1 #008800);
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """,
            "inactive_red": """
                QLabel {
                    background-color: #330000;
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """,
            "inactive_yellow": """
                QLabel {
                    background-color: #333300;
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """,
            "inactive_green": """
                QLabel {
                    background-color: #003300;
                    border: 2px solid gray;
                    border-radius: 25px;
                    min-width: 50px;
                    min-height: 50px;
                }
            """
        }

        # Apply styles based on status
        if status == "danger":
            if hasattr(self.ui, 'led_red'):
                self.ui.led_red.setStyleSheet(led_styles["active_red"])
            if hasattr(self.ui, 'led_yellow'):
                self.ui.led_yellow.setStyleSheet(led_styles["inactive_yellow"])
            if hasattr(self.ui, 'led_green'):
                self.ui.led_green.setStyleSheet(led_styles["inactive_green"])
        elif status == "warning":
            if hasattr(self.ui, 'led_red'):
                self.ui.led_red.setStyleSheet(led_styles["inactive_red"])
            if hasattr(self.ui, 'led_yellow'):
                self.ui.led_yellow.setStyleSheet(led_styles["active_yellow"])
            if hasattr(self.ui, 'led_green'):
                self.ui.led_green.setStyleSheet(led_styles["inactive_green"])
        else:  # safe
            if hasattr(self.ui, 'led_red'):
                self.ui.led_red.setStyleSheet(led_styles["inactive_red"])
            if hasattr(self.ui, 'led_yellow'):
                self.ui.led_yellow.setStyleSheet(led_styles["inactive_yellow"])
            if hasattr(self.ui, 'led_green'):
                self.ui.led_green.setStyleSheet(led_styles["active_green"])

    def apply_board_status_style(self, color):
        """Apply styling to board status display"""
        if not hasattr(self.ui, 'lab_board_status_GS'):
            return
            
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
        self.ui.lab_board_status_GS.setStyleSheet(style)

    def apply_board_led_style(self, color):
        """Apply styling to board status LED indicator"""
        if not hasattr(self.ui, 'led_boardST_6'):
            return
            
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
        self.ui.led_boardST_6.setStyleSheet(style)

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_gas_message(self, topic, payload):
        """Handle incoming gas sensor data"""
        print(f"[GAS SENSOR] Received data - Topic: {topic}, Payload: {payload}")
        
        if topic == MQTT_TOPIC_GAS:
            try:
                # Parse and validate JSON payload
                sensor_data = json.loads(payload)
                print(f"[GAS SENSOR] Parsed data: {sensor_data}")
                
                # Extract data with fallback values
                gas_ppm = sensor_data.get("gas_ppm", 0)
                voltage = sensor_data.get("voltage", 0)

                # Update UI through signals
                self.gas_data_changed.emit(gas_ppm, voltage)
                self.led_status_changed.emit(gas_ppm)
                
                # Update plots
                self.plot_update_signal.emit(gas_ppm, voltage)

            except json.JSONDecodeError as e:
                print(f"[GAS SENSOR] JSON decode error: {e}")
                self.error_state_signal.emit()
            except Exception as e:
                print(f"[GAS SENSOR] Processing error: {e}")
                self.error_state_signal.emit()
        else:
            print(f"[GAS SENSOR] Unexpected topic: {topic}")

    def handle_status_response_message(self, topic, payload):
        """Process board status messages from response topic"""
        try:
            print(f"[STATUS] Received message on {topic}: {payload}")
            
            if payload.strip() == "status_request":
                print("[STATUS] Ignoring our own status_request message")
                return
                
            if "Board :" in payload and "Status :" in payload:
                board_part, status_part = payload.split("Status :")
                board_name = board_part.replace("Board :", "").strip()
                status = status_part.strip().lower()
                
                if status == "connected":
                    self.board_status_changed.emit(board_name, "Connected", "green")
                    self.board_led_status_changed.emit("green")
                    self.status_received = True
                else:
                    self.board_status_changed.emit(board_name, status.capitalize(), "red")
                    self.board_led_status_changed.emit("red")
                    
        except Exception as e:
            print(f"[STATUS] Error processing message: {e}")

    # ============================================================================
    # BOARD STATUS MANAGEMENT
    # ============================================================================
    def request_board_status(self):
        """Send status request to request topic with timeout fallback"""
        self.status_received = False
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "status_request")
        print(f"[STATUS] Sent status request to {MQTT_TOPIC_MQTT_Rq}")
        
        QTimer.singleShot(3000, self.check_status_response)

    def check_status_response(self):
        """Check if we received a valid response"""
        if not self.status_received:
            print("[STATUS] No response received within timeout period")
            self.board_status_changed.emit("Unknown", "Disconnected", "red")
            self.board_led_status_changed.emit("red")

    # ============================================================================
    # CLEANUP
    # ============================================================================
    def deactivate(self):
        """Cleanly deactivate the project and clear all curve data"""
        print("deactivate Gas Sensor")

        try:
            # Send shutdown command
            self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

            # Unsubscribe from topics
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_GAS)
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)

            # Reset UI displays
            self.init_sensor_display()
            self.apply_gas_led_styles("safe")  # Reset LEDs to safe state
            self.board_status_changed.emit("Unknown", "Disconnected", "red")
            self.board_led_status_changed.emit("red")

            # Clear ALL plot data buffers
            self.gas_data.clear()
            self.voltage_data.clear()
            self.time_data.clear()

            # Completely clear and reinitialize gas plot
            if hasattr(self, 'gas_plot') and hasattr(self.ui, 'gas_plot_widget'):
                # Clear all items from the plot
                self.gas_plot.clear()
                
                # Remove existing curve reference
                if hasattr(self, 'gas_curve'):
                    delattr(self, 'gas_curve')
                
                # Reinitialize the gas plot completely
                self.gas_plot.setBackground(QColor(0, 0, 0, 100))
                self.gas_plot.setTitle("Gas Concentration (ppm)", color='w', size='14pt', bold=True)
                self.gas_plot.setLabel('left', 'Concentration (ppm)')
                self.gas_plot.setLabel('bottom', 'Time')
                self.gas_plot.addLegend()
                self.gas_plot.showGrid(x=True, y=True)
                
                # Create new empty curve
                self.gas_curve = self.gas_plot.plot(pen='r', name="Gas PPM")
                # Ensure curve is empty
                self.gas_curve.setData([], [])

            # Completely clear and reinitialize voltage plot
            if hasattr(self, 'voltage_plot') and hasattr(self.ui, 'volt_plot_widget'):
                # Clear all items from the plot
                self.voltage_plot.clear()
                
                # Remove existing curve reference
                if hasattr(self, 'voltage_curve'):
                    delattr(self, 'voltage_curve')
                
                # Reinitialize the voltage plot completely
                self.voltage_plot.setBackground(QColor(0, 0, 0, 100))
                self.voltage_plot.setTitle("Sensor Voltage (V)", color='w', size='14pt', bold=True)
                self.voltage_plot.setLabel('left', 'Voltage (V)')
                self.voltage_plot.setLabel('bottom', 'Time')
                self.voltage_plot.addLegend()
                self.voltage_plot.showGrid(x=True, y=True)
                
                # Create new empty curve
                self.voltage_curve = self.voltage_plot.plot(pen='b', name="Voltage")
                # Ensure curve is empty
                self.voltage_curve.setData([], [])

            # Reset status flag
            self.status_received = False

            print("[GAS SENSOR] Project completely deactivated. All curve data cleared and plots reset.")

        except Exception as e:
            print(f"[GAS SENSOR] Error during deactivation: {e}")
