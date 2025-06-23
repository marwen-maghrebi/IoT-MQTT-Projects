# ========================
#         Imports
# ========================
from PyQt5.QtCore import QObject, pyqtSignal
import paho.mqtt.client as mqtt


# ========================
#      MQTT Client Class
# ========================
class MqttClient(QObject):
    # --- Signal emitted when data is received ---
    data_received = pyqtSignal(str)

    # ========================
    #     Initialization
    # ========================
    def __init__(self):
        super().__init__()
        self._connection_result = None           # Store connection result

        # --- MQTT Client Setup ---
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # --- Internal State ---
        self._topics_to_subscribe = []           # Topics queued for subscription after connect
        self._topic_handlers = {}                # Handlers registered per topic

    # ========================
    #      MQTT Callbacks
    # ========================
    def on_connect(self, client, userdata, flags, rc):
        # --- Called upon successful or failed connection ---
        print(f"Connected to MQTT broker with result code {rc}")
        self._connection_result = rc
        if rc == 0:
            # --- Subscribe to all queued topics ---
            for topic in self._topics_to_subscribe:
                self.client.subscribe(topic)
                print(f"Subscribed to topic: {topic}")
        else:
            print(f"Connection failed with result code {rc}")

    def on_message(self, client, userdata, msg):
        # --- Called when a message is received ---
        topic = msg.topic
        payload = msg.payload.decode()

        # --- Dispatch message to registered handler ---
        if topic in self._topic_handlers:
            self._topic_handlers[topic](topic, payload)

    # ========================
    #     Topic Management
    # ========================
    def subscribe_to_topic(self, topic, handler=None):
        # --- Subscribe immediately if connected, else queue it ---
        if self.client.is_connected():
            self.client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
        else:
            self._topics_to_subscribe.append(topic)
            print(f"Topic '{topic}' queued for subscription after connection.")

        # --- Register handler if provided ---
        if handler:
            self._topic_handlers[topic] = handler

    def unsubscribe_from_topic(self, topic):
        # --- Unsubscribe from topic and remove its handler ---
        if self.client:
            self.client.unsubscribe(topic)
            print(f"Unsubscribed from topic: {topic}")

        if topic in self._topic_handlers:
            del self._topic_handlers[topic]

    # ========================
    #     Connection Control
    # ========================
    def connect_to_broker(self, broker, port, username, password):
        # --- Set credentials and connect to broker ---
        self._connection_result = None
        
        # Set username and password if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        try:
            # Attempt connection
            self.client.connect(broker, port, 60)
            self.client.loop_start()
            
            # Wait for connection result (with timeout)
            import time
            timeout = 10  # 10 seconds timeout
            start_time = time.time()
            
            while self._connection_result is None and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self._connection_result is None:
                # Timeout occurred
                self.client.loop_stop()
                return -1  # Connection timeout
            
            return self._connection_result
            
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return -1  # General connection error

    def disconnect_from_broker(self):
        # --- Gracefully disconnect and stop network loop ---
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected from MQTT broker.")

    # ========================
    #      Message Sending
    # ========================
    def publish(self, topic, message):
        # --- Publish message to specified topic ---
        if self.client:
            self.client.publish(topic, message)
            print(f"Published '{message}' to '{topic}'")
