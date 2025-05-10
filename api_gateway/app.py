from fastapi import FastAPI, HTTPException
import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import json
import random

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI()

# MQTT Broker Details (from .env or default)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "gateway/topic")

client_id = f'python-mqtt-{random.randint(0, 1000)}'

# Initialize MQTT Client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Callback when message is published
def on_publish(client, userdata, mid):
    print(f"Message published with mid: {mid}")

# Set the callback
mqtt_client.on_publish = on_publish

# Connect to the MQTT Broker
mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)

# Start the MQTT client loop
mqtt_client.loop_start()

@app.on_event("startup")
async def startup_event():
    # Make an initial connection to the MQTT broker
    mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)

@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect the MQTT client during shutdown
    mqtt_client.disconnect()

@app.get("/")
async def read_root():
    return {"message": "API Gateway is up and running!"}

@app.post("/send_data/")
async def send_data(data: dict):
    """Send data to the MQTT broker"""

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
    """Endpoint to check the API Gateway status"""
    return {"status": "API Gateway is running", "mqtt_host": MQTT_BROKER_HOST, "mqtt_port": MQTT_BROKER_PORT}
