#!/usr/bin/env python3
"""
OpenClaw Activity Dashboard
A local web dashboard for monitoring OpenClaw activity on macOS.
"""

import os
import glob
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Configuration
LOG_DIR = "/tmp/openclaw"
REFRESH_INTERVAL = 10  # seconds

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #e0e0e0; min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 1.8rem; color: #7c3aed; }
        .refresh-btn { background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: background 0.2s; }
        .refresh-btn:hover { background: #6d28d9; }
        .refresh-btn.loading { opacity: 0.7; pointer-events: none; }
        
        .counters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .counter { background: #2d2d2d; padding: 20px; border-radius: 12px; text-align: center; }
        .counter-value { font-size: 2.5rem; font-weight: bold; }
        .counter-label { font-size: 0.9rem; color: #9ca3af; margin-top: 5px; }
        .counter.pending .counter-value { color: #f59e0b; }
        .counter.completed .counter-value { color: #10b981; }
        .counter.failed .counter-value { color: #ef4444; }
        .counter.todo .counter-value { color: #3b82f6; }
        
        .filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter-chip { background: #2d2d2d; border: 1px solid #404040; color: #9ca3af; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
        .filter-chip:hover { border-color: #7c3aed; color: #e0e0e0; }
        .filter-chip.active { background: #7c3aed; border-color: #7c3aed; color: white; }
        
        .panel { background: #2d2d2d; border-radius: 12px; margin-bottom: 20px; overflow: hidden; }
        .panel-header { background: #363636; padding: 15px 20px; font-weight: 600; font-size: 1rem; display: flex; justify-content: space-between; align-items: center; }
        .panel-content { padding: 15px 20px; max-height: 300px; overflow-y: auto; }
        
        .log-line { font-family: 'SF Mono', Monaco, monospace; font-size: 12px; padding: 6px 0; border-bottom: 1px solid #3d3d3d; }
        .log-line:last-child { border-bottom: none; }
        .log-time { color: #6b7280; margin-right: 10px; }
        
        .task-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #3d3d3d; }
        .task-item:last-child { border-bottom: none; }
        .task-name { font-weight: 500; }
        .task-status { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }
        .task-status.pending { background: #f59e0b20; color: #f59e0b; }
        .task-status.completed { background: #10b98120; color: #10b981; }
        .task-status.failed { background: #ef444420; color: #ef4444; }
        .task-status.todo { background: #3b82f620; color: #3b82f6; }
        
        .warning { background: #f59e0b20; border: 1px solid #f59e0b; color: #f59e0b; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        
        .empty-state { color: #6b7280; font-style: italic; padding: 20px; text-align: center; }
        
        .auto-refresh { font-size: 12px; color: #6b7280; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖥️ OpenClaw Dashboard</h1>
            <div>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
                <span class="auto-refresh">Auto-refresh: {{ refresh_interval }}s</span>
            </div>
        </header>
        
        {% if warning %}
        <div class="warning">{{ warning }}</div>
        {% endif %}
        
        <div class="counters">
            <div class="counter pending">
                <div class="counter-value">{{ stats.pending }}</div>
                <div class="counter-label">Pending</div>
            </div>
            <div class="counter completed">
                <div class="counter-value">{{ stats.completed }}</div>
                <div class="counter-label">Completed</div>
            </div>
            <div class="counter failed">
                <div class="counter-value">{{ stats.failed }}</div>
                <div class="counter-label">Failed</div>
            </div>
            <div class="counter todo">
                <div class="counter-value">{{ stats.todo }}</div>
                <div class="counter-label">TODO</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-chip active" data-filter="all" onclick="setFilter('all')">All</button>
            <button class="filter-chip" data-filter="pending" onclick="setFilter('pending')">Pending</button>
            <button class="filter-chip" data-filter="completed" onclick="setFilter('completed')">Completed</button>
            <button class="filter-chip" data-filter="failed" onclick="setFilter('failed')">Failed</button>
            <button class="filter-chip" data-filter="todo" onclick="setFilter('todo')">TODO</button>
        </div>
        
        <div class="panel">
            <div class="panel-header">
                <span>📋 Tasks</span>
                <span style="font-weight: normal; font-size: 13px; color: #9ca3af;">{{ tasks|length }} items</span>
            </div>
            <div class="panel-content">
                {% if tasks %}
                    {% for task in tasks %}
                    <div class="task-item" data-status="{{ task.status }}">
                        <span class="task-name">{{ task.name }}</span>
                        <span class="task-status {{ task.status }}">{{ task.status }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">No tasks found</div>
                {% endif %}
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">
                <span>📝 Recent Activity</span>
                <span style="font-weight: normal; font-size: 13px; color: #9ca3af;">{{ logs|length }} lines</span>
            </div>
            <div class="panel-content">
                {% if logs %}
                    {% for log in logs %}
                    <div class="log-line">
                        <span class="log-time">{{ log.time }}</span>
                        <span>{{ log.message }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">No log entries found</div>
                {% endif %}
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">
                <span>⏰ Cron Jobs</span>
                <span style="font-weight: normal; font-size: 13px; color: #9ca3af;">{{ cron_jobs|length }} jobs</span>
            </div>
            <div class="panel-content">
                {% if cron_jobs %}
                    {% for job in cron_jobs %}
                    <div class="task-item">
                        <span class="task-name">{{ job.name }}</span>
                        <span class="task-status todo">{{ job.schedule }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">No cron jobs configured</div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <script>
        let currentFilter = 'all';
        
        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-chip').forEach(chip => {
                chip.classList.toggle('active', chip.dataset.filter === filter);
            });
            
            document.querySelectorAll('.task-item').forEach(item => {
                if (filter === 'all' || item.dataset.status === filter) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        }
        
        function refreshData() {
            const btn = document.querySelector('.refresh-btn');
            btn.classList.add('loading');
            btn.textContent = '⏳ Refreshing...';
            
            fetch('/api/data')
                .then(res => res.json())
                .then(data => {
                    location.reload();
                })
                .catch(err => {
                    console.error('Refresh failed:', err);
                    btn.classList.remove('loading');
                    btn.textContent = '🔄 Refresh';
                });
        }
        
        // Auto-refresh
        setInterval(() => {
            refreshData();
        }, {{ refresh_interval }} * 1000);
    </script>
</body>
</html>
"""


def get_openclaw_logs():
    """Parse recent OpenClaw logs."""
    logs = []
    log_pattern = os.path.join(LOG_DIR, "openclaw-*.log")
    
    try:
        log_files = glob.glob(log_pattern)
        if not log_files:
            return []
        
        # Get most recent log file
        latest_log = max(log_files, key=os.path.getmtime)
        
        # Read last 100 lines
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines[-100:]:
            line = line.strip()
            if line:
                # Extract timestamp if present
                parts = line.split(']', 1)
                if len(parts) > 1:
                    time_part = parts[0].strip('[')
                    message = parts[1].strip()
                else:
                    time_part = ''
                    message = line
                logs.append({'time': time_part, 'message': message})
        
        return logs[-50:]  # Return last 50 entries
    
    except FileNotFoundError:
        return []
    except Exception as e:
        return [{'time': '', 'message': f'Error reading logs: {str(e)}'}]


def get_subagents_list():
    """Parse subagent/task states from subagents list command."""
    try:
        result = subprocess.run(
            ['openclaw', 'subagents', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return [], f"Command failed: {result.stderr.strip()}"
        
        tasks = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Session') or line.startswith('-'):
                continue
            
            # Parse task lines - format varies but look for status indicators
            if any(status in line.lower() for status in ['pending', 'running', 'completed', 'failed', 'todo']):
                parts = line.split()
                if len(parts) >= 2:
                    # Try to extract status
                    status = 'pending'
                    if 'completed' in line.lower():
                        status = 'completed'
                    elif 'failed' in line.lower():
                        status = 'failed'
                    elif 'todo' in line.lower():
                        status = 'todo'
                    elif 'running' in line.lower():
                        status = 'pending'
                    
                    # Use line as task name
                    tasks.append({
                        'name': line[:80] + ('...' if len(line) > 80 else ''),
                        'status': status
                    })
        
        return tasks, None
    
    except FileNotFoundError:
        return [], "OpenClaw CLI not found. Is OpenClaw installed?"
    except subprocess.TimeoutExpired:
        return [], "Command timed out"
    except Exception as e:
        return [], f"Error: {str(e)}"


def get_cron_jobs():
    """Parse cron jobs from openclaw cron list."""
    try:
        result = subprocess.run(
            ['openclaw', 'cron', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return []  # Graceful fallback
        
        jobs = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Job') or line.startswith('-'):
                continue
            if '-----' in line:
                continue
            
            # Simple parsing - use line as job info
            jobs.append({
                'name': line[:60] + ('...' if len(line) > 60 else ''),
                'schedule': 'scheduled'
            })
        
        return jobs[:10]  # Limit to 10
    
    except Exception:
        return []  # Graceful fallback


def calculate_stats(tasks):
    """Calculate status counters."""
    stats = {
        'pending': 0,
        'completed': 0,
        'failed': 0,
        'todo': 0
    }
    
    for task in tasks:
        status = task.get('status', 'pending').lower()
        if status in stats:
            stats[status] += 1
    
    return stats


@app.route('/')
def index():
    """Main dashboard page."""
    logs = get_openclaw_logs()
    tasks, warning = get_subagents_list()
    cron_jobs = get_cron_jobs()
    stats = calculate_stats(tasks)
    
    return render_template_string(
        HTML_TEMPLATE,
        logs=logs,
        tasks=tasks,
        cron_jobs=cron_jobs,
        stats=stats,
        warning=warning,
        refresh_interval=REFRESH_INTERVAL
    )


@app.route('/api/data')
def api_data():
    """JSON API for auto-refresh."""
    logs = get_openclaw_logs()
    tasks, _ = get_subagents_list()
    cron_jobs = get_cron_jobs()
    stats = calculate_stats(tasks)
    
    return jsonify({
        'logs': logs,
        'tasks': tasks,
        'cron_jobs': cron_jobs,
        'stats': stats
    })


if __name__ == '__main__':
    import socket
    
    def find_free_port(start_port=5000, max_attempts=10):
        """Find a free port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        return start_port
    
    port = find_free_port()
    
    print("🚀 Starting OpenClaw Dashboard...")
    print(f"📍 Open http://localhost:{port} in your browser")
    if port != 5000:
        print(f"⚠️  Port 5000 was in use, using port {port} instead")
    app.run(host='0.0.0.0', port=port, debug=False)
