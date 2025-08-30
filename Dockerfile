FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY dstack_cluster.py .
COPY signature_proof.py .

# Environment variables with defaults
ENV CONTRACT_ADDRESS=""
ENV CONNECTION_URL="http://localhost:8080"
ENV RPC_URL="http://host.docker.internal:8545"
ENV DSTACK_SOCKET="/app/simulator/dstack.sock"

# Create directory for dstack socket if needed
RUN mkdir -p /app/simulator

# Default command runs the demo
CMD ["python3", "dstack_cluster.py"]