# Troubleshooting Guide - OpenClaw Dashboard

## Quick Decision Tree

```
Dashboard not working?
│
├─ Blank page (loads but empty)
│  ├─ Check console (F12): CORS errors? → Flask version required, use `python3 app.py`
│  ├─ No data shown: /api/data returns empty? → OpenClaw not running or no logs yet
│  └─ Spinner forever: API endpoint down → Check `/healthz`, verify port correct
│
├─ Stale data (old info, not updating)
│  ├─ Auto-refresh broken? → Browser cache: hard refresh (Cmd+Shift+R / Ctrl+F5)
│  ├─ Data hasn't changed in 10s? → OpenClaw idle or stopped
│  └─ Wrong time range? → Check log file timestamps match expected date
│
├─ Bad task parsing (garbled output, missing fields)
│  ├─ Log format changed? → Dashboard may need update, check GitHub for latest
│  ├─ Task names truncated? → CSS width issue: F12 inspect, increase `.task-name` width
│  └─ Status colors wrong? → Regex pattern mismatch, verify task status keywords in logs
│
└─ API errors (/api/data fails)
   ├─ 500 error: Check server terminal for traceback
   │  ├─ "No log files found": OpenClaw not generating logs yet
   │  ├─ "JSON parse error": Log file corrupted, check disk space
   │  └─ Permission denied: Run dashboard as user with read access to /tmp/openclaw/
   │
   ├─ 503 error (service unavailable): Flask crashed or port mismatch
   │  → Restart dashboard: `./scripts/dashboard_ctl.sh restart`
   │
   └─ Connection refused: Wrong port?
      → Check active port: `lsof -i :5001`, adjust URL accordingly
```

## Detailed Issues

### Blank Page

**Symptoms:** Browser loads, shows dashboard UI but no data, counters show 0.

**Causes & Fixes:**

| Cause | How to Verify | Fix |
|-------|---------------|-----|
| No OpenClaw logs yet | `ls -la /tmp/openclaw/` empty or old | Start OpenClaw, wait for new log entries |
| Wrong date in filename | Logs named `openclaw-2026-02-27.log` but today is 28th | Dashboard reads current day's log by default |
| CORS blocked (browser console errors) | F12 → Console tab shows CORS errors | Use Flask version: `python3 app.py` not stdlib |
| API endpoint wrong URL | `/api/data` returns 404 | Check port, ensure dashboard actually running |

### Stale Data

**Symptoms:** Dashboard loads with data but doesn't update every 10 seconds.

**Causes & Fixes:**

| Cause | How to Verify | Fix |
|-------|---------------|-----|
| Browser caching | Hard refresh shows same old data | Cmd+Shift+R (Mac) or Ctrl+F5 (Windows) |
| JavaScript error in console | F12 → Console tab has errors | Check for script load failures, update dashboard |
| OpenClaw idle | No new log entries since last check | Activity required to refresh counters |
| Refresh interval changed | Inspect `REFRESH_INTERVAL` in app.py | Default is 10s, can be increased if needed |

### Bad Task Parsing

**Symptoms:** Tasks show as "Unknown", truncated names, wrong status colors.

**Causes & Fixes:**

| Cause | How to Verify | Fix |
|-------|---------------|-----|
| Log format changed | Check `/tmp/openclaw/` log content structure | Update dashboard regex patterns in app.py |
| Custom task names | Tasks with non-standard keywords | Add custom status mappings in dashboard config |
| Unicode/special chars | Task names display as boxes or garbled | Ensure UTF-8 encoding, check browser font support |

### API Errors (/api/data fails)

**Symptoms:** Network tab shows failed request, console shows error.

**Causes & Fixes:**

| Cause | How to Verify | Fix |
|-------|---------------|-----|
| Flask crashed | Server terminal shows traceback | Restart: `./scripts/dashboard_ctl.sh restart` |
| Port mismatch | URL uses 5001 but app runs on 5002 | Check startup message for correct port |
| Permission denied | Terminal shows "PermissionError" | Run as user with read access to log directory |
| Disk full | `df -h /tmp` shows 100% usage | Free disk space, logs can grow large |

## Emergency Recovery

If dashboard is completely broken:

```bash
# 1. Kill any zombie instances
pkill -f "app.py"
pkill -f "app_stdlib.py"

# 2. Clear potential stale locks
rm -f /tmp/openclaw-dashboard.lock

# 3. Verify dependencies
python3 -c "import flask; print('Flask OK')" || pip install flask

# 4. Check OpenClaw is running
openclaw session list

# 5. Restart fresh
./run_dashboard.sh
```

## Getting Help

1. Check `/healthz` endpoint for data source status
2. Review server terminal output for errors
3. Inspect browser console (F12) for client-side issues
4. Verify log files exist and are readable: `ls -la /tmp/openclaw/*.log`
