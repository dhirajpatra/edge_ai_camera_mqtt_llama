# Dockerfile for llm_service

# Dockerfile for llm_service

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git build-essential cmake wget ninja-build \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Clone llama-cpp-python into /llama
RUN git clone --recurse-submodules https://github.com/abetlen/llama-cpp-python.git /llama

WORKDIR /llama

RUN cmake . -B build && cmake --build build

RUN pip3 install .

ENV LLAMA_CPP_FLAGS="-DLLAMA_CUDA=OFF"

# Download the model
# Ensure the models directory exists before downloading
# Ensure the models directory exists and check if the model already exists before downloading
RUN mkdir -p /app/models && \
    if [ ! -f /app/models/Llama-3.2-1B-Instruct-Q4_0.gguf ]; then \
        wget -O /app/models/Llama-3.2-1B-Instruct-Q4_0.gguf \
        https://huggingface.co/mukel/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_0.gguf; \
    fi

WORKDIR /app

COPY requirements.txt /app/
COPY app.py /app/
COPY init.sh /app/
RUN chmod +x /app/init.sh
RUN pip3 install -r /app/requirements.txt

CMD ["./init.sh"]
