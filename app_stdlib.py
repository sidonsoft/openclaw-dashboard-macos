#!/usr/bin/env python3
"""
OpenClaw Activity Dashboard - Stdlib Version
A local web dashboard for monitoring OpenClaw activity on macOS.
Requires no external dependencies.
"""

import os
import glob
import subprocess
import json
import http.server
import socketserver
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Configuration
PORT = 5000
LOG_DIR = "/tmp/openclaw"
REFRESH_INTERVAL = 10  # seconds

HTML_TEMPLATE = """<!DOCTYPE html>
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
        .panel-header { background: #363636; padding: 15px 20px; font-weight: 600; font-size: 1rem; }
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
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
                <span class="auto-refresh">Auto-refresh: {refresh_interval}s</span>
            </div>
        </header>
        
        {warning_html}
        
        <div class="counters">
            <div class="counter pending">
                <div class="counter-value">{stats_pending}</div>
                <div class="counter-label">Pending</div>
            </div>
            <div class="counter completed">
                <div class="counter-value">{stats_completed}</div>
                <div class="counter-label">Completed</div>
            </div>
            <div class="counter failed">
                <div class="counter-value">{stats_failed}</div>
                <div class="counter-label">Failed</div>
            </div>
            <div class="counter todo">
                <div class="counter-value">{stats_todo}</div>
                <div class="counter-label">TODO</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-chip active" onclick="filterTasks('all')">All</button>
            <button class="filter-chip" onclick="filterTasks('pending')">Pending</button>
            <button class="filter-chip" onclick="filterTasks('completed')">Completed</button>
            <button class="filter-chip" onclick="filterTasks('failed')">Failed</button>
            <button class="filter-chip" onclick="filterTasks('todo')">TODO</button>
        </div>
        
        <div class="panel">
            <div class="panel-header">📋 Tasks ({tasks_count} items)</div>
            <div class="panel-content">
                {tasks_html}
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">📝 Recent Activity ({logs_count} lines)</div>
            <div class="panel-content">
                {logs_html}
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">⏰ Cron Jobs ({cron_count} jobs)</div>
            <div class="panel-content">
                {cron_html}
            </div>
        </div>
    </div>
    
    <script>
        function filterTasks(filter) {{
            document.querySelectorAll('.filter-chip').forEach(chip => {{
                chip.classList.toggle('active', chip.textContent.toLowerCase().includes(filter));
            }});
            document.querySelectorAll('.task-item').forEach(item => {{
                item.style.display = (filter === 'all' || item.dataset.status === filter) ? 'flex' : 'none';
            }});
        }}
        
        setInterval(() => location.reload(), {refresh_interval} * 1000);
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
        
        latest_log = max(log_files, key=os.path.getmtime)
        
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines[-100:]:
            line = line.strip()
            if line:
                parts = line.split(']', 1)
                if len(parts) > 1:
                    time_part = parts[0].strip('[')
                    message = parts[1].strip()
                else:
                    time_part = ''
                    message = line
                logs.append({'time': time_part, 'message': message})
        
        return logs[-50:]
    
    except Exception:
        return []


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
            return [], result.stderr.strip()
        
        tasks = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Session') or line.startswith('-'):
                continue
            
            if any(status in line.lower() for status in ['pending', 'running', 'completed', 'failed', 'todo']):
                status = 'pending'
                if 'completed' in line.lower():
                    status = 'completed'
                elif 'failed' in line.lower():
                    status = 'failed'
                elif 'todo' in line.lower():
                    status = 'todo'
                
                tasks.append({
                    'name': line[:80] + ('...' if len(line) > 80 else ''),
                    'status': status
                })
        
        return tasks, None
    
    except FileNotFoundError:
        return [], "OpenClaw CLI not found"
    except Exception as e:
        return [], str(e)


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
            return []
        
        jobs = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Job') or line.startswith('-') or '-----' in line:
                continue
            jobs.append({
                'name': line[:60] + ('...' if len(line) > 60 else ''),
                'schedule': 'scheduled'
            })
        
        return    
    except Exception jobs[:10]
:
        return []


def calculate_stats(tasks):
    """Calculate status counters."""
    stats = {'pending': 0, 'completed': 0, 'failed': 0, 'todo': 0}
    for task in tasks:
        status = task.get('status', 'pending').lower()
        if status in stats:
            stats[status] += 1
    return stats


def render_tasks_html(tasks):
    """Render tasks HTML."""
    if not tasks:
        return '<div class="empty-state">No tasks found</div>'
    
    html = ''
    for task in tasks:
        html += f'''<div class="task-item" data-status="{task['status']}">
            <span class="task-name">{task['name']}</span>
            <span class="task-status {task['status']}">{task['status']}</span>
        </div>'''
    return html


def render_logs_html(logs):
    """Render logs HTML."""
    if not logs:
        return '<div class="empty-state">No log entries found</div>'
    
    html = ''
    for log in logs:
        html += f'''<div class="log-line">
            <span class="log-time">{log['time']}</span>
            <span>{log['message']}</span>
        </div>'''
    return html


def render_cron_html(jobs):
    """Render cron jobs HTML."""
    if not jobs:
        return '<div class="empty-state">No cron jobs configured</div>'
    
    html = ''
    for job in jobs:
        html += f'''<div class="task-item">
            <span class="task-name">{job['name']}</span>
            <span class="task-status todo">{job['schedule']}</span>
        </div>'''
    return html


def get_dashboard_html():
    """Generate the dashboard HTML."""
    logs = get_openclaw_logs()
    tasks, warning = get_subagents_list()
    cron_jobs = get_cron_jobs()
    stats = calculate_stats(tasks)
    
    warning_html = f'<div class="warning">{warning}</div>' if warning else ''
    
    return HTML_TEMPLATE.format(
        refresh_interval=REFRESH_INTERVAL,
        warning_html=warning_html,
        stats_pending=stats['pending'],
        stats_completed=stats['completed'],
        stats_failed=stats['failed'],
        stats_todo=stats['todo'],
        tasks_count=len(tasks),
        tasks_html=render_tasks_html(tasks),
        logs_count=len(logs),
        logs_html=render_logs_html(logs),
        cron_count=len(cron_jobs),
        cron_html=render_cron_html(cron_jobs)
    )


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = get_dashboard_html()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress logging."""
        pass


def main():
    """Start the dashboard server."""
    print("🚀 Starting OpenClaw Dashboard (stdlib)...")
    print(f"📍 Open http://localhost:{PORT} in your browser")
    
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    main()
