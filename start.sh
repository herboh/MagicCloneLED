#!/bin/sh

# Start FastAPI backend in background
echo "Starting FastAPI backend..."
cd /app/backend && python3 main.py &
FASTAPI_PID=$!

# Start nginx in foreground
echo "Starting nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill $FASTAPI_PID $NGINX_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

echo "Services started. FastAPI PID: $FASTAPI_PID, Nginx PID: $NGINX_PID"

# Wait for processes
wait $NGINX_PID