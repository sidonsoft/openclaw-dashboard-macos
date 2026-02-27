# OpenClaw Dashboard for macOS

A local web dashboard for monitoring OpenClaw activity on macOS.

## Features

- 📊 Real-time activity monitoring from OpenClaw logs
- 📋 Task status tracking (TODO, Pending, Completed, Failed)
- ⏰ Cron job overview
- 🔄 Auto-refresh every 10 seconds
- 🎯 Filter chips for task status
- 🖥️ Native macOS-friendly dark theme
- 🔮 Codex Usage panel (Windows quotas, account info)
- 🦞 OpenClaw Session Usage panel (active sessions, token usage)

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

## Health Check

Both dashboard versions include a `/healthz` endpoint for monitoring:

```bash
# Check health status (returns JSON)
curl http://localhost:5000/healthz
```

Example response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-28T02:30:00.000000",
  "dataSources": {
    "openclaw_cli": true,
    "log_files": true,
    "sessions": true,
    "cron": true
  }
}
```

## Startup Diagnostics

On launch, both apps print diagnostics showing which data sources are available:

```
🚀 Starting OpenClaw Dashboard...

📊 Startup Diagnostics:
  ✅ OpenClaw CLI
  ✅ Log files in /tmp/openclaw
  ✅ Sessions API
  ✅ Cron API

📍 Open http://localhost:5001 in your browser
```

If any source is unavailable (❌), check the troubleshooting section.

## Troubleshooting

### "OpenClaw CLI not found"
- Ensure OpenClaw is installed and in your PATH
- Run `which openclaw` to verify

### "No log entries found"
- Check that OpenClaw is running and generating logs
- Logs should be in `/tmp/openclaw/openclaw-*.log`

### "Port 5000 already in use" (macOS)
- On macOS, AirPlay Receiver often uses port 5000
- The dashboard now automatically finds an available port (5001-5009)
- If you want to use a specific port, modify `app.py`: `app.run(port=5001)`
- Or disable AirPlay Receiver in System Settings → AirDrop & Handoff

### To kill process on port 5000:
```bash
lsof -ti:5000 | xargs kill -9
```

## Files

- `app.py` - Main Flask application
- `app_stdlib.py` - Pure stdlib version (no Flask needed)
- `run_dashboard.sh` - Launcher script
- `README.md` - This file

## Security Notes

- Dashboard runs locally on `localhost` only
- No authentication (local use only)
- Secrets are filtered from output
