# 🧠 Edge AI Microservice with LLaMA 3.2 1B (Quantized) using `llama.cpp`

This project sets up a microservice architecture where a camera detection service sends object detection events to an LLM service that replies intelligently using a quantized LLaMA 3.2 1B model powered by [`llama.cpp`](https://github.com/ggerganov/llama.cpp). Communication is via MQTT.

You may need to run following command in your system. To get the video url and update into the docker-compose.

`ls /dev/video*`
`sudo usermod -aG video $USER`


---

## 🖥️ System 1: Laptop (Intel i5 + 32GB RAM)

### ✅ Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Download LLaMA 3.2 1B quantized model (e.g. `bartowski/Llama-3.2-1B-Instruct-GGUF` from TheBloke or convert yourself)
- MQTT broker (e.g., Mosquitto)

### 📁 Folder Structure

```

llm\_service/
├── app.py
├── Dockerfile
├── requirements.txt
└── models/
└── llama-3-1b-q4\_0.gguf

````

### 🧪 Run Locally

```bash
docker build -t llm_service .
docker run -v $(pwd)/models:/app/models -p 1883:1883 llm_service
```

---

## 🍓 System 2: Raspberry Pi 4 (4GB or 8GB RAM)

### ✅ Prerequisites

* Raspberry Pi OS 64-bit
* Docker & Docker Compose
* Dockerfile will automatically download same `bartowski/Llama-3.2-1B-Instruct-GGUF` model
* Optional: Mosquitto installed for local MQTT broker

### ⚙️ Build for ARM64

If building on a different architecture (e.g. x86):

```bash
docker buildx build --platform linux/arm64 -t llm_service .
```

Or build directly on Raspberry Pi:

```bash
docker build -t llm_service .
```

### 🏃 Run

```bash
docker run -v $(pwd)/models:/app/models --network host llm_service
```

> Use `--network host` on Raspberry Pi if running Mosquitto locally.

---

## 📡 MQTT Topics

* `detections`: input topic for camera\_service object detection
* `llm_response`: output topic where LLM replies are published

---

## 📥 Download Prebuilt Models (Optional)

You can download quantized models from:

* [TheBloke's HuggingFace Repo](https://huggingface.co/TheBloke)
* Choose: `bartowski/Llama-3.2-1B-Instruct-GGUF`

Place the `.gguf` file in `llm_service/models/`.

---

## 📌 Notes

* `n_threads` can be set to `2` or `4` on Raspberry Pi for better performance.
* On Pi 4, total memory usage will be \~1.7–2.2 GB (use swap if needed).
* Use minimal prompt and small context size (≤512) to reduce latency.

---

## 🧩 Coming Soon

* `camera_service/` (TensorFlow/OpenVINO object detection)
* UI Dashboard (Optional)
* Logging and metrics

---

## 🤝 Contribution

We welcome contributions! Please follow these guidelines:

- Fork the repository and create a new branch (`feature/your-feature-name`)
- Follow existing coding conventions and directory structure
- Write clear commit messages
- Test your code before pushing
- Submit a Pull Request with a clear description of changes

For major changes, please open an issue first to discuss what you would like to change.

---
