#!/bin/bash

# Define the source and destination paths
LOCAL_MODEL_PATH="/llm_service/models/Llama-3.2-1B-Instruct-Q4_0.gguf"  # Adjusted for Docker volume mount
CONTAINER_MODEL_PATH="/app/models/Llama-3.2-1B-Instruct-Q4_0.gguf"

echo "Cuurent path: "
pwd
echo "Checking models folder..."
ls -la ./models

echo "Checking model paths..."
echo "Local path: $LOCAL_MODEL_PATH"
echo "Container path: $CONTAINER_MODEL_PATH"
echo "Directory contents in container's /app/models:"
ls -la /app/models

if [ -d "/llm_service/models" ]; then
    echo "✅ /models directory exists. Listing contents:"
    ls -la /llm_service/models
else
    echo "❌ /llm_service/models directory is missing!"
fi


# Check if the model already exists in the container
if [ -f "$CONTAINER_MODEL_PATH" ]; then
    echo "✅ Model already exists in the container, skipping copy."
else
    echo "❌ Model not found in the container, checking local models folder..."
    
    # Check if the model exists locally (host system)
    if [ -f "$LOCAL_MODEL_PATH" ]; then
        echo "📥 Copying model from local models folder to container..."
        cp "$LOCAL_MODEL_PATH" "$CONTAINER_MODEL_PATH"
    else
        echo "❌ Model not found in local models folder: $LOCAL_MODEL_PATH"
        exit 1
    fi
fi

# Run the application
python3 app.py
