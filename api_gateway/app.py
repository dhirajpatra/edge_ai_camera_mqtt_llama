# api_gateway/app.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import json
import random
import base64
from io import BytesIO # Useful for StreamingResponse with bytes

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI()

# MQTT Broker Details (from .env or default)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "camera/feed") # Topic to subscribe to and publish to
MQTT_TOPIC_LLM = os.getenv("MQTT_TOPIC_LLM", "llm_response")

# Store the latest received image data
latest_image_payload: bytes | None = None
latest_image_media_type: str = "image/jpeg" # Default media type, can be updated from message
latest_llm_response: str | None = None # Store the latest LLM text response

client_id = f'python-mqtt-{random.randint(0, 1000)}'

# Initialize MQTT Client
# Use protocol version 5 for newer features if your broker supports it, otherwise use VERSION4
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)

# --- MQTT Callbacks ---

# Callback when the client connects to the MQTT broker
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the image topic after connecting
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")

        # Subscribe to the LLM response topic
        client.subscribe(MQTT_TOPIC_LLM)
        print(f"Subscribed to LLM response topic: {MQTT_TOPIC_LLM}")
    else:
        print(f"Failed to connect, return code {rc}\n")

# Callback when a message is received from the MQTT broker
def on_message(client, userdata, msg):
    # Handle messages from the image topic
    if msg.topic == MQTT_TOPIC:
        global latest_image_payload, latest_image_media_type
        print(f"Received message on topic {msg.topic}")
        try:
            # Assuming the payload is a JSON string containing base64 image data
            payload_str = msg.payload.decode('utf-8')
            message_data = json.loads(payload_str)

            if "image" in message_data:
                # Decode the base64 image string
                latest_image_payload = base64.b64decode(message_data["image"])
                print("Decoded image data received.")

                # Check if the message includes a media type
                if "type" in message_data:
                    latest_image_media_type = message_data["type"]
                    print(f"Image media type: {latest_image_media_type}")
                else:
                    # Reset to default if type is not provided
                    latest_image_media_type = "image/jpeg"
                    print(f"Image media type not provided, defaulting to: {latest_image_media_type}")


            else:
                print("Received message but no 'image' key found in payload.")
                # Optionally handle other types of messages here
                pass # Or handle messages without image data

        except json.JSONDecodeError:
            print("Failed to decode JSON payload.")
            # Handle non-JSON messages if necessary
        except base64.binascii.Error:
            print("Failed to decode base64 image data.")
        except Exception as e:
            print(f"An error occurred while processing message: {e}")
    elif msg.topic == MQTT_TOPIC_LLM:
        global latest_llm_response
        try:
            # Assuming the payload is a plain text string from the LLM service
            latest_llm_response = msg.payload.decode('utf-8')
            print("Received text response from LLM topic.")
            # print(f"LLM Response: {latest_llm_response}") # Uncomment for verbose output

        except Exception as e:
            print(f"An error occurred while processing message from LLM topic: {e}")

    # Handle messages from any other subscribed topics (optional)
    else:
        print(f"Received message on unhandled topic: {msg.topic}")

# Callback when message is published
def on_publish(client, userdata, mid):
    print(f"Message published with mid: {mid}")

# Set the callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_publish = on_publish

# --- FastAPI Events ---

@app.on_event("startup")
async def startup_event():
    # Connect to the MQTT Broker and start the loop
    # The on_connect callback will handle the subscription after successful connection
    print(f"Connecting to MQTT Broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
    mqtt_client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60) # Use connect_async to avoid blocking startup
    mqtt_client.loop_start() # Start the network loop in a background thread

@app.on_event("shutdown")
async def shutdown_event():
    # Stop the MQTT client loop and disconnect during shutdown
    print("Shutting down. Disconnecting MQTT client.")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("MQTT client disconnected.")

# --- FastAPI Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "API Gateway is up and running!"}

@app.post("/send_data/")
async def send_data(data: dict):
    """Send data to the MQTT broker (original functionality)"""

    try:
        # Convert the data dictionary to a JSON string
        payload = json.dumps(data)

        # Publish data to the MQTT broker
        result = mqtt_client.publish(MQTT_TOPIC, payload)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise HTTPException(status_code=500, detail="Failed to publish message to MQTT Broker")

        return {"message": "Data sent successfully", "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/")
async def get_status():
    """Endpoint to check the API Gateway status and MQTT connection"""
    # You could add more detailed MQTT status checks here if needed
    mqtt_connection_status = "Connected" if mqtt_client.is_connected() else "Disconnected"
    return {
        "status": "API Gateway is running",
        "mqtt_host": MQTT_BROKER_HOST,
        "mqtt_port": MQTT_BROKER_PORT,
        "mqtt_connection": mqtt_connection_status,
        "subscribed_topics": [MQTT_TOPIC, MQTT_TOPIC_LLM]
    }

@app.get("/latest_image/")
async def get_latest_image():
    """Endpoint to retrieve and display the latest received image"""
    global latest_image_payload, latest_image_media_type

    if latest_image_payload is None:
        raise HTTPException(status_code=404, detail="No image received yet.")

    # Return the image bytes using StreamingResponse
    # Use BytesIO to wrap the bytes data for StreamingResponse
    return StreamingResponse(BytesIO(latest_image_payload), media_type=latest_image_media_type)

@app.get("/latest_llm_insight/")
async def get_latest_llm_insight():
    """Endpoint to retrieve the latest received LLM text response"""
    global latest_llm_response

    if latest_llm_response is None:
        raise HTTPException(status_code=404, detail="No LLM insight received yet.")

    # Return the text response, perhaps wrapped in JSON
    return JSONResponse(content={"llm_insight": latest_llm_response})

@app.get("/latest/", response_class=HTMLResponse) # Specify response class as HTML
async def get_latest_combined_html_feed():
    """
    Endpoint to generate an HTML page displaying the latest image and LLM insight.
    """
    global latest_image_payload, latest_image_media_type, latest_llm_response

    # Start building the HTML response
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Latest Camera Feed and LLM Insight</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; }}
            img {{ max-width: 100%; height: auto; display: block; margin: 20px auto; border: 1px solid #ccc; }}
            .insight {{ margin-top: 20px; padding: 15px; border: 1px solid #eee; background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Latest Camera Feed and LLM Insight</h1>
    """

    if latest_image_payload is not None:
        # Encode image bytes to base64 for embedding in HTML
        try:
            base64_image_string = base64.b64encode(latest_image_payload).decode('utf-8')
            # Construct the image data URL
            img_src = f"data:{latest_image_media_type};base64,{base64_image_string}"
            html_content += f'<img src="{img_src}" alt="Latest Camera Image">'
        except Exception as e:
            print(f"Error encoding image to base64 for HTML: {e}")
            html_content += "<p style='color: red;'>Error displaying image.</p>"
    else:
        html_content += "<p>No image received yet.</p>"

    # Add the LLM insight
    html_content += "<div class='insight'><h2>LLM Insight:</h2>"
    if latest_llm_response is not None:
        # Escape HTML special characters in the LLM response to prevent issues
        # A simple way is replace < > & " '
        import html # Import the html module
        escaped_llm_response = html.escape(latest_llm_response)
        # Replace newlines with <br> for basic formatting in HTML
        formatted_llm_response = escaped_llm_response.replace('\n', '<br>')
        html_content += f"<p>{formatted_llm_response}</p>"
    else:
        html_content += "<p>No LLM insight received yet.</p>"
    html_content += "</div>" # Close insight div


    html_content += """
    </body>
    </html>
    """

    # Return the complete HTML content with the correct media type
    return HTMLResponse(content=html_content)

