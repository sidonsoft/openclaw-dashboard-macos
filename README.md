# OpenClaw Dashboard for macOS

A local web dashboard for monitoring OpenClaw activity on macOS.

## Features

- 📊 Real-time activity monitoring from OpenClaw logs
- 📋 Task status tracking (TODO, Pending, Completed, Failed)
- ⏰ Cron job overview
- 🔄 Auto-refresh every 10 seconds
- 🎯 Filter chips for task status
- 🖥️ Native macOS-friendly dark theme

## Prerequisites

- Python 3.8+
- Flask (optional, falls back to stdlib if not installed)

## Installation

1. **Install Flask (recommended for better performance):**
   ```bash
   pip install flask
   ```
   
   Or run without Flask using Python's built-in http.server (limited functionality).

2. **Ensure OpenClaw is running** with logs in `/tmp/openclaw/`

## Running the Dashboard

### Option 1: Using the launcher script (recommended)
```bash
./run_dashboard.sh
```

### Option 2: Direct Python
```bash
python3 app.py
```

### Option 3: Without Flask (stdlib only)
```bash
python3 app_stdlib.py
```

## Access

Open your browser to: **http://localhost:5000**

## Troubleshooting

### "OpenClaw CLI not found"
- Ensure OpenClaw is installed and in your PATH
- Run `which openclaw` to verify

### "No log entries found"
- Check that OpenClaw is running and generating logs
- Logs should be in `/tmp/openclaw/openclaw-*.log`

### Port 5000 already in use
- Modify the port in `app.py`: `app.run(host='0.0.0.0', port=5001)`
- Or kill the existing process: `lsof -ti:5000 | xargs kill`

## Files

- `app.py` - Main Flask application
- `app_stdlib.py` - Pure stdlib version (no Flask needed)
- `run_dashboard.sh` - Launcher script
- `README.md` - This file

## Security Notes

- Dashboard runs locally on `localhost` only
- No authentication (local use only)
- Secrets are filtered from output
