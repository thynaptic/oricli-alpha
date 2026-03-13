# Base image with CUDA 11.8 and PyTorch
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Avoid interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies, including OpenSSH Server
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    openssh-server \
    rsync \
    curl \
    unzip \
    zstd \
    pciutils \
    mbuffer \
    ca-certificates \
    libgl1 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /var/run/sshd

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip -q awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip ./aws

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Pre-upgrade Python tooling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Set working directory
WORKDIR /workspace

# Copy only requirements-related files first to leverage Docker cache
COPY pyproject.toml .
RUN touch README.md

# Install oricli_core dependencies (train_neural and ml)
RUN pip install --no-cache-dir ".[train_neural,ml]"

# Copy our custom entrypoint and make it executable
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command (will be executed by the entrypoint)
CMD ["/bin/bash"]
