# ========================
#         Imports
# ========================
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
import pyqtgraph as pg
from collections import deque
import time
from data import MQTT_TOPIC_SENSOR, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs, MQTT_TOPIC_CONTROL


class WaterLevelControllerWindow(QObject):
    """Thread-safe water level controller that works with PyQt5"""
    # ============================================================================
    # SIGNALS
    # ============================================================================
    water_level_changed = pyqtSignal(float)
    status_update = pyqtSignal(str, str)
    update_plot_signal = pyqtSignal()
    board_connected_signal = pyqtSignal(bool)
    clear_history_signal = pyqtSignal()
    log_message_signal = pyqtSignal(str)
    
    # ============================================================================
    # INITIALIZATION
    # ============================================================================
    def __init__(self, mqtt_client, ui):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.ui = ui
        
        # Control variables
        self._water_level = 0.0
        self._target_level = 20.0
        self._filling = False
        self._draining = False
        self._auto_mode = True
        self._board_connected = False
        self.status_received = False
        self.hysteresis = 2.0
        
        # flag to control when status messages should be processed
        self._waiting_for_status = False

        # History tracking
        self.max_history_points = 100
        self.history_timestamps = deque(maxlen=self.max_history_points)
        self.history_levels = deque(maxlen=self.max_history_points)
        self.start_time = time.time()
        
        # Setup
        self.connect_signals()
        self.init_ui()
        self.setup_mqtt()
        self.setup_timers()
        
    # ============================================================================
    # CORE METHODS
    # ============================================================================
    def connect_signals(self):
        """Connect all signals to their slots"""
        self.water_level_changed.connect(self.update_water_level_ui)
        self.status_update.connect(self.update_status_ui)
        self.update_plot_signal.connect(self.update_history_plot)
        self.board_connected_signal.connect(self.update_connection_state)
        self.clear_history_signal.connect(self.clear_history_data)
        self.log_message_signal.connect(self.append_log_message)

    def init_ui(self):
        """Initialize all UI components"""
        self.setup_history_plot()
        
        # Board status
        if hasattr(self.ui, 'lab_board_SS'):
            self.ui.lab_board_SS.setText("Unknown")
        if hasattr(self.ui, 'lab_mqtt_broker_SS'):
            self.ui.lab_mqtt_broker_SS.setText(self.ui.host_lineEdit.text())
        if hasattr(self.ui, 'refrech_btn_SS'):
            self.ui.refrech_btn_SS.clicked.connect(self.request_board_status)
        
        # Mode switch
        if hasattr(self.ui, 'SwitchMode'):
            switch = self.ui.SwitchMode
            switch._circle_radius = 12
            switch._bg_color = "#F2F2F2"
            switch._circle_color = "#000000"
            switch._active_color = "#03A9F4"
            switch.setFixedSize(50, 16)
            switch.update()
            self.ui.SwitchMode.stateChanged.connect(self.handle_switch)
            self.ui.SwitchMode.setChecked(False)
        
        # Manual controls
        self.ui.fillButton.setEnabled(False)
        self.ui.drainButton.setEnabled(False)
        self.ui.fillButton.pressed.connect(self.start_fill)
        self.ui.fillButton.released.connect(self.stop_fill)
        self.ui.drainButton.pressed.connect(self.start_drain)
        self.ui.drainButton.released.connect(self.stop_drain)

        # Target level
        self.ui.targetLevelSlider.valueChanged.connect(self.target_level_changed)
        self.ui.targetLevelSlider.setValue(int(self._target_level))
        self.ui.targetLevelDisplay.setText(f"{self._target_level:.1f}%")
        
        # Status display
        self.ui.statusLabel.setText("Status: Automatic")
        self.ui.statusLabel.setStyleSheet("font-weight: bold; background-color:transparent; color: #2196F3;")

    def setup_history_plot(self):
        """Configure the history plot"""
        if hasattr(self.ui, 'Wate_Level_History_Plot'):
            plot = self.ui.Wate_Level_History_Plot
            plot.setBackground('transparent')
            plot.setLabel('left', 'Water Level', units='%')
            plot.setLabel('bottom', 'Time', units='s')
            plot.setTitle('Water Level History')
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setYRange(0, 100)
            
            pen = pg.mkPen(color='#2196F3', width=2)
            self.history_curve = plot.plot(pen=pen, name='Water Level')
            
            target_pen = pg.mkPen(color='#FF5722', width=2, style=pg.QtCore.Qt.DashLine)
            self.target_line = plot.plot(pen=target_pen, name='Target Level')
            
            plot.addLegend()

    def setup_mqtt(self):
        """Setup MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_SENSOR, self.handle_sensor_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_message3)

    def setup_timers(self):
        """Initialize control and plot timers"""
        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self.update_control_simple)
        
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(lambda: self.update_plot_signal.emit())
        
        if self._auto_mode:
            self.control_timer.start(500)
        self.plot_timer.start(1000)

    # ============================================================================
    # UI UPDATE METHODS
    # ============================================================================
    @pyqtSlot(float)   
    def update_water_level_ui(self, level):
        """Update water level displays"""
        if hasattr(self.ui, 'tankProgressBar'):
            self.ui.tankProgressBar.setValue(int(level))
        if hasattr(self.ui, 'levelDisplay'):
            self.ui.levelDisplay.setText(f"{level:.1f}%")
    
    @pyqtSlot(str, str)
    def update_status_ui(self, text, style):
        """Update status label"""
        if hasattr(self.ui, 'statusLabel'):
            self.ui.statusLabel.setText(text)
            self.ui.statusLabel.setStyleSheet(style)
   
    @pyqtSlot()
    def update_history_plot(self):
        """Update the history plot"""
        if not hasattr(self, 'history_curve'):
            return
            
        if len(self.history_timestamps) > 0:
            self.history_curve.setData(list(self.history_timestamps), list(self.history_levels))
            
            if len(self.history_timestamps) >= 2:
                self.target_line.setData(
                    [min(self.history_timestamps), max(self.history_timestamps)],
                    [self._target_level, self._target_level]
                )
            
            if len(self.history_timestamps) > 1:
                latest = max(self.history_timestamps)
                self.ui.Wate_Level_History_Plot.setXRange(max(0, latest - 60), latest + 5)
    
    @pyqtSlot(bool)
    def update_connection_state(self, connected):
        """Update connection state"""
        if connected:
            self.set_connected_ui()
            self.enable_all_controls()
        else:
            self.set_disconnected_ui()
            self.disable_all_controls()

    # ============================================================================
    # CONNECTION STATE UI
    # ============================================================================
    def set_connected_ui(self):
        """Update UI for connected state"""
        if hasattr(self.ui, 'lab_board_status_SS'):
            self.ui.lab_board_status_SS.setText("Connected")
            self.ui.lab_board_status_SS.setStyleSheet("""
                color: rgb(0, 255, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """)
        if hasattr(self.ui, 'led_boardST_3'):
            self.ui.led_boardST_3.setStyleSheet("""
                background-color: rgb(0, 255, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(0, 102, 0);
            """)
                
    def set_disconnected_ui(self):
        """Update UI for disconnected state"""
        if hasattr(self.ui, 'lab_board_status_SS'):
            self.ui.lab_board_status_SS.setText("Disconnected")
            self.ui.lab_board_status_SS.setStyleSheet("""
                color: rgb(255, 0, 0);
                font: bold 15px;
                background-color: transparent;
                border-radius: 10px;
            """)
        if hasattr(self.ui, 'led_boardST_3'):
            self.ui.led_boardST_3.setStyleSheet("""
                background-color: rgb(255, 0, 0);
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 2px solid rgb(128, 0, 0);
            """)
       
    def enable_all_controls(self):
        """Enable all controls"""
        if self._auto_mode and not self.control_timer.isActive():
            self.control_timer.start(500)
        self.ui.targetLevelSlider.setEnabled(True)
        self.ui.fillButton.setEnabled(not self._auto_mode)
        self.ui.drainButton.setEnabled(not self._auto_mode)
        
        mode = "Automatic" if self._auto_mode else "Manual"
        color = "#2196F3" if self._auto_mode else "#FFA000"
        self.status_update.emit(f"Status: {mode}", f"font-weight: bold; background-color:transparent; color: {color};")

    def disable_all_controls(self):
        """Disable all controls"""
        if self.control_timer.isActive():
            self.control_timer.stop()
        self.ui.targetLevelSlider.setEnabled(False)
        self.ui.fillButton.setEnabled(False)
        self.ui.drainButton.setEnabled(False)

    # ============================================================================
    # CONTROL LOGIC
    # ============================================================================
    def handle_switch(self, state):
        """Handle mode switch"""
        self._auto_mode = not state
        
        if self._auto_mode:
            if not self.control_timer.isActive():
                self.control_timer.start(500)
            self.ui.fillButton.setEnabled(False)
            self.ui.drainButton.setEnabled(False)
            self.status_update.emit("Status: Automatic", "font-weight: bold; background-color:transparent; color: #2196F3;")
            self.log_message("Switched to Automatic mode")
            
            if self._filling or self._draining:
                self.stop_fill()
                self.stop_drain()
        else:
            if self.control_timer.isActive():
                self.control_timer.stop()
            self.ui.fillButton.setEnabled(True)
            self.ui.drainButton.setEnabled(True)
            self.status_update.emit("Status: Manual", "font-weight: bold; background-color:transparent; color: #FFA000;")
            self.log_message("Switched to Manual mode")

    def update_control_simple(self):
        """Automatic control logic"""
        if not self._board_connected or not self._auto_mode:
            return
            
        current = self._water_level
        target = self._target_level

        if target > current:
            self.log_message(f"Target {target:.1f}% > Level {current:.1f}% – FILLING")
            self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_ON DRAIN_OFF")
        elif target < current:
            self.log_message(f"Target {target:.1f}% < Level {current:.1f}% – DRAINING")
            self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_OFF DRAIN_ON")
        else:
            self.log_message(f"Target {target:.1f}% = Level {current:.1f}% – IDLE")
            self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_DRAIN_OFF")

    # ============================================================================
    # MANUAL CONTROL
    # ============================================================================
    def start_fill(self):
        """Start manual fill"""
        if not self._board_connected or self._auto_mode or self._filling:
            return
        self._filling = True
        self._draining = False
        self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_ON DRAIN_OFF")
        self.log_message("Manual FILL started")
        self.update_status_display()

    def stop_fill(self):
        """Stop manual fill"""
        if not self._board_connected or self._auto_mode or not self._filling:
            return
        self._filling = False
        self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_DRAIN_OFF")
        self.log_message("Manual FILL stopped")
        self.update_status_display()

    def start_drain(self):
        """Start manual drain"""
        if not self._board_connected or self._auto_mode or self._draining:
            return
        self._draining = True
        self._filling = False
        self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_OFF DRAIN_ON")
        self.log_message("Manual DRAIN started")
        self.update_status_display()

    def stop_drain(self):
        """Stop manual drain"""
        if not self._board_connected or self._auto_mode or not self._draining:
            return
        self._draining = False
        self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_DRAIN_OFF")
        self.log_message("Manual DRAIN stopped")
        self.update_status_display()

    def update_status_display(self):
        """Update manual control status"""
        status = "Manual"
        if self._filling:
            status += " - Filling"
        elif self._draining:
            status += " - Draining"
        else:
            status += " - Idle"
        self.status_update.emit(f"Status: {status}", "font-weight: bold; background-color:transparent;  color: white;")

    # ============================================================================
    # TARGET LEVEL CONTROL
    # ============================================================================
    def target_level_changed(self, value):
        """Handle target level change"""
        new_target = float(value)
        old_target = self._target_level
        self._target_level = new_target
        self.ui.targetLevelDisplay.setText(f"{new_target:.1f}%")
        self.log_message(f"Target level changed from {old_target:.1f}% to {new_target:.1f}%")

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_sensor_message(self, topic, payload):
        """Process water level messages"""
        try:
            if payload.startswith("Water Level:"):
                level_str = payload.split(':')[1].strip().split('%')[0].strip()
                new_level = float(level_str)
                
                self._water_level = new_level
                self.add_to_history(new_level)
                self.water_level_changed.emit(new_level)
        except Exception as e:
            print(f"Sensor message error: {e}")

    def handle_status_message3(self, topic, payload):
        """Process board status messages"""
        if not self._waiting_for_status:
            return
        try:
            if "Board :" in payload and "Status :" in payload:
                board_part, status_part = payload.split("Status :")
                board_name = board_part.replace("Board :", "").strip()
                status = status_part.strip().lower()
                
                self.status_received = True
                if status == "connected":
                    print("Connected to control board")
                    self._board_connected = True
                    self.board_connected_signal.emit(True)
                    if hasattr(self.ui, 'lab_board_SS'):
                        self.ui.lab_board_SS.setText(board_name)
                else:
                    if hasattr(self.ui, 'lab_board_SS'):
                        self.ui.lab_board_SS.setText("Unknown")
        except Exception as e:
            print(f"Status message error: {e}")

    # ============================================================================
    # BOARD STATUS MANAGEMENT
    # ============================================================================
    def request_board_status(self):
        """Request board status"""
        self.status_received = False
        self._waiting_for_status = True  # Set flag before requesting
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "status_request")
        QTimer.singleShot(5000, self.check_status_response)

    def check_status_response(self):
        """Check for status response"""
        if not self.status_received and self._waiting_for_status:
            self._board_connected = False
            self.board_connected_signal.emit(False)
        # Always reset the flag after timeout
        self._waiting_for_status = False
    # ============================================================================
    # HISTORY MANAGEMENT
    # ============================================================================
    def add_to_history(self, level):
        """Add level to history"""
        current_time = time.time() - self.start_time
        self.history_timestamps.append(current_time)
        self.history_levels.append(level)

    def clear_history_data(self):
        """Clear history data"""
        self.history_timestamps.clear()
        self.history_levels.clear()
        self.start_time = time.time()
        
        if hasattr(self, 'history_curve'):
            self.history_curve.setData([], [])
        if hasattr(self, 'target_line'):
            self.target_line.setData([], [])
        
        self.log_message("Water level history cleared")

    # ============================================================================
    # LOG MESSSAGE
    # ============================================================================
    def log_message(self, message):
        """Log a message"""
        self.log_message_signal.emit(message)

    def append_log_message(self, message):
        """Append message to log"""
        if hasattr(self.ui, 'logText'):
            ts = datetime.now().strftime("%H:%M:%S")
            self.ui.logText.append(f"[{ts}] {message}")
            sb = self.ui.logText.verticalScrollBar()
            sb.setValue(sb.maximum())

    # ============================================================================
    # CLEANUP
    # ============================================================================
    def deactivate(self):
        print("deactivate P3")
        """Prepare for shutdown"""
        try:
            # Send shutdown-related MQTT commands
            self.mqtt_client.publish(MQTT_TOPIC_CONTROL, "FILL_DRAIN_OFF")
            self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

            # Stop timers if they exist
            if hasattr(self, 'control_timer'):
                self.control_timer.stop()
            if hasattr(self, 'plot_timer'):
                self.plot_timer.stop()

            # Update UI and internal status
            if hasattr(self, 'set_disconnected_ui'):
                self.set_disconnected_ui()
            
            self._board_connected = False
            if hasattr(self, 'board_connected_signal'):
                self.board_connected_signal.emit(False)
            self._waiting_for_status = False

            # Unsubscribe from MQTT topics
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_SENSOR)
            self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)

            print("[SENSOR] Project deactivated successfully.")

        except Exception as e:
            print(f"[SENSOR] Error during deactivation: {e}")
