# camera_service/app.py

import os
import time
import paho.mqtt.client as mqtt
import cv2
import numpy as np
import random
from dotenv import load_dotenv
import base64
import json
load_dotenv()

# MQTT Settings
MQTT_BROKER = "mqtt_broker"  # Change to your actual MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "camera/feed"
SLEEP_DURATION = int(os.getenv('SLEEP_DURATION', 60))

# Camera settings (You can update these based on your actual camera feed source)
CAMERA_SOURCE = 0  # Use 0 for the default camera or replace with IP for network cameras

# Store the latest received image data
latest_image_payload: bytes | None = None
latest_image_media_type: str = "image/jpeg" # Default media type, can be updated from message

client_id = f'python-mqtt-{random.randint(0, 1000)}'

# Initialize MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Connect to the MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"MQTT connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

def on_disconnect(client, userdata, reason_code, properties):
    print(f"MQTT disconnected with result code {reason_code}. Attempting to reconnect...")
    # Docker's restart policy helps, but manual reconnect logic could be added here if needed

def on_publish(client, userdata, mid, rc, properties):
    """Callback for when a message is successfully published."""
    if rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Message with mid {mid} published successfully.")
    else:
        print(f"Failed to publish message with mid {mid}. Result code: {rc}")
    # print(f"Properties: {properties}") # Optional: print properties if needed

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_publish = on_publish # Set the publish callback

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# If you manually copied it to the /app directory:
# CASCADE_PATH = '/app/haarcascade_frontalface_default.xml'
# If relying on the opencv-python package installation path:
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

# cv2.data.haarcascades points to the directory where these files are typically installed.
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

# Check if the cascade file loaded correctly
if face_cascade.empty():
    print("Error loading face cascade classifier XML file.")
    # Handle this error - perhaps exit or raise an exception
    # For simplicity in this example, we'll assume it loads.
    # In a real application, you should ensure this file is found.

def detect_faces(frame):
    """
    Detects faces in an image frame using Haar Cascades and draws rectangles.

    Args:
        frame: A NumPy array representing the image frame (e.g., from cv2.VideoCapture.read()).

    Returns:
        The original frame with bounding boxes drawn around detected faces.
        Returns the original frame unchanged if face detection fails or no faces are found.
    """
    if frame is None:
        # print("Warning: Received None frame for detection.") # Log less frequently
        return frame # Return the None frame directly

    # Haar cascades work best on grayscale images
    # Create a grayscale copy to avoid modifying the original frame in place if it were needed later
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect faces in the grayscale image
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,  # Adjust if detection is too slow or misses faces
        minNeighbors=5,   # Adjust if you get too many false positives or miss faces
        minSize=(30, 30)  # Minimum size of the object to detect
    )

    # Draw a rectangle around each detected face on the original color frame
    # Iterate through the detected bounding boxes (x, y, width, height)
    for (x, y, w, h) in faces:
        # Draw a blue rectangle with thickness 2
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

    # Return the frame with detections drawn
    return frame

def process_frame(frame):
    """
    Applies processing steps like resizing and face detection to the frame.

    Args:
        frame: A NumPy array representing the image frame.

    Returns:
        The processed frame (e.g., resized with detections).
        Returns None if the input frame is None.
    """
    if frame is None:
        # print("Warning: Received None frame for processing.") # Log less frequently
        return None

    # Example: Correctly resize the frame
    # Note: If resizing, the coordinates from detection (done on the resized frame)
    # would correspond to the resized dimensions.
    # If detection should happen on the original resolution, resize *after* detection or not at all.
    # Assuming you want to resize *before* detection:
    resized_frame = cv2.resize(frame, (640, 480))
    frame_to_process = resized_frame
    # frame_to_process = frame # Process at original capture resolution

    # Apply face detection to the frame (detect_faces handles grayscale conversion internally)
    frame_with_detections = detect_faces(frame_to_process)

    # If you wanted to return a grayscale image *after* detection, you could convert here:
    # gray_with_detections = cv2.cvtColor(frame_with_detections, cv2.COLOR_BGR2GRAY)
    # return gray_with_detections

    # Return the frame with detections (whether resized or original resolution)
    return frame_with_detections

