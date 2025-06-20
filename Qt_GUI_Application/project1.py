# ========================
#         Imports
# ========================
from data import MQTT_TOPIC_LED, MQTT_TOPIC_MQTT_Rq, MQTT_TOPIC_MQTT_Rs
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot


class LED_and_Button(QObject):
    # ============================================================================
    # SIGNALS DEFINITION
    # ============================================================================
    update_button_text = pyqtSignal(str, str)        # button object name, text
    update_label_color = pyqtSignal(str, str)        # label object name, color
    update_board_status = pyqtSignal(str, str, str)  # board_name, status, color
    update_led_status = pyqtSignal(str, str)         # led object name, color

    # ============================================================================
    # INITIALIZATION METHODS
    # ============================================================================
    def __init__(self, mqtt_client, ui):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.ui = ui
        self.status_received = False
        self.switches = {}  # Dictionary to store all switch references
        
        # Initialize all components
        self._setup_mqtt()
        self._connect_signals()
        self._init_ui_components()
        self._setup_button_mappings()
        self._setup_switch_mappings()
        self._init_buttons()
        self._init_switches()
        self._init_status_display()

    def _setup_mqtt(self):
        """Initialize MQTT subscriptions"""
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_LED, self.handle_led_message)
        self.mqtt_client.subscribe_to_topic(MQTT_TOPIC_MQTT_Rs, self.handle_status_message)

    def _connect_signals(self):
        """Connect internal signals to slots"""
        self.update_button_text.connect(self._update_button_text)
        self.update_label_color.connect(self._update_label_color)
        self.update_board_status.connect(self._update_board_status)
        self.update_led_status.connect(self._update_led_status)

    def _setup_button_mappings(self):
        """Create mapping between buttons and their LED IDs/labels"""
        self.button_map = [
            (self.ui.btn_1, "ledRED1", self.ui.label_red_led),
            (self.ui.btn_2, "ledRED2", self.ui.label_red_led_2),
            (self.ui.btn_3, "ledRED3", self.ui.label_red_led_3),
            (self.ui.btn_4, "ledRED4", self.ui.label_red_led_4),
            (self.ui.btn_5, "ledRED5", self.ui.label_red_led_5)
        ]

    def _setup_switch_mappings(self):
        """Create mapping between switches and their LED IDs/labels"""
        self.green_led_map = {
            "ledGREEN1": self.ui.label_green_led,
            "ledGREEN2": self.ui.label_green_led_2,
            "ledGREEN3": self.ui.label_green_led_3,
            "ledGREEN4": self.ui.label_green_led_4,
            "ledGREEN5": self.ui.label_green_led_5
        }
        self.switch_to_green_led = {
            "switch_1": "ledGREEN1",
            "switch_2": "ledGREEN2",
            "switch_3": "ledGREEN3",
            "switch_4": "ledGREEN4",
            "switch_5": "ledGREEN5"
        }

    def _init_ui_components(self):
        """Initialize basic UI components"""
        self.ui.refrech_btn.clicked.connect(self.request_board_status)

    def _init_buttons(self):
        """Initialize all button states and connections"""
        for btn, led_id, label in self.button_map:
            btn.setText("OFF")
            self.reset_label_color(label)
            btn.clicked.connect(lambda checked, b=btn, l=label, lid=led_id: 
                             self.toggle_state(b, l, lid))

    def _init_switches(self):
        """Initialize all switches using direct attribute access"""
        switch_names = ["switch_1", "switch_2", "switch_3", "switch_4", "switch_5"]
        
        for name in switch_names:
            if hasattr(self.ui, name):
                switch = getattr(self.ui, name)
                self._configure_switch(switch, name)
            else:
                print(f"Warning: {name} not found as direct attribute in UI!")

    def _init_status_display(self):
        """Initialize board status display"""
        self.ui.lab_board_1.setText("Unknown")
        self.ui.lab_mqtt_broker1.setText(self.ui.host_lineEdit.text())

    # ============================================================================
    # UI UPDATE METHODS (SLOTS)
    # ============================================================================
    @pyqtSlot(str, str)
    def _update_button_text(self, button_name, text):
        """Thread-safe button text update"""
        button = getattr(self.ui, button_name)
        button.setText(text)

    @pyqtSlot(str, str)
    def _update_label_color(self, label_name, color):
        """Thread-safe label color update"""
        label = getattr(self.ui, label_name)
        if color == "red":
            self._set_red_color(label)
        elif color == "green":
            self._set_green_color(label)
        else:
            self.reset_label_color(label)

    @pyqtSlot(str, str, str)
    def _update_board_status(self, board_name, status, color):
        """Thread-safe board status update"""
        self.ui.lab_board_1.setText(board_name)
        self.ui.lab_board_status1.setText(status)
        self._apply_board_status_style(color)

    @pyqtSlot(str, str)
    def _update_led_status(self, led_name, color):
        """Thread-safe LED status update"""
        led = getattr(self.ui, led_name)
        self._apply_led_style(led, color)

    # ============================================================================
    # SWITCH MANAGEMENT
    # ============================================================================
    def _configure_switch(self, switch, name):
        """Configure individual switch appearance and behavior"""
        switch._circle_radius = 26
        switch._bg_color = "#cccccc"  # Off state
        switch._circle_color = "#FFFFFF"  # Circle color
        switch._active_color = "#03A9F4"  # On state (blue)
        switch.setFixedSize(65, 30)
        
        self.switches[name] = switch
        switch.stateChanged.connect(
            lambda state, n=name: self.handle_switch_state(state, n))
        
        switch.update()
        print(f"Initialized {name} successfully")

    def handle_switch_state(self, state, switch_name):
        """Handle switch state changes - controls green LEDs"""
        print(f"{switch_name} changed to {'ON' if state else 'OFF'}")
        
        led_id = self.switch_to_green_led.get(switch_name)
        if led_id:
            label = self.green_led_map.get(led_id)
            if label:
                label_name = label.objectName()
                if state:
                    self.update_label_color.emit(label_name, "green")
                    self.mqtt_client.publish(MQTT_TOPIC_LED, f"{led_id}_ON")
                else:
                    self.update_label_color.emit(label_name, "reset")
                    self.mqtt_client.publish(MQTT_TOPIC_LED, f"{led_id}_OFF")

    # ============================================================================
    # BUTTON MANAGEMENT
    # ============================================================================
    def toggle_state(self, button, label, led_id):
        """Toggle button state and control corresponding LED"""
        button_name = button.objectName()
        label_name = label.objectName()
        
        if button.text() == "OFF":
            self.update_button_text.emit(button_name, "ON")
            self.update_label_color.emit(label_name, "red")
            self.mqtt_client.publish(MQTT_TOPIC_LED, f"{led_id}_ON")
        else:
            self.update_button_text.emit(button_name, "OFF")
            self.update_label_color.emit(label_name, "reset")
            self.mqtt_client.publish(MQTT_TOPIC_LED, f"{led_id}_OFF")

    # ============================================================================
    # STYLE MANAGEMENT
    # ============================================================================
    def reset_label_color(self, label):
        """Reset to original white color"""
        label.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 255, 255);
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
            }
        """)

    def _set_red_color(self, label):
        """Change only the background color to red"""
        label.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 0, 0);
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
            }
        """)

    def _set_green_color(self, label):
        """Change only the background color to green"""
        label.setStyleSheet("""
            QLabel {
                background-color: rgb(0, 255, 0);
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
            }
        """)

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
        self.ui.lab_board_status1.setStyleSheet(style)

    def _apply_led_style(self, led, color):
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
        led.setStyleSheet(style)

    # ============================================================================
    # MQTT MESSAGE HANDLING
    # ============================================================================
    def handle_led_message(self, topic, payload):
        """Handle incoming LED control messages for combined red/green labels"""
        print(f"[LED MESSAGE] Received payload: '{payload}'")

        try:
            if payload.startswith("leds"):
                parts = payload.split()
                if len(parts) == 2:
                    led_id, state = parts
                    led_num = led_id.replace("leds", "")  # Extract the number
                    
                    red_label_name = f"label_red_led_{led_num}" if led_num != "1" else "label_red_led"
                    green_label_name = f"label_green_led_{led_num}" if led_num != "1" else "label_green_led"
                    
                    if state == "ON":
                        self.update_label_color.emit(red_label_name, "red")
                        self.update_label_color.emit(green_label_name, "green")
                    elif state == "OFF":
                        self.update_label_color.emit(red_label_name, "reset")
                        self.update_label_color.emit(green_label_name, "reset")
        except Exception as e:
            print(f"[ERROR] Processing LED message: {e}")

    def handle_status_message(self, topic, payload):
        """Process board status messages from response topic"""
        try:           
            if "Board :" in payload and "Status :" in payload:
                board_part, status_part = payload.split("Status :")
                board_name = board_part.replace("Board :", "").strip()
                status = status_part.strip().lower()
                
                if status == "connected":
                    self.update_board_status.emit(board_name, "Connected", "green")
                    self.update_led_status.emit("led_boardST", "green")
                    self.status_received = True
                else:
                    self.update_board_status.emit(board_name, status, "red")
                    self.update_led_status.emit("led_boardST", "red")
                    
        except Exception as e:
            print(f"Error processing status message: {e}")

    # ============================================================================
    # BOARD STATUS MANAGEMENT
    # ============================================================================
    def request_board_status(self):
        """Send status request to request topic with timeout fallback"""
        self.status_received = False
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "status_request")
        print(f"[STATUS] Sent status request to {MQTT_TOPIC_MQTT_Rq}")
        
        QTimer.singleShot(1000, self.check_status_response)

    def check_status_response(self):
        """Check if we received a valid response"""
        if not self.status_received:
            print("[STATUS] No response received within timeout period")
            self.update_board_status.emit("Unknown", "Disconnected", "red")
            self.update_led_status.emit("led_boardST", "red")

    # ============================================================================
    # CLEANUP
    # ============================================================================
    def deactivate(self):
        """Clean up before exiting or switching projects."""
        print("deactivate P1")
        self.mqtt_client.publish(MQTT_TOPIC_MQTT_Rq, "TurnOFF")

        # Unsubscribe from MQTT topics
        self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_LED)
        self.mqtt_client.unsubscribe_from_topic(MQTT_TOPIC_MQTT_Rs)
        # Reset button texts and labels
        for btn, _, label in self.button_map:
            btn.setText("OFF")
            self.reset_label_color(label)

        # Reset switches and green LEDs
        for switch_name, switch in self.switches.items():
            switch.blockSignals(True)
            switch.setChecked(False)
            switch.blockSignals(False)

            led_id = self.switch_to_green_led.get(switch_name)
            if led_id:
                label = self.green_led_map.get(led_id)
                if label:
                    self.reset_label_color(label)

        # Clear board status display
        self.ui.lab_board_1.setText("Unknown")
        self.ui.lab_board_status1.setText("Disconnected")
        self._apply_board_status_style("red")
        self.update_led_status.emit("led_boardST", "red")
        
