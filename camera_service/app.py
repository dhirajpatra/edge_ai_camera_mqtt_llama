# camera_service/app.py

import os
import time
import paho.mqtt.client as mqtt
import cv2
import numpy as np
import random


# MQTT Settings
MQTT_BROKER = "mqtt_broker"  # Change to your actual MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "camera/feed"

# Camera settings (You can update these based on your actual camera feed source)
CAMERA_SOURCE = 0  # Use 0 for the default camera or replace with IP for network cameras

client_id = f'python-mqtt-{random.randint(0, 1000)}'

# Initialize MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Connect to the MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"MQTT connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

mqtt_client.on_connect = on_connect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

def process_frame(frame):
    """Apply any image processing to the frame, if needed."""
    # Example: Convert to grayscale (you can add more processing here)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

def capture_and_send():    
    print("⏳ Waiting for 30 seconds...")
    time.sleep(30)

    print("🔍 Checking available video devices in /dev...")
    try:
        print("📷 Devices:", os.listdir("/dev"))
    except Exception as e:
        print(f"❌ Failed to list /dev: {e}")

    # Initialize the camera once
    print(f"📷 Trying to open camera source: {CAMERA_SOURCE}")

    cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_V4L2)
    # cap = cv2.VideoCapture(CAMERA_SOURCE)

    if not cap.isOpened():
        print("❌ Could not open camera.")
    
    while True:
        print("🎥 Capturing for 5 seconds...")
        start_time = time.time()
        
        # Capture frames for 5 seconds
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            
            if ret:
                processed_frame = process_frame(frame)
                _, img_encoded = cv2.imencode('.jpg', processed_frame)
                img_bytes = img_encoded.tobytes()
                mqtt_client.publish(MQTT_TOPIC, img_bytes)
                time.sleep(5)

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Start the MQTT client loop in a separate thread
    mqtt_client.loop_start()

    # Start capturing and sending frames
    capture_and_send()

    # Ensure MQTT client stops when finished
    mqtt_client.loop_stop()
