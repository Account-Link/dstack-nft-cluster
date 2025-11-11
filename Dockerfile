# Use multi-platform base image
FROM --platform=$TARGETPLATFORM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

# Copy project configuration files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application files
COPY dstack_cluster.py .
COPY signature_proof.py .
COPY fastapi_server.py .

# Environment variables with defaults
ENV CONTRACT_ADDRESS=""
ENV CONNECTION_URL="http://localhost:8080"
ENV RPC_URL="http://host.docker.internal:8545"
ENV DSTACK_SOCKET="/app/simulator/dstack.sock"
ENV HOST="0.0.0.0"
ENV PORT="8080"

# Create directory for dstack socket if needed
RUN mkdir -p /app/simulator

# Expose the port
EXPOSE 8080

# Default command runs the FastAPI server using uv
CMD ["uv", "run", "python", "fastapi_server.py"]
