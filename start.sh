#!/usr/bin/env bash

# Detect OS
OS_TYPE="$(uname -s)"

echo "Checking for Ollama..."

if [ "$OS_TYPE" = "Linux" ]; then
    # Check if inside Termux
    if [ -n "$TERMUX_VERSION" ]; then
        # Termux logic
        if ! command -v ollama &> /dev/null; then
            echo "Ollama not found in Termux. Please install it via the GitHub fork."
            exit 1
        fi
        pkill ollama
        ollama serve > /dev/null 2>&1 &
    else
        # Standard Linux
        sudo systemctl start ollama || ollama serve > /dev/null 2>&1 &
    fi
elif [ "$OS_TYPE" = "Darwin" ]; then
    # macOS - Ollama usually starts with the app
    echo "Ensuring Ollama is running on macOS..."
    open -a Ollama
else
    echo "Windows detected. Please ensure Ollama is running in your System Tray."
fi

# Wait for server
sleep 3

# Launch the agent
echo "Firing up the Codex Agent..."
python Agent.py
