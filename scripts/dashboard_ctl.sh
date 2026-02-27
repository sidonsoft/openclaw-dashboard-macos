#!/bin/bash
# dashboard_ctl.sh - Control script for OpenClaw Dashboard
# macOS-friendly, safe operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_PY="$PROJECT_DIR/app.py"
APP_STDIB="$PROJECT_DIR/app_stdlib.py"
LOG_FILE="$PROJECT_DIR/dashboard_ctl.log"

# Default port range (macOS avoids 5000 for AirPlay)
PORTS=(5001 5002 5003 5004 5005)

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
    for port in "${PORTS[@]}"; do
        if ! lsof -i :$port &>/dev/null; then
            echo "$port"
            return 0
        fi
    done
    log "ERROR: No available ports in range ${PORTS[*]}" >&2
    return 1
}

check_process() {
    pgrep -f "python3.*app\.py|python3.*app_stdlib\.py" >/dev/null 2>&1
}

get_pid() {
    pgrep -f "python3.*app\.py|python3.*app_stdlib\.py" | head -1
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
    
    local port=$(find_available_port) || exit 1
    log "Found available port: $port"
    
    # Start in background, redirect output to log file
    cd "$PROJECT_DIR"
    python3 app_stdlib.py > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "${PROJECT_DIR}/dashboard.pid"
    
    log "Dashboard started with PID $pid on port $port"
    echo "Dashboard started!"
    echo "  PID: $pid"
    echo "  Port: $port"
    echo "  URL: http://localhost:$port"
    echo "  Log: $LOG_FILE"
    
    # Wait for service to be ready (up to 10 seconds)
    local retries=10
    while [ $retries -gt 0 ]; do
        if curl -s --max-time 2 "http://localhost:$port/healthz" >/dev/null 2>&1; then
            echo "Dashboard is healthy!"
            return 0
        fi
        sleep 1
        retries=$((retries - 1))
    done
    
    log "WARNING: Dashboard may not be ready yet, check $LOG_FILE" >&2
    echo "Warning: Service startup delay, check log file for details"
    return 0
}

cmd_stop() {
    log "Stopping dashboard..."
    
    if ! check_process; then
        log "No dashboard process running"
        echo "Dashboard is not running."
        exit 0
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
        pkill -9 -f "python3.*app\.py|python3.*app_stdlib\.py" || true
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
            if lsof -i :$port &>/dev/null; then
                echo "Active port: $port"
                
                # Check health status
                local health=$(curl -s --max-time 2 "http://localhost:$port/healthz" 2>/dev/null)
                if [ -n "$health" ]; then
                    echo "Health: OK"
                    echo "Details: $health" | python3 -m json.tool 2>/dev/null || echo "$health"
                else
                    echo "Health: Unable to check (service may be starting)"
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
