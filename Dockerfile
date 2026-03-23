# Base image
FROM fedora:latest

# Metadata
LABEL maintainer="Oracle NBA Team"
LABEL description="Environment for NBA Predictive Model development"

# Install system dependencies
RUN dnf -y update && dnf -y install \
    python3.11 \
    python3-pip \
    gcc \
    gcc-c++ \
    make \
    git \
    && dnf clean all

# Set working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy project structure
COPY . .

# Default command
CMD ["python3"]
