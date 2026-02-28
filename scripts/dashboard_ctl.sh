#!/bin/bash
# dashboard_ctl.sh - Control script for OpenClaw Dashboard
# macOS-friendly, safe operations

set -e

LSOF_BIN="/usr/sbin/lsof"
if [ ! -x "$LSOF_BIN" ]; then
  LSOF_BIN="$(command -v lsof || true)"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_PY="$PROJECT_DIR/app.py"
APP_STDIB="$PROJECT_DIR/app_stdlib.py"
LOG_FILE="$PROJECT_DIR/dashboard_ctl.log"
SERVER_LOG="$PROJECT_DIR/dashboard_server.log"

# Default port range (macOS avoids 5000 for AirPlay)
PORTS=(5001 5002 5003 5004 5005 5006 5007 5008 5009 5010 5011 5012)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

usage() {
    cat << EOF
Usage: dashboard_ctl.sh <command>

Commands:
  start   - Start the dashboard (finds available port)
  stop    - Stop any running dashboard instance
  restart - Restart the dashboard
  status  - Show current dashboard status and active port
  health  - Check /healthz endpoint on all possible ports

Options:
  -v, --verbose   Enable verbose output
EOF
}

find_available_port() {
    python3 - <<'PY'
import socket
for p in range(5001, 5013):
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', p))
        print(p)
        s.close()
        raise SystemExit(0)
    except OSError:
        s.close()
print('')
raise SystemExit(1)
PY
}

check_process() {
    pgrep -f "openclaw-dashboard-macos/.*/app\.py|openclaw-dashboard-macos/.*/app_stdlib\.py|python3 app\.py|python3 app_stdlib\.py|Python app\.py|Python app_stdlib\.py" >/dev/null 2>&1
}

get_pid() {
    pgrep -f "openclaw-dashboard-macos/.*/app\.py|openclaw-dashboard-macos/.*/app_stdlib\.py|python3 app\.py|python3 app_stdlib\.py|Python app\.py|Python app_stdlib\.py" | head -1
}

check_health() {
    local port=$1
    if curl -s --max-time 2 "http://localhost:$port/healthz" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

cmd_start() {
    log "Starting dashboard..."
    
    if check_process; then
        local pid=$(get_pid)
        log "WARNING: Dashboard already running (PID $pid)" >&2
        echo "Dashboard is already running on PID $pid"
        exit 0
    fi
    
    # Start in background (use Flask app.py), keep server logs separate
    cd "$PROJECT_DIR"
    nohup python3 app.py >> "$SERVER_LOG" 2>&1 &
    local pid=$!
    echo "$pid" > "${PROJECT_DIR}/dashboard.pid"

    # Wait for service to be ready and discover port from /healthz
    local retries=15
    local active_port=""
    while [ $retries -gt 0 ]; do
        for p in "${PORTS[@]}"; do
            if curl -s --max-time 1 "http://localhost:$p/healthz" >/dev/null 2>&1; then
                active_port="$p"
                break
            fi
        done
        if [ -n "$active_port" ]; then
            break
        fi
        sleep 1
        retries=$((retries - 1))
    done

    log "Dashboard started with PID $pid${active_port:+ on port $active_port}"
    echo "Dashboard started!"
    echo "  PID: $pid"
    if [ -n "$active_port" ]; then
        echo "  Port: $active_port"
        echo "  URL: http://localhost:$active_port"
        echo "Dashboard is healthy!"
        return 0
    fi

    echo "  Port: unknown (still starting)"
    echo "  Log: $SERVER_LOG"
    log "WARNING: Dashboard may not be ready yet, check $SERVER_LOG" >&2
    return 0
}

cmd_stop() {
    log "Stopping dashboard..."
    
    if ! check_process; then
        log "No dashboard process running"
        echo "Dashboard is not running."
        return 0
    fi
    
    local pid=$(get_pid)
    log "Killing process $pid"
    kill "$pid" 2>/dev/null || true
    
    # Wait for process to die (up to 5 seconds)
    local retries=5
    while [ $retries -gt 0 ] && check_process; do
        sleep 1
        retries=$((retries - 1))
    done
    
    if check_process; then
        log "Force killing remaining process" >&2
        pkill -9 -f "app\.py" || true
        pkill -9 -f "app_stdlib\.py" || true
    fi
    
    # Clean up PID file
    rm -f "${PROJECT_DIR}/dashboard.pid"
    
    log "Dashboard stopped."
    echo "Dashboard stopped."
}

cmd_restart() {
    log "Restarting dashboard..."
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    if check_process; then
        local pid=$(get_pid)
        echo "Dashboard is running (PID: $pid)"
        
        # Try to find which port it's using
        for port in "${PORTS[@]}"; do
            if check_health "$port"; then
                echo "Active port: $port"
                local health=$(curl -s --max-time 2 "http://localhost:$port/healthz" 2>/dev/null)
                if [ -n "$health" ]; then
                    echo "Health: OK"
                    echo "Details: $health" | python3 -m json.tool 2>/dev/null || echo "$health"
                fi
                return 0
            fi
        done
        
        echo "Warning: Process running but no port detected in expected range"
        return 1
    else
        echo "Dashboard is not running."
        
        # Check for stale PID file
        if [ -f "${PROJECT_DIR}/dashboard.pid" ]; then
            local stale_pid=$(cat "${PROJECT_DIR}/dashboard.pid")
            log "WARNING: Found stale PID file with $stale_pid" >&2
            echo "Note: Stale PID file found (may be from crashed process)"
        fi
        
        return 1
    fi
}

cmd_health() {
    local all_ok=true
    
    for port in "${PORTS[@]}"; do
        if check_health "$port"; then
            echo "Port $port: OK"
            curl -s "http://localhost:$port/healthz" | python3 -m json.tool 2>/dev/null || true
        else
            echo "Port $port: Not responding or not running"
            all_ok=false
        fi
    done
    
    if [ "$all_ok" = false ]; then
        return 1
    fi
}

# Main command dispatcher
case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    health)
        cmd_health
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown command: $1" >&2
        usage
        exit 1
        ;;
esac
