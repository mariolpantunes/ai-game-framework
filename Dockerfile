FROM python:3.14-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include framework and game logic
ENV PYTHONPATH="/app:/app/framework:/app/game"

# Expose the WebSocket/API port
EXPOSE 8765

# The framework and game logic are mounted as volumes
# Framework -> /app/framework
# Game -> /app/game

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