def capture_and_send():
    """
    Captures frames from the camera, processes them, and sends them to the MQTT broker.
    """
    # Use environment variable for initial delay, default to 5 seconds
    initial_delay = int(os.getenv('STARTUP_DELAY', 5))
    print(f"⏳ Waiting for initial delay ({initial_delay} seconds)...")
    time.sleep(initial_delay)

    # Main loop to continuously capture, send, and wait
    while True:
        print("\n--- Starting a new capture cycle ---")

        # Open the camera at the start of each cycle
        print(f"📷 Trying to open camera source: {CAMERA_SOURCE}")
        # Ensure you are explicitly using the V4L2 backend as previously recommended
        cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_V4L2)

        # Check if camera opened successfully
        if not cap.isOpened():
            print(f"❌ Could not open camera source {CAMERA_SOURCE}.")
            print("😴 Waiting for 60 seconds before retrying...")
            cap.release() # Ensure any partially opened handle is released
            time.sleep(SLEEP_DURATION) # Wait before attempting to open again in the next cycle
            continue # Skip the rest of this loop iteration and start the next

        print("✅ Camera opened successfully.")

        sent_one_image = False # Flag to ensure only one image is sent per cycle
        start_time = time.time()
        capture_duration = 5 # Capture video for 5 seconds
        print(f"🎥 Capturing frames for {capture_duration} seconds...")

        # Capture frames for the specified duration
        while time.time() - start_time < capture_duration:
            ret, frame = cap.read() # Read a frame from the camera

            if ret:
                # Process and send only the first successfully read frame in this cycle
                if not sent_one_image:
                    processed_frame = process_frame(frame) # Apply your image processing
                    success, img_encoded = cv2.imencode('.jpg', processed_frame) # Encode the frame to JPG

                    if success:
                        img_bytes = img_encoded.tobytes() # Convert encoded image to bytes

                        try:
                            # Encode the image bytes to base64
                            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                            # Create the JSON payload dictionary
                            payload_dict = {
                                "image": img_base64,
                                "type": "image/jpeg" # Specify the image type
                                # You could add other metadata here like timestamp, camera_id etc.
                            }

                            # Convert the dictionary to a JSON string
                            payload_json = json.dumps(payload_dict)

                            # Publish the JSON string to MQTT
                            publish_result = mqtt_client.publish(MQTT_TOPIC, payload_json)
                            print("✅ Published one frame to MQTT")

                            # Check publish result
                            if publish_result.rc == mqtt.MQTT_ERR_SUCCESS:
                                print("✅ Published one frame (JSON with base64 image) to MQTT")
                                sent_one_image = True # Set the flag
                                # Add a small delay if needed before concluding the capture window
                                time.sleep(0.1)
                                break # Exit the inner capture loop after sending one frame
                            else:
                                print(f"❌ Failed to publish JSON message: {publish_result.rc}")
                                # Depending on the error code, you might want to break or retry
                                break # Break on publish failure to avoid issues
                        except Exception as e:
                            print(f"❌ Failed to publish frame: {e}")
                            break
            else:
                # Handle frame read failure - log if necessary, but avoid spamming logs
                # print("❌ Failed to capture frame during capture window.")
                time.sleep(0.05) # Add a small sleep to avoid a tight loop if frame reading fails

        # Release the camera resources for this cycle
        cap.release()
        # cv2.destroyAllWindows() # Not typically necessary after cap.release()

        # Optional: Add a note if no frame was sent during the capture window
        if not sent_one_image:
             print("⚠️ Note: No frame was successfully captured and sent during the last cycle.")
        else:
             print(f"✅ Finished {capture_duration}-second capture window.")

        # Wait for 1 minute before the next cycle starts
        wait_duration = SLEEP_DURATION # seconds
        print(f"😴 Waiting for {wait_duration} seconds before next cycle...")
        time.sleep(wait_duration)

if __name__ == "__main__":
    # Start the MQTT client loop in a separate thread
    mqtt_client.loop_start()

    # Start capturing and sending frames
    capture_and_send()

    # Ensure MQTT client stops when finished
    mqtt_client.loop_stop()
