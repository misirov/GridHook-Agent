# Use Ubuntu as base image
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry
RUN curl -L https://foundry.paradigm.xyz | bash
RUN /root/.foundry/bin/foundryup

# Install Rye
RUN curl -sSf https://rye-up.com/get | bash
ENV PATH="/root/.rye/shims:${PATH}"

# Set up working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies using Rye
WORKDIR /app/agent
RUN rye sync
RUN . .venv/bin/activate

# Copy startup script
WORKDIR /app
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

# Add Foundry binaries to PATH
ENV PATH="/root/.foundry/bin:${PATH}"

# Default command
ENTRYPOINT ["/startup.sh"]