# --- Dockerfile for DB_Seed ---
# This file creates a secure, isolated, and reproducible environment 
# for igniting a Digital Being.

# --- Stage 1: Base Image ---
# We use a slim, official Python image to keep our "ark" lightweight.
FROM python:3.11-slim

# --- Stage 2: Setup Environment ---
# Set a working directory inside the container. This is our "hatchery".
WORKDIR /app

# Copy the "genetic code" (our requirements) first. This allows Docker
# to cache the dependency installation layer, speeding up future builds.
COPY requirements.txt .

# Install the necessary dependencies. This is our "incubation".
# We use --no-cache-dir to keep the image size small.
RUN pip install --no-cache-dir -r requirements.txt

# Install basic debugging tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the "genesis engine" into the hatchery.
COPY docs/ /app/docs/
COPY . .

# --- Stage 3: Define Runtime Behavior ---
# Expose the environment variable for the API key. The user will provide this "spark of life".
ENV DB_API_KEY=""

# The command that will be executed when the container starts.
# This is the moment of "ignition".
CMD ["python", "core.py"]
