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
PYTHON_EXEC="/usr/bin/python3"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Python 3.10 not found at $PYTHON_EXEC"
    echo "Trying to find it in PATH..."
    PYTHON_EXEC=$(which python3.10)
    if [ -z "$PYTHON_EXEC" ]; then
        echo "Error: python3.10 not found. Please install it."
        exit 1
    fi
fi

echo "Using Python: $PYTHON_EXEC"
# Uninstall legacy SDK if present to avoid confusion, install new SDK
$PYTHON_EXEC -m pip uninstall -y google-generativeai
$PYTHON_EXEC -m pip install -q google-genai uvicorn fastapi websockets

# 3. Run PoB (Gemini Native Version)
echo "Starting PoB with Gemini 3 Pro Preview..."
$PYTHON_EXEC app_gemini_ui_saved.py
