#!/bin/bash

# 1. Source Environment Variables (API Keys)
if [ -f "../../env" ]; then
    echo "Loading environment variables from ../../env..."
    set -a
    source "../../env"
    set +a
elif [ -f "env" ]; then
    echo "Loading environment variables from env..."
    set -a
    source "env"
    set +a
elif [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -a
    source ".env"
    set +a
fi

# 2. Check & Install Dependencies
echo "Checking dependencies..."
# Use explicit python path to ensure pip and python match
PYTHON_EXEC="python"

echo "Using Python: $PYTHON_EXEC"
# Uninstall legacy SDK if present to avoid confusion, install new SDK
$PYTHON_EXEC -m pip uninstall -y google-generativeai
$PYTHON_EXEC -m pip install -r requirements.txt

# 3. Run PoB (Gemini Native Version)
echo "Starting PoB with Gemini 3 Pro Preview..."
$PYTHON_EXEC app.py
