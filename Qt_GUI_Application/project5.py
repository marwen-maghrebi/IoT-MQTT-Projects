# ========================
#         Imports
# ========================
from data import MQTT_TOPIC_MPU6050, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from datetime import datetime
import json
import pyqtgraph as pg


class AccelerometerGyroscopeController(QObject):
    """Thread-safe accelerometer and gyroscope sensor controller that works with PyQt5"""
    # ============================================================================
    # SIGNALS
    # ============================================================================
    accelerometer_data_changed = pyqtSignal(float, float, float)  # x, y, z
    gyroscope_data_changed = pyqtSignal(float, float, float)      # x, y, z
    temperature_changed = pyqtSignal(str)
    board_status_changed = pyqtSignal(str, str, str)              # board_name, status, color
    led_status_changed = pyqtSignal(str)                          # color
    plot_update_signal = pyqtSignal(float, float, float, float, float, float)  # accelX, Y, Z, gyroX, Y, Z
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
        self.accel_data = {'x': [], 'y': [], 'z': []}
        self.gyro_data = {'x': [], 'y': [], 'z': []}
        self.time_data = []
        self.max_data_points = 100
        
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
        self.accelerometer_data_changed.connect(self.update_accelerometer_ui)
        self.gyroscope_data_changed.connect(self.update_gyroscope_ui)
        self.temperature_changed.connect(self.update_temperature_ui)
        self.board_status_changed.connect(self.update_board_status_ui)
        self.led_status_changed.connect(self.update_led_status_ui)
        self.plot_update_signal.connect(self.update_plots_ui)
        self.error_state_signal.connect(self.show_error_state_ui)

    def setup_mqtt(self):
        """Initialize MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MPU6050, self.handle_mpu6050_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_response_message)

    def init_ui(self):
        """Initialize all UI components"""
        self.init_sensor_display()
        self.init_status_display()
        self.init_plots()

    def init_sensor_display(self):
        """Initialize sensor display with default values"""
        if hasattr(self.ui, 'Accelx_lineEdit'):
            self.ui.Accelx_lineEdit.setText("-- g")
        if hasattr(self.ui, 'Accely_lineEdit'):
            self.ui.Accely_lineEdit.setText("-- g")
        if hasattr(self.ui, 'Accelz_lineEdit'):
            self.ui.Accelz_lineEdit.setText("-- g")
        if hasattr(self.ui, 'Gyrox_lineEdit'):
            self.ui.Gyrox_lineEdit.setText("-- °/sec")
        if hasattr(self.ui, 'Gyroy_lineEdit'):
            self.ui.Gyroy_lineEdit.setText("-- °/sec")
        if hasattr(self.ui, 'Gyroz_lineEdit'):
            self.ui.Gyroz_lineEdit.setText("-- °/sec")
        if hasattr(self.ui, 'temp_lineEdit'):
            self.ui.temp_lineEdit.setText("-- °C")

    def init_status_display(self):
        """Initialize board status display"""
        if hasattr(self.ui, 'lab_board_MS'):
            self.ui.lab_board_MS.setText("Unknown")
        if hasattr(self.ui, 'lab_mqtt_broker_MS'):
            self.ui.lab_mqtt_broker_MS.setText(self.ui.host_lineEdit.text())

    def init_plots(self):
        """Initialize the accelerometer and gyroscope plots"""
        # Set up accelerometer plot
        if hasattr(self.ui, 'accel_plot_widget'):
            self.accel_plot = self.ui.accel_plot_widget
            self.accel_plot.setBackground(QColor(0, 0, 0, 100))
            self.accel_plot.setTitle("Accelerometer Data (g)", color='w', size='14pt', bold=True)
            self.accel_plot.setLabel('left', 'Acceleration (g)')
            self.accel_plot.setLabel('bottom', 'Time')
            self.accel_plot.addLegend()
            self.accel_plot.showGrid(x=True, y=True)

            # Create accelerometer plot curves
            self.accel_x_curve = self.accel_plot.plot(pen='r', name="AccelX")
            self.accel_y_curve = self.accel_plot.plot(pen='g', name="AccelY")
            self.accel_z_curve = self.accel_plot.plot(pen='b', name="AccelZ")

        # Set up gyroscope plot
        if hasattr(self.ui, 'gyro_plot_widget'):
            self.gyro_plot = self.ui.gyro_plot_widget
            self.gyro_plot.setBackground(QColor(0, 0, 0, 100))
            self.gyro_plot.setTitle("Gyroscope Data (°/sec)", color='w', size='14pt', bold=True)
            self.gyro_plot.setLabel('left', 'Angular Velocity (°/sec)')
            self.gyro_plot.setLabel('bottom', 'Time')
            self.gyro_plot.addLegend()
            self.gyro_plot.showGrid(x=True, y=True)

            # Create gyroscope plot curves
            self.gyro_x_curve = self.gyro_plot.plot(pen='r', name="GyroX")
            self.gyro_y_curve = self.gyro_plot.plot(pen='g', name="GyroY")
            self.gyro_z_curve = self.gyro_plot.plot(pen='b', name="GyroZ")

    def setup_ui_connections(self):
        """Connect UI buttons to their handlers"""
        if hasattr(self.ui, 'refrech_btn_MS'):
            self.ui.refrech_btn_MS.clicked.connect(self.request_board_status)

    # ============================================================================
    # UI UPDATE METHODS (SLOTS)
    # ============================================================================
    @pyqtSlot(float, float, float)
    def update_accelerometer_ui(self, x, y, z):
        """Thread-safe accelerometer data update"""
        if hasattr(self.ui, 'Accelx_lineEdit'):
            self.ui.Accelx_lineEdit.setText(f"{x:.2f} g")
        if hasattr(self.ui, 'Accely_lineEdit'):
            self.ui.Accely_lineEdit.setText(f"{y:.2f} g")
        if hasattr(self.ui, 'Accelz_lineEdit'):
            self.ui.Accelz_lineEdit.setText(f"{z:.2f} g")

    @pyqtSlot(float, float, float)
    def update_gyroscope_ui(self, x, y, z):
        """Thread-safe gyroscope data update"""
        if hasattr(self.ui, 'Gyrox_lineEdit'):
            self.ui.Gyrox_lineEdit.setText(f"{x:.2f} °/sec")
        if hasattr(self.ui, 'Gyroy_lineEdit'):
            self.ui.Gyroy_lineEdit.setText(f"{y:.2f} °/sec")
        if hasattr(self.ui, 'Gyroz_lineEdit'):
            self.ui.Gyroz_lineEdit.setText(f"{z:.2f} °/sec")

    @pyqtSlot(str)
    def update_temperature_ui(self, temp):
        """Thread-safe temperature update"""
        if hasattr(self.ui, 'temp_lineEdit'):
            self.ui.temp_lineEdit.setText(f"{temp} °C")

    @pyqtSlot(str, str, str)
    def update_board_status_ui(self, board_name, status, color):
        """Thread-safe board status update"""
        if hasattr(self.ui, 'lab_board_MS'):
            self.ui.lab_board_MS.setText(board_name)
        if hasattr(self.ui, 'lab_board_status_MS'):
            self.ui.lab_board_status_MS.setText(status)
        self.apply_board_status_style(color)

    @pyqtSlot(str)
    def update_led_status_ui(self, color):
        """Thread-safe LED status update"""
        self.apply_led_style(color)

    @pyqtSlot(float, float, float, float, float, float)
    def update_plots_ui(self, accelX, accelY, accelZ, gyroX, gyroY, gyroZ):
        """Thread-safe plot update"""
        # Append new data
        self.accel_data['x'].append(accelX)
        self.accel_data['y'].append(accelY)
        self.accel_data['z'].append(accelZ)
        self.gyro_data['x'].append(gyroX)
        self.gyro_data['y'].append(gyroY)
        self.gyro_data['z'].append(gyroZ)
        self.time_data.append(len(self.time_data))

        # Trim data buffers if needed
        if len(self.time_data) > self.max_data_points:
            for axis in ['x', 'y', 'z']:
                self.accel_data[axis].pop(0)
                self.gyro_data[axis].pop(0)
            self.time_data.pop(0)

        # Update plots if they exist
        if hasattr(self, 'accel_x_curve'):
            self.accel_x_curve.setData(self.time_data, self.accel_data['x'])
            self.accel_y_curve.setData(self.time_data, self.accel_data['y'])
            self.accel_z_curve.setData(self.time_data, self.accel_data['z'])
        
        if hasattr(self, 'gyro_x_curve'):
            self.gyro_x_curve.setData(self.time_data, self.gyro_data['x'])
            self.gyro_y_curve.setData(self.time_data, self.gyro_data['y'])
            self.gyro_z_curve.setData(self.time_data, self.gyro_data['z'])

    @pyqtSlot()
    def show_error_state_ui(self):
        """Thread-safe error state display"""
        error_text = "ERR"
        if hasattr(self.ui, 'Accelx_lineEdit'):
            self.ui.Accelx_lineEdit.setText(error_text)
        if hasattr(self.ui, 'Accely_lineEdit'):
            self.ui.Accely_lineEdit.setText(error_text)
        if hasattr(self.ui, 'Accelz_lineEdit'):
            self.ui.Accelz_lineEdit.setText(error_text)
        if hasattr(self.ui, 'Gyrox_lineEdit'):
            self.ui.Gyrox_lineEdit.setText(error_text)
        if hasattr(self.ui, 'Gyroy_lineEdit'):
            self.ui.Gyroy_lineEdit.setText(error_text)
        if hasattr(self.ui, 'Gyroz_lineEdit'):
            self.ui.Gyroz_lineEdit.setText(error_text)
        if hasattr(self.ui, 'temp_lineEdit'):
            self.ui.temp_lineEdit.setText(error_text)

    # ============================================================================
    # STYLE MANAGEMENT
    # ============================================================================
    def apply_board_status_style(self, color):
        """Apply styling to board status display"""
        if not hasattr(self.ui, 'lab_board_status_MS'):
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
        self.ui.lab_board_status_MS.setStyleSheet(style)

    def apply_led_style(self, color):
        """Apply styling to LED indicator"""
        if not hasattr(self.ui, 'led_boardST_5'):
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
        self.ui.led_boardST_5.setStyleSheet(style)

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_mpu6050_message(self, topic, payload):
        """Handle incoming MPU6050 sensor data"""
        print(f"[MPU6050] Received data - Topic: {topic}, Payload: {payload}")
        
        if topic == MQTT_TOPIC_MPU6050:
            try:
                # Parse and validate JSON payload
                sensor_data = json.loads(payload)
                print(f"[MPU6050] Parsed data: {sensor_data}")
                
                # Extract data with fallback values
                accelX = sensor_data.get("accelX", 0)
                accelY = sensor_data.get("accelY", 0)
                accelZ = sensor_data.get("accelZ", 0)
                gyroX = sensor_data.get("gyroX", 0)
                gyroY = sensor_data.get("gyroY", 0)
                gyroZ = sensor_data.get("gyroZ", 0)
                temp = sensor_data.get("temp", "--")

                # Update UI through signals
                self.accelerometer_data_changed.emit(accelX, accelY, accelZ)
                self.gyroscope_data_changed.emit(gyroX, gyroY, gyroZ)
                self.temperature_changed.emit(str(temp))
                
                # Update plots
                self.plot_update_signal.emit(accelX, accelY, accelZ, gyroX, gyroY, gyroZ)

            except json.JSONDecodeError as e:
                print(f"[MPU6050] JSON decode error: {e}")
                self.error_state_signal.emit()
            except Exception as e:
                print(f"[MPU6050] Processing error: {e}")
                self.error_state_signal.emit()
        else:
            print(f"[MPU6050] Unexpected topic: {topic}")

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
                    self.led_status_changed.emit("green")
                    self.status_received = True
                else:
                    self.board_status_changed.emit(board_name, status.capitalize(), "red")
                    self.led_status_changed.emit("red")
                    
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
            self.led_status_changed.emit("red")

    # ============================================================================
    # CLEANUP
    # ============================================================================
    def deactivate(self):
        """Cleanly deactivate the project, including removing plot legends."""
        print("deactivate P5")

        try:
            # Send shutdown command
            self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

            # Unsubscribe from topics
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MPU6050)
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)

            # Reset UI displays
            self.init_sensor_display()
            self.board_status_changed.emit("Unknown", "Disconnected", "red")
            self.led_status_changed.emit("red")

            # Clear plot data buffers
            self.accel_data = {'x': [], 'y': [], 'z': []}
            self.gyro_data = {'x': [], 'y': [], 'z': []}
            self.time_data = []

            # Remove legends and curves without recreating them
            if hasattr(self, 'accel_plot'):
                self.accel_plot.clear()  # Removes all items (curves + legend)
                self.accel_plot.setTitle("Accelerometer Data (g)", color='w', size='14pt', bold=True)
                self.accel_plot.setLabel('left', 'Acceleration (g)')
                self.accel_plot.setLabel('bottom', 'Time')
                self.accel_plot.showGrid(x=True, y=True)
                # Do NOT recreate curves or legend here

            if hasattr(self, 'gyro_plot'):
                self.gyro_plot.clear()  # Removes all items (curves + legend)
                self.gyro_plot.setTitle("Gyroscope Data (°/sec)", color='w', size='14pt', bold=True)
                self.gyro_plot.setLabel('left', 'Angular Velocity (°/sec)')
                self.gyro_plot.setLabel('bottom', 'Time')
                self.gyro_plot.showGrid(x=True, y=True)
                # Do NOT recreate curves or legend here

            print("[MPU6050] Project deactivated. Legends and curves removed.")

        except Exception as e:
            print(f"[MPU6050] Error during deactivation: {e}")