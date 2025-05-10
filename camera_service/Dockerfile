### ⚙️ Dockerfile camera_service

# ⚙️ Dockerfile camera_service

FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set timezone non-interactively and install system dependencies
RUN ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    apt-get update && \
    apt-get install -y tzdata && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get install -y \
    python3 python3-pip python3-dev git curl v4l-utils \
    libopencv-dev python3-opencv ffmpeg \
    libglib2.0-0 libsm6 libxrender1 libxext6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run your app
CMD ["python3", "app.py"]


