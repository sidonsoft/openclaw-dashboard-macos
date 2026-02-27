#!/bin/bash
#
# OpenClaw Dashboard Launcher
# Starts the local web dashboard for monitoring OpenClaw activity
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting OpenClaw Dashboard..."

# Check for Flask, install if missing
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip install flask
fi

# Start the dashboard
echo "🌐 Opening http://localhost:5000"
python3 app.py
