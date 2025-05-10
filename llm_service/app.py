# llm_service/app.py

import os
import time
from llama_cpp import Llama
import paho.mqtt.client as mqtt
import json
import random
import base64 # Needed for base64 decoding
from dotenv import load_dotenv

load_dotenv()

# --- LLM Settings ---
model_path = os.getenv("MODEL_PATH")
# model_name = os.getenv("MODEL_NAME") # Not used in current script
n_ctx = int(os.getenv("LLM_CONTEXT_SIZE", 512))
max_tokens = int(os.getenv("LLM_MAX_TOKENS", 64))
n_threads = int(os.getenv("LLM_THREADS", 4))
# LLM_GPU_LAYERS = int(os.getenv("LLM_GPU_LAYERS", 0)) # Optional: for GPU offloading


# --- MQTT Settings ---
# Topic where the camera service publishes images (Using MQTT_TOPIC env var)
MQTT_IMAGE_TOPIC = os.getenv("MQTT_TOPIC", "camera/feed")
# Topic where the LLM service publishes text responses (Using MQTT_TOPIC_LLM env var)
MQTT_LLM_TOPIC_OUT = os.getenv("MQTT_TOPIC_LLM", "llm_response")


mqtt_host = os.getenv("MQTT_HOST", "mqtt_broker")
mqtt_port = int(os.getenv("MQTT_PORT", 1883))


client_id = f'python-llm-service-{random.randint(0, 1000)}' # More descriptive client ID

# --- Initialize LLM ---
print(f"Loading LLM model from {model_path}...")
try:
    llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        # n_gpu_layers=LLM_GPU_LAYERS, # Uncomment if using GPU offloading
        use_mlock=True, # Use mlock for better performance if available
        verbose=False # Reduce verbosity from llama_cpp during inference
    )
    print("LLM model loaded successfully.")
except Exception as e:
    print(f"Error loading LLM model: {e}")
    print("Please check MODEL_PATH and LLM_CONTEXT_SIZE environment variables.")
    # Exit or raise exception if LLM fails to load, as the service cannot function
    exit(1) # Exit the script


# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("MQTT connected successfully!")
        # Subscribe to the image topic upon connection
        try:
            client.subscribe(MQTT_IMAGE_TOPIC)
            print(f"Subscribed to image topic: {MQTT_IMAGE_TOPIC}")
        except Exception as e:
             print(f"Failed to subscribe to {MQTT_IMAGE_TOPIC}: {e}")
    else:
        print(f"MQTT failed to connect, return code {reason_code}")
        # Implement retry logic here if needed

def on_disconnect(client, userdata, reason_code, properties):
    print(f"MQTT disconnected with result code {reason_code}.")
    # Implement logic here to attempt reconnection

def on_message(client, userdata, msg):
    """
    Callback for when a message is received from a subscribed topic.
    This function now expects messages from the image topic.
    """
    print(f"Received message on topic {msg.topic}")

    if msg.topic == MQTT_IMAGE_TOPIC:
        try:
            # --- Decode Image Data ---
            # Assuming the payload is a JSON string containing base64 image data
            payload_str = msg.payload.decode('utf-8')
            message_data = json.loads(payload_str)

            if message_data:
                print("Image data decoded.")

                # --- Generate LLM Prompt based on Detection static prompt ---
                prompt_text = "A faces were detected in an image. What general observations or insights can you provide about a face in the image?"

                print(f"LLM Prompt: '{prompt_text}'")

                # --- Run LLM Inference ---
                try:
                    # Using a simple text completion interface
                    output = llm(
                        prompt=prompt_text,
                        max_tokens=max_tokens,
                        stop=["Q:", "\n"], # Stop sequences common for instruct models
                        echo=False # Don't include the prompt in the output
                    )
                    # Extract the response text
                    llm_response = output["choices"][0]["text"].strip()
                    print(f"LLM Response: '{llm_response}'")

                    # --- Publish LLM Response ---
                    try:
                        publish_result = client.publish(MQTT_LLM_TOPIC_OUT, llm_response)
                        if publish_result.rc == mqtt.MQTT_ERR_SUCCESS:
                             print(f"Published LLM response to {MQTT_LLM_TOPIC_OUT}")
                        else:
                             print(f"Failed to publish LLM response, result code: {publish_result.rc}")
                    except Exception as e:
                        print(f"Error publishing LLM response: {e}")

                except Exception as e:
                    print(f"Error during LLM inference: {e}")
                    # Depending on the error, you might want to stop or log more

            else:
                print("Received message on image topic without 'image' key in payload.")
                # This could be other JSON data on the topic, maybe log or handle differently
                try:
                    # Attempt to process as generic JSON if it's not an image payload
                    # You might add more specific handling here based on expected messages
                    print("Attempting to process as generic JSON...")
                    data = json.loads(payload_str)
                    print(f"Generic JSON payload received: {data}")
                    # You could add logic here to prompt LLM based on other data
                except json.JSONDecodeError:
                    print("Payload is not JSON.")
                except Exception as e:
                     print(f"Error handling generic JSON payload: {e}")


        except json.JSONDecodeError:
            print("Failed to decode JSON payload from image topic (initial check).")
        except base64.binascii.Error:
            print("Failed to decode base64 image data from image payload.")
        except Exception as e:
            print(f"An unexpected error occurred while processing message: {e}")

    # You could add logic here to handle messages from other topics if subscribed (not expected by default)
    # elif msg.topic == "some/other/topic":
    #     pass


# --- Initialize MQTT Client ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)

# Set MQTT callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message # This callback now handles the image topic


# --- Main Execution ---
if __name__ == "__main__":
    print(f"Connecting to MQTT Broker at {mqtt_host}:{mqtt_port}...")
    # Use connect_async and loop_start for non-blocking operation
    try:
        mqtt_client.connect_async(mqtt_host, mqtt_port, 60)
        mqtt_client.loop_start() # Start the network loop in a background thread
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")
        exit(1) # Exit if MQTT connection fails at startup

    print("LLM Service started. Waiting for messages...")

    # The MQTT loop is running in the background.
    # Use loop_forever to keep the main thread running and processing messages.
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("LLM Service interrupted. Shutting down.")
    finally:
        print("Stopping MQTT loop and disconnecting.")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("LLM Service shut down.")