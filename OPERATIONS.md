# Operations Guide - OpenClaw Dashboard

## Starting the Dashboard

### Recommended: Use the control script
```bash
./scripts/dashboard_ctl.sh start
```

### Alternative methods
```bash
# Using launcher script (finds available port)
./run_dashboard.sh

# Direct Python (Flask required)
python3 app.py

# Pure stdlib (no Flask needed, uses port 5001)
python3 app_stdlib.py
```

## Stopping the Dashboard

### Using control script
```bash
./scripts/dashboard_ctl.sh stop
```

### Manual methods
```bash
# Kill by process name
pkill -f "app.py"
pkill -f "app_stdlib.py"

# Or kill specific PID (from `ps aux | grep app`)
kill <PID>
```

## Restarting the Dashboard
```bash
./scripts/dashboard_ctl.sh restart
```

## Finding Active Port

The dashboard automatically searches ports 5001-5009 to avoid conflicts.

### Check which port is in use:
```bash
# Using lsof (macOS)
lsof -i :5001
lsof -i :5002
# ... etc

# Or check all dashboard ports at once
for port in 5001 5002 5003 5004 5005; do lsof -i :$port 2>/dev/null && echo "Port $port is active"; done
```

### From the control script:
```bash
./scripts/dashboard_ctl.sh status
```

## Health Check

### Via browser
Open `http://localhost:<PORT>/healthz` in your browser (replace `<PORT>` with actual port).

### Via curl
```bash
curl http://localhost:5001/healthz
# or check all ports
for port in 5001 5002 5003; do echo "=== Port $port ==="; curl -s http://localhost:$port/healthz; done
```

### Expected response
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-28T03:00:00.000000",
  "dataSources": {
    "openclaw_cli": true,
    "log_files": true,
    "sessions": true,
    "cron": true
  }
}
```

## Common Failure Fixes

### Port already in use (AirPlay on macOS)
```bash
# Find the process using port 5001
lsof -ti:5001

# Kill it
lsof -ti:5001 | xargs kill -9

# Or disable AirPlay Receiver (System Settings → AirDrop & Handoff)
```

### Stale dashboard instance
```bash
# Check for zombie processes
ps aux | grep "app.py"

# Force kill all instances
pkill -f "app.py"
pkill -f "app_stdlib.py"

# Wait 2 seconds, then restart
sleep 2 && ./run_dashboard.sh
```

### Flask not installed
```bash
# Install Flask
pip install flask

# Or use stdlib version (no Flask needed)
python3 app_stdlib.py
```

### No log entries found
- Ensure OpenClaw is running and generating logs
- Check logs exist: `ls -la /tmp/openclaw/`
- Logs should be named `openclaw-*.log`

### Dashboard starts but shows no data
1. Verify OpenClaw CLI works: `openclaw session list`
2. Check log files: `cat /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log`
3. Restart dashboard after OpenClaw generates new activity
