# ========================
#         Imports
# ========================
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
import pyqtgraph as pg
from collections import deque
import time
import re
import csv
from data import MQTT_TOPIC_LOADCELL, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs


class LOADCELL(QObject):
    """Thread-safe load cell controller with weight history tracking"""
    
    # ============================================================================
    # SIGNALS DEFINITION
    # ============================================================================
    weight_changed = pyqtSignal(float, str)      # weight_value, display_text
    status_update = pyqtSignal(str, str)         # message, style
    update_plot_signal = pyqtSignal()
    board_connected_signal = pyqtSignal(bool)
    clear_history_signal = pyqtSignal()
    
    # ============================================================================
    # INITIALIZATION METHODS
    # ============================================================================
    def __init__(self, mqtt_client, ui):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.ui = ui
        
        # Initialize control variables
        self._current_weight = 0.0
        self._board_connected = False
        self.status_received = False
        
        # Initialize all components
        self.init_history_tracking()
        self.init_statistics_tracking()
        self.connect_signals()
        self.init_ui()
        self.setup_mqtt()
        self.setup_timers()

    def init_history_tracking(self):
        """Initialize weight history tracking"""
        self.max_history_points = 100  # Keep last 100 readings
        self.history_timestamps = deque(maxlen=self.max_history_points)
        self.history_weights = deque(maxlen=self.max_history_points)
        self.start_time = time.time()

    def init_statistics_tracking(self):
        """Initialize statistics tracking variables"""
        self.max_weight_seen = None
        self.min_weight_seen = None
        self.total_weight_sum = 0.0
        self.total_weight_count = 0

    def connect_signals(self):
        """Connect internal signals to slots for thread-safe operations"""
        self.weight_changed.connect(self.update_weight_ui)
        self.status_update.connect(self.update_status_ui)
        self.update_plot_signal.connect(self.update_history_plot)
        self.board_connected_signal.connect(self.update_connection_state)
        self.clear_history_signal.connect(self.clear_history_data)

    def init_ui(self):
        """Initialize all UI components"""
        self.setup_weight_display()
        self.setup_history_plot()
        self.setup_status_display()
        self.setup_control_buttons()
        self.set_disconnected_ui()

    def setup_mqtt(self):
        """Initialize MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_LOADCELL, self.handle_loadcell_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_message4)

    def setup_timers(self):
        """Initialize system timers"""
        # Plot update timer
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(lambda: self.update_plot_signal.emit())
        self.plot_timer.start(1000)  # Update plot every 1 second
        
        # Status check timer (optional periodic status check)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.periodic_status_check)
        # Uncomment to enable periodic status checks
        # self.status_timer.start(30000)  # Check every 30 seconds

    # ============================================================================
    # UI SETUP METHODS
    # ============================================================================
    def setup_weight_display(self):
        """Setup weight display components"""
        if hasattr(self.ui, 'loadCell_val_label'):
            self.ui.loadCell_val_label.setText("--")

    def setup_history_plot(self):
        """Setup the weight history plot"""
        if hasattr(self.ui, 'Weight_History_Plot'):
            plot_widget = self.ui.Weight_History_Plot
            
            # Configure plot appearance
            plot_widget.setBackground('transparent')  # White background
            plot_widget.setLabel('left', 'Weight', units='kg')
            plot_widget.setLabel('bottom', 'Time', units='s')
            plot_widget.setTitle('Weight History')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Create plot curves
            pen = pg.mkPen(color='#2196F3', width=2)  # Blue line
            self.weight_curve = plot_widget.plot(pen=pen, name='Weight')
            
            # Enable auto-range and add legend
            plot_widget.enableAutoRange('xy', True)
            plot_widget.addLegend()
            
            print("Weight history plot initialized")
        else:
            print("Warning: Weight_History_Plot not found in UI")

    def setup_status_display(self):
        """Setup status display components"""
        if hasattr(self.ui, 'lab_board_LC'):
            self.ui.lab_board_LC.setText("Unknown")
            
        if hasattr(self.ui, 'lab_mqtt_broker_LC') and hasattr(self.ui, 'host_lineEdit'):
            self.ui.lab_mqtt_broker_LC.setText(self.ui.host_lineEdit.text())

    def setup_control_buttons(self):
        """Setup control buttons and their connections"""
        if hasattr(self.ui, 'refrech_btn_LC'):
            self.ui.refrech_btn_LC.clicked.connect(self.request_board_status)
            
        if hasattr(self.ui, 'clear_history_btn_LC'):
            self.ui.clear_history_btn_LC.clicked.connect(self.clear_weight_history)
            
        if hasattr(self.ui, 'export_data_btn_LC'):
            self.ui.export_data_btn_LC.clicked.connect(self.export_weight_data)

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_loadcell_message(self, topic, payload):
        """Process incoming load cell data"""
        try:
            if topic != MQTT_TOPIC_LOADCELL:
                return
                
            payload_str = str(payload).strip()            
            
            if ": " in payload_str:
                # Extract value (format: "Load: 12.34 kg")
                _, value_with_unit = payload_str.split(": ", 1)
                
                # Extract numeric weight for plotting
                weight_value = self.extract_weight_value(value_with_unit)
                
                if weight_value is not None:
                    self._current_weight = weight_value
                    self.add_to_history(weight_value)
                    self.weight_changed.emit(weight_value, value_with_unit)
                else:
                    self.weight_changed.emit(0.0, "ERR")
            else:
                self.weight_changed.emit(0.0, "ERR")
                
        except Exception as e:
            print(f"Error processing load cell message: {e}")
            self.weight_changed.emit(0.0, "ERR")

    def handle_status_message4(self, topic, payload):
        """Process board status messages"""
        try:
            # Skip our own status requests
            if str(payload).strip() == "status_request":
                return
                
            if "Board :" in payload and "Status :" in payload:
                board_part, status_part = payload.split("Status :")
                board_name = board_part.replace("Board :", "").strip()
                status = status_part.strip()
                
                # Update board name display
                if hasattr(self.ui, 'lab_board_LC'):
                    self.ui.lab_board_LC.setText(board_name)
                
                # Update connection state
                self.status_received = True
                connected = status.lower() == "connected"
                self.board_connected_signal.emit(connected)
                
                if connected:
                    print(f"Connected to board: {board_name}")
                else:
                    print(f"Board {board_name} status: {status}")
                    
        except Exception as e:
            print(f"Error processing status message: {e}")

    # ============================================================================
    # DATA PROCESSING METHODS
    # ============================================================================
    def extract_weight_value(self, payload_text):
        """Extract numeric weight value from payload"""
        try:
            # Look for patterns like "12.34 kg", "12.34", etc.
            weight_pattern = r'(\d+\.?\d*)\s*(?:kg|g|lbs?)?'
            matches = re.findall(weight_pattern, payload_text.lower())
            
            if matches:
                weight = float(matches[0])
                return weight
            else:
                print(f"No numeric weight found in: {payload_text}")
                return None
                
        except Exception as e:
            print(f"Error extracting weight: {e}")
            return None

    def add_to_history(self, weight_value):
        """Add new weight reading to history"""
        try:
            current_time = time.time() - self.start_time
            self.history_timestamps.append(current_time)
            self.history_weights.append(weight_value)
            
        except Exception as e:
            print(f"Error adding weight to history: {e}")

    def update_session_statistics(self, weight_value):
        """Track and update session max, min, and average"""
        # Update min and max
        if self.max_weight_seen is None or weight_value > self.max_weight_seen:
            self.max_weight_seen = weight_value

        if self.min_weight_seen is None or weight_value < self.min_weight_seen:
            self.min_weight_seen = weight_value

        # Update running total and count
        self.total_weight_sum += weight_value
        self.total_weight_count += 1

        avg_weight = self.total_weight_sum / self.total_weight_count if self.total_weight_count > 0 else 0.0

        # Update UI statistics displays
        self.update_statistics_ui(avg_weight)

    def update_statistics_ui(self, avg_weight):
        """Update statistics display in UI"""
        if hasattr(self.ui, 'loadCell_val_label_Max'):
            self.ui.loadCell_val_label_Max.setText(f"{self.max_weight_seen:.2f} kg")

        if hasattr(self.ui, 'loadCell_val_label_MIN'):
            self.ui.loadCell_val_label_MIN.setText(f"{self.min_weight_seen:.2f} kg")

        if hasattr(self.ui, 'loadCell_val_label_Average'):
            self.ui.loadCell_val_label_Average.setText(f"{avg_weight:.2f} kg")

    # ============================================================================
    # UI UPDATE METHODS (SLOTS)
    # ============================================================================
    @pyqtSlot(float, str)
    def update_weight_ui(self, weight_value, display_text):
        """Update weight display in UI"""
        if hasattr(self.ui, 'loadCell_val_label'):
            self.ui.loadCell_val_label.setText(display_text)
            
        # Update additional weight displays if they exist
        if hasattr(self.ui, 'weight_numeric_display'):
            self.ui.weight_numeric_display.setText(f"{weight_value:.2f} kg")

        # Update session statistics
        self.update_session_statistics(weight_value)

    @pyqtSlot(str, str)
    def update_status_ui(self, text, style):
        """Update status label"""
        if hasattr(self.ui, 'status_label_LC'):
            self.ui.status_label_LC.setText(text)
            self.ui.status_label_LC.setStyleSheet(style)

    @pyqtSlot()
    def update_history_plot(self):
        """Update the history plot with current data"""
        if not hasattr(self.ui, 'Weight_History_Plot') or not hasattr(self, 'weight_curve'):
            return
            
        try:
            if len(self.history_timestamps) > 0:
                # Update the main curve
                self.weight_curve.setData(
                    list(self.history_timestamps), 
                    list(self.history_weights)
                )
                
                # Auto-scale to show recent data
                if len(self.history_timestamps) > 1:
                    latest_time = max(self.history_timestamps)
                    self.ui.Weight_History_Plot.setXRange(
                        max(0, latest_time - 120),  # Show last 2 minutes
                        latest_time + 10
                    )
                    
        except Exception as e:
            print(f"Error updating plot: {e}")

    @pyqtSlot(bool)
    def update_connection_state(self, connected):
        """Update UI based on connection state"""
        self._board_connected = connected
        
        if connected:
            self.set_connected_ui()
        else:
            self.set_disconnected_ui()

    # ============================================================================
    # CONNECTION STATE UI METHODS
    # ============================================================================
    def set_connected_ui(self):
        """Update UI for connected state"""
        if hasattr(self.ui, 'lab_board_status_LC'):
            self.ui.lab_board_status_LC.setText("Connected")
            self.ui.lab_board_status_LC.setStyleSheet("""
                color: rgb(0, 255, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """)
            
        if hasattr(self.ui, 'led_boardST_4'):
            self.ui.led_boardST_4.setStyleSheet("""
                background-color: rgb(0, 255, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(0, 102, 0);
            """)
            
        self.status_update.emit(
            "Status: Connected", 
            "font-weight: bold; color: #0D47A1;"
        )

    def set_disconnected_ui(self):
        """Update UI for disconnected state"""
        if hasattr(self.ui, 'lab_board_status_LC'):
            self.ui.lab_board_status_LC.setText("Disconnected")
            self.ui.lab_board_status_LC.setStyleSheet("""
                color: rgb(255, 0, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """)
            
        if hasattr(self.ui, 'led_boardST_4'):
            self.ui.led_boardST_4.setStyleSheet("""
                background-color: rgb(255, 0, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(128, 0, 0);
            """)
            
        self.status_update.emit(
            "Status: Disconnected", 
            "font-style: italic; color: #B0B0B0;"
        )

    # ============================================================================
    # BOARD STATUS MANAGEMENT
    # ============================================================================
    def request_board_status(self):
        """Request status from hardware"""
        try:
            self.status_received = False
            self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "status_request")
            print("Status request sent")
            
            # Set timeout to check for response
            QTimer.singleShot(5000, self.check_status_response)
            
        except Exception as e:
            print(f"Error requesting board status: {e}")

    def check_status_response(self):
        """Handle status response timeout"""
        if not self.status_received:
            print("No status response received - board may be disconnected")
            self.board_connected_signal.emit(False)

    def periodic_status_check(self):
        """Periodic status check (optional)"""
        if not self._board_connected:
            self.request_board_status()

    # ============================================================================
    # HISTORY MANAGEMENT METHODS
    # ============================================================================
    @pyqtSlot()
    def clear_history_data(self):
        """Clear history data"""
        try:
            self.history_timestamps.clear()
            self.history_weights.clear()
            self.start_time = time.time()
            
            # Reset statistics
            self.max_weight_seen = None
            self.min_weight_seen = None
            self.total_weight_sum = 0.0
            self.total_weight_count = 0
            
            if hasattr(self, 'weight_curve'):
                self.weight_curve.setData([], [])
            
            print("Weight history cleared")
            
        except Exception as e:
            print(f"Error clearing history: {e}")

    def clear_weight_history(self):
        """Public method to clear weight history"""
        self.clear_history_signal.emit()

    def set_plot_range(self, max_points=100):
        """Set the maximum number of points to display"""
        old_max = self.max_history_points
        self.max_history_points = max_points
        
        # Recreate deques with new max length
        self.history_timestamps = deque(list(self.history_timestamps), maxlen=max_points)
        self.history_weights = deque(list(self.history_weights), maxlen=max_points)
        
        print(f"Plot range changed from {old_max} to {max_points} points")

    # ============================================================================
    # DATA EXPORT METHODS
    # ============================================================================
    def export_weight_data(self, filename=None):
        """Export weight history to CSV file"""
        try:
            if len(self.history_weights) == 0:
                print("No data to export")
                return None
                
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"weight_history_{timestamp}.csv"
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Timestamp', 'Elapsed Time (s)', 'Weight (kg)'])
                
                start_datetime = datetime.now() - timedelta(
                    seconds=max(self.history_timestamps) if self.history_timestamps else 0
                )
                
                for elapsed_time, weight_val in zip(self.history_timestamps, self.history_weights):
                    actual_time = start_datetime + timedelta(seconds=elapsed_time)
                    writer.writerow([
                        actual_time.strftime('%Y-%m-%d %H:%M:%S'),
                        f"{elapsed_time:.1f}",
                        f"{weight_val:.3f}"
                    ])
            
            print(f"Weight data exported to {filename}")
            return filename
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            return None

    # ============================================================================
    # PUBLIC GETTERS AND UTILITY METHODS
    # ============================================================================
    def get_current_weight(self):
        """Get current weight value"""
        return self._current_weight

    def get_weight_statistics(self):
        """Get weight statistics"""
        if len(self.history_weights) == 0:
            return None
            
        weights = list(self.history_weights)
        return {
            'current': self._current_weight,
            'min': min(weights),
            'max': max(weights),
            'avg': sum(weights) / len(weights),
            'count': len(weights)
        }

    def get_connection_status(self):
        """Get current connection status"""
        return self._board_connected

    # ============================================================================
    # CLEANUP METHODS
    # ============================================================================
    def deactivate(self):
        """Deactivate the load cell controller and clean up resources"""
        print("deactivate P4")

        try:            
            # Send shutdown-related MQTT commands
            self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

            # Stop timers
            if hasattr(self, 'plot_timer') and self.plot_timer.isActive():
                self.plot_timer.stop()

            if hasattr(self, 'status_timer') and self.status_timer.isActive():
                self.status_timer.stop()

            # Disconnect MQTT topics
            if self.mqtt_client:
                self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_LOADCELL)
                self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)

            # Disconnect UI buttons (if needed)
            if hasattr(self.ui, 'refrech_btn_LC'):
                self.ui.refrech_btn_LC.clicked.disconnect()

            if hasattr(self.ui, 'clear_history_btn_LC'):
                self.ui.clear_history_btn_LC.clicked.disconnect()

            if hasattr(self.ui, 'export_data_btn_LC'):
                self.ui.export_data_btn_LC.clicked.disconnect()

            # Reset UI
            if hasattr(self.ui, 'loadCell_val_label'):
                self.ui.loadCell_val_label.setText("--")
            if hasattr(self.ui, 'lab_board_status_LC'):
                self.ui.lab_board_status_LC.setText("Inactive")
            if hasattr(self.ui, 'led_boardST_4'):
                self.ui.led_boardST_4.setStyleSheet("background-color: gray;")

            # Clear history and statistics
            self.clear_history_data()

            print("Load cell controller deactivated.")

        except Exception as e:
            print(f"Error during deactivation: {e}")