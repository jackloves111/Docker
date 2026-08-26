#!/bin/sh
set -e

# Create necessary directories
mkdir -p /config /tmp/dockerpilot/downloads /tmp/dockerpilot/compose

# Start the application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
