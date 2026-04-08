# Dashboard V2 - Hardware Agent
# NOTE: This agent works best when run directly on the host machine
# to access accurate hardware stats. Running in a container limits
# access to GPU stats and may not reflect host system metrics accurately.

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash agent

# Copy application
COPY --chown=agent:agent agent.py .
COPY --chown=agent:agent .env.example .env.example

USER agent

# Environment variables (override with docker run -e)
ENV BACKEND_WS_URL=ws://backend:8000/hardware/ws/agent \
    HW_AGENT_TOKEN=change-me \
    INTERVAL=2

# Run the agent
CMD ["python", "agent.py"]
