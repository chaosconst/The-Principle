#!/bin/bash

# 1. Source Environment Variables (API Keys)
if [ -f "env" ]; then
    echo "Loading environment variables from env..."
    # Manually export variables from env file
    while IFS='=' read -r key value; do
      if [[ ! $key =~ ^# && -n $key ]]; then
        export "$key=$value"
      fi
    done < env
fi

# 2. Check & Install Dependencies
echo "Checking dependencies..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

PYTHON_EXEC="./venv/bin/python"

echo "Using Python: $PYTHON_EXEC"
# Uninstall legacy SDK if present to avoid confusion, install new SDK
$PYTHON_EXEC -m pip uninstall -y google-generativeai
$PYTHON_EXEC -m pip install -r requirements.txt

# Debug: Check if API Key is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: GOOGLE_API_KEY is not set!"
else
    echo "GOOGLE_API_KEY is set (length: ${#GOOGLE_API_KEY})"
fi

# 3. Run PoB (Gemini Native Version)
echo "Starting PoB with Gemini 3 Pro Preview..."
$PYTHON_EXEC app.py
