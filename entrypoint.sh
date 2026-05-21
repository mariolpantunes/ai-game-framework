#!/bin/sh

# If a game requirements file is provided via volume, install it
if [ -f "/app/requirements.txt" ]; then
    echo "Installing game dependencies from /app/requirements.txt..."
    pip install --no-cache-dir -r /app/requirements.txt
fi

# Run the framework server
exec uvicorn framework.main:app --host 0.0.0.0 --port 8765
