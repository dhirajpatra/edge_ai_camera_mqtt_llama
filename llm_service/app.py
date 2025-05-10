import os
from llama_cpp import Llama
import paho.mqtt.client as mqtt
import json
from dotenv import load_dotenv
import random

load_dotenv()

model_path = os.getenv("MODEL_PATH")
model_name = os.getenv("MODEL_NAME")
n_ctx = int(os.getenv("LLM_CONTEXT_SIZE", 512))
max_tokens = int(os.getenv("LLM_MAX_TOKENS", 64))
n_threads = int(os.getenv("LLM_THREADS", 4))

mqtt_host = os.getenv("MQTT_HOST", "mqtt_broker")
mqtt_port = int(os.getenv("MQTT_PORT", 1883))
mqtt_topic_in = os.getenv("MQTT_TOPIC_IN", "detections")
mqtt_topic_out = os.getenv("MQTT_TOPIC_OUT", "llm_response")

client_id = f'python-mqtt-{random.randint(0, 1000)}'

llm = Llama(
    model_path=model_path,
    n_ctx=n_ctx,
    n_threads=n_threads,
    use_mlock=True
)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    prompt = f"Detected: {data['object']} with {data['confidence']:.2f} confidence. What should be done?"
    output = llm(prompt, max_tokens=max_tokens)
    reply = output["choices"][0]["text"]
    mqtt_client.publish(mqtt_topic_out, reply)

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_host, mqtt_port)
mqtt_client.subscribe(mqtt_topic_in)
mqtt_client.loop_forever()
