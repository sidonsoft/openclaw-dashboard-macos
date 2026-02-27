#!/usr/bin/env python3
"""
OpenClaw Activity Dashboard
A local web dashboard for monitoring OpenClaw activity on macOS.
"""

import os
import glob
import subprocess
import json
import re
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
        
        .task-item { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 12px 0; border-bottom: 1px solid #3d3d3d; }
        .task-item:last-child { border-bottom: none; }
        .task-main { min-width: 0; }
        .task-name { font-weight: 600; margin-bottom: 3px; }
        .task-summary { font-size: 12px; color: #a8b0bd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 860px; }
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
                        <div class="task-main">
                            <div class="task-name">{{ task.name }}</div>
                            <div class="task-summary">{{ task.summary }}</div>
                        </div>
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
        
        {% if codex_usage %}
        <div class="panel">
            <div class="panel-header">
                <span>🔮 Codex Usage</span>
                <span style="font-weight: normal; font-size: 13px; color: #9ca3af;">{{ codex_usage.plan or 'Account' }}</span>
            </div>
            <div class="panel-content" style="max-height: 180px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <div style="color: #9ca3af; font-size: 12px; margin-bottom: 4px;">Primary Window</div>
                        <div style="font-size: 1.4rem; font-weight: bold;">{{ codex_usage.primary.usedPercent }}%</div>
                        <div style="font-size: 11px; color: #6b7280;">{{ codex_usage.primary.resetDescription or '' }}</div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 12px; margin-bottom: 4px;">Secondary Window</div>
                        <div style="font-size: 1.4rem; font-weight: bold;">{{ codex_usage.secondary.usedPercent }}%</div>
                        <div style="font-size: 11px; color: #6b7280;">{{ codex_usage.secondary.resetDescription or '' }}</div>
                    </div>
                </div>
                {% if codex_usage.accountEmail %}
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #3d3d3d; font-size: 12px; color: #9ca3af;">
                    {{ codex_usage.accountEmail }}
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}
        
        {% if openclaw_usage %}
        <div class="panel">
            <div class="panel-header">
                <span>🦞 OpenClaw Sessions</span>
                <span style="font-weight: normal; font-size: 13px; color: #9ca3af;">{{ openclaw_usage.totalActive }} active</span>
            </div>
            <div class="panel-content" style="max-height: 220px;">
                {% if openclaw_usage.mainSession %}
                <div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #3d3d3d;">
                    <div style="color: #9ca3af; font-size: 12px; margin-bottom: 4px;">Main Session</div>
                    <div style="font-size: 13px;">{{ openclaw_usage.mainSession.model }}</div>
                    <div style="font-size: 12px;">
                        {{ openclaw_usage.mainSession.totalTokens|default(0) }} tokens / {{ openclaw_usage.mainSession.contextTokens|default(0) }} context
                        {% if openclaw_usage.mainSession.tokenRatio %}({{ openclaw_usage.mainSession.tokenRatio }}%){% endif %}
                    </div>
                </div>
                {% endif %}
                {% if openclaw_usage.topSessions %}
                <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Top Sessions by Tokens</div>
                    {% for session in openclaw_usage.topSessions %}
                    <div class="task-item">
                        <div class="task-main">
                            <div class="task-name" style="font-size: 12px;">{{ session.key }}</div>
                            <div class="task-summary" style="font-size: 11px;">{{ session.model }} • {{ session.totalTokens|default(0) }} tokens{% if session.tokenRatio %} ({{ session.tokenRatio }}%){% endif %}</div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">No session data</div>
                {% endif %}
            </div>
        </div>
        {% endif %}
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


def _summarize_log_message(raw: str) -> str:
    """Convert noisy OpenClaw log lines into concise, human-readable summaries."""
    s = raw.strip()

    # Unwrap common JSON-wrapped console payloads: {"0":"...","1":"...","_meta":...}
    if s.startswith('{"0"'):
        m1 = re.search(r'"1":"([^"]+)"', s)
        m0 = re.search(r'"0":"([^"]+)"', s)
        s = (m1.group(1) if m1 else (m0.group(1) if m0 else s))
        s = s.replace('\\\"', '"').replace('\\n', ' ').replace('\\t', ' ').strip()

    # Drop known noisy metadata blobs that don't help operators
    if '"_meta"' in s and 'embedded run' not in s and 'lane ' not in s and 'sendMessage ok' not in s:
        return ''

    # Common high-signal simplifications
    replacements = [
        (r"embedded run tool start:.*tool=([a-zA-Z0-9_-]+).*$", r"Tool started: \1"),
        (r"embedded run tool end:.*tool=([a-zA-Z0-9_-]+).*$", r"Tool finished: \1"),
        (r"embedded run done:.*aborted=(true|false).*$", r"Run finished (aborted=\1)"),
        (r"lane enqueue: lane=([^\s]+).*$", r"Queued: \1"),
        (r"lane dequeue: lane=([^\s]+).*$", r"Started: \1"),
        (r"lane task done: lane=([^\s]+).*$", r"Completed: \1"),
        (r"telegram sendMessage ok chat=([^\s]+).*$", r"Telegram sent to chat \1"),
    ]
    for pattern, repl in replacements:
        m = re.search(pattern, s)
        if m:
            return re.sub(pattern, repl, s)

    # Trim very long JSON-ish blobs to reduce noise
    if len(s) > 220:
        s = s[:220] + "…"
    return s


def get_openclaw_logs():
    """Parse recent OpenClaw logs into concise human-readable activity."""
    logs = []
    log_pattern = os.path.join(LOG_DIR, "openclaw-*.log")

    try:
        log_files = glob.glob(log_pattern)
        if not log_files:
            return []

        latest_log = max(log_files, key=os.path.getmtime)

        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Focus on recent lines; include high-signal events first
        for line in lines[-220:]:
            line = line.strip()
            if not line:
                continue

            # Expected format: ISO level [subsystem] message
            m = re.match(r"^(\S+)\s+(\w+)\s+\[([^\]]+)\]\s+(.*)$", line)
            if m:
                ts, level, subsystem, msg = m.groups()
                level_l = level.lower()

                # Keep errors/warnings always; sample key info/debug lifecycle lines
                keep = level_l in {"error", "warn"}
                if not keep:
                    keep = any(k in msg for k in [
                        "lane task done", "lane enqueue", "lane dequeue",
                        "embedded run", "sendMessage ok", "failed", "timeout"
                    ])
                if not keep:
                    continue

                summary = _summarize_log_message(msg)
                if not summary:
                    continue
                logs.append({
                    'time': ts,
                    'message': f"[{subsystem}] {summary}"
                })
            else:
                summary = _summarize_log_message(line)
                if summary:
                    logs.append({'time': '', 'message': summary})

        return logs[-80:]

    except FileNotFoundError:
        return []
    except Exception as e:
        return [{'time': '', 'message': f'Error reading logs: {str(e)}'}]


def _short_task_text(text: str, max_len: int = 110) -> str:
    text = (text or '').replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > max_len:
        return text[:max_len - 1] + '…'
    return text


def get_subagents_list():
    """Build task list with agent + concise task summary from session store."""
    try:
        store_path = os.path.expanduser('~/.openclaw/agents/main/sessions/sessions.json')
        if not os.path.exists(store_path):
            return [], f"session store not found: {store_path}"

        with open(store_path, 'r', encoding='utf-8') as f:
            store = json.load(f)

        now_ms = int(datetime.now().timestamp() * 1000)
        tasks = []

        for key, s in store.items():
            if 'subagent' not in key:
                continue

            updated_at = int(s.get('updatedAt', 0) or 0)
            if not updated_at:
                continue

            age_ms = max(0, now_ms - updated_at)
            aborted = bool(s.get('abortedLastRun', False))
            model = s.get('model', 'unknown')
            label = s.get('label') or 'subagent task'
            spawned_by = s.get('spawnedBy', 'main')

            # Heuristic statuses tuned for operator visibility:
            # - fresh delegated work appears as TODO
            # - medium-age work appears as pending
            # - old work considered completed unless aborted
            if aborted:
                status = 'failed'
            elif age_ms < 20 * 60 * 1000:
                status = 'todo'
            elif age_ms < 2 * 60 * 60 * 1000:
                status = 'pending'
            else:
                status = 'completed'

            agent_name = 'lmstudio' if 'qwen' in model.lower() else ('minimax' if 'minimax' in model.lower() else 'agent')

            tasks.append({
                'name': _short_task_text(label, 70),
                'summary': _short_task_text(f"{agent_name} • {model} • from {spawned_by}", 120),
                'status': status,
                'updatedAt': updated_at,
            })

        tasks.sort(key=lambda x: x.get('updatedAt', 0), reverse=True)
        return tasks[:120], None

    except json.JSONDecodeError:
        return [], 'sessions.json parse error'
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


def get_codex_usage():
    """Collect Codex usage data from codexbar."""
    try:
        result = subprocess.run(
            ['codexbar', 'usage', '--provider', 'codex', '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        if not data:
            return None
        
        # Get first entry (codex provider)
        entry = data[0] if isinstance(data, list) else data
        usage = entry.get('usage', {})
        
        primary = usage.get('primary', {})
        secondary = usage.get('secondary', {})
        identity = usage.get('identity', {})
        
        return {
            'primary': {
                'usedPercent': primary.get('usedPercent'),
                'resetDescription': primary.get('resetDescription')
            },
            'secondary': {
                'usedPercent': secondary.get('usedPercent'),
                'resetDescription': secondary.get('resetDescription')
            },
            'accountEmail': identity.get('accountEmail') or usage.get('accountEmail'),
            'plan': identity.get('loginMethod') or usage.get('loginMethod')
        }
    
    except Exception:
        return None  # Graceful fallback


def get_openclaw_usage():
    """Collect OpenClaw session usage data."""
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', '--active', '180', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        sessions = data.get('sessions', [])
        
        if not sessions:
            return {'totalActive': 0, 'topSessions': [], 'mainSession': None}
        
        # Filter sessions with valid totalTokens
        valid_sessions = [s for s in sessions if s.get('totalTokens') is not None]
        
        # Sort by totalTokens descending and get top 5
        top_sessions = sorted(valid_sessions, key=lambda x: x.get('totalTokens', 0), reverse=True)[:5]
        
        top_5 = []
        for s in top_sessions:
            tokens = s.get('totalTokens', 0)
            context = s.get('contextTokens', 0)
            ratio = round(tokens / context * 100, 1) if context and tokens else None
            
            top_5.append({
                'key': s.get('key', '')[:50] + ('...' if len(s.get('key', '')) > 50 else ''),
                'model': s.get('model', 'unknown'),
                'totalTokens': tokens,
                'contextTokens': context,
                'tokenRatio': ratio
            })
        
        # Find main session
        main_session = None
        for s in sessions:
            if s.get('key') == 'agent:main:main':
                tokens = s.get('totalTokens', 0)
                context = s.get('contextTokens', 0)
                ratio = round(tokens / context * 100, 1) if context and tokens else None
                main_session = {
                    'totalTokens': tokens,
                    'contextTokens': context,
                    'tokenRatio': ratio,
                    'model': s.get('model', 'unknown')
                }
                break
        
        return {
            'totalActive': len(sessions),
            'topSessions': top_5,
            'mainSession': main_session
        }
    
    except Exception:
        return None  # Graceful fallback


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
    codex_usage = get_codex_usage()
    openclaw_usage = get_openclaw_usage()
    
    return render_template_string(
        HTML_TEMPLATE,
        logs=logs,
        tasks=tasks,
        cron_jobs=cron_jobs,
        stats=stats,
        warning=warning,
        refresh_interval=REFRESH_INTERVAL,
        codex_usage=codex_usage,
        openclaw_usage=openclaw_usage
    )


@app.route('/api/data')
def api_data():
    """JSON API for auto-refresh."""
    logs = get_openclaw_logs()
    tasks, _ = get_subagents_list()
    cron_jobs = get_cron_jobs()
    stats = calculate_stats(tasks)
    codex_usage = get_codex_usage()
    openclaw_usage = get_openclaw_usage()
    
    return jsonify({
        'logs': logs,
        'tasks': tasks,
        'cron_jobs': cron_jobs,
        'stats': stats,
        'codex_usage': codex_usage,
        'openclaw_usage': openclaw_usage
    })


def check_data_sources():
    """Check availability of each data source."""
    sources = {
        'openclaw_cli': False,
        'log_files': False,
        'sessions': False,
        'cron': False
    }
    
    # Check OpenClaw CLI
    try:
        result = subprocess.run(['openclaw', '--version'], capture_output=True, timeout=5)
        sources['openclaw_cli'] = result.returncode == 0
    except Exception:
        pass
    
    # Check log files
    try:
        log_files = glob.glob(os.path.join(LOG_DIR, "openclaw-*.log"))
        sources['log_files'] = len(log_files) > 0
    except Exception:
        pass
    
    # Check sessions
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', '--active', '180', '--json'],
            capture_output=True, timeout=10
        )
        sources['sessions'] = result.returncode == 0
    except Exception:
        pass
    
    # Check cron
    try:
        result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, timeout=10)
        sources['cron'] = result.returncode == 0
    except Exception:
        pass
    
    return sources


def get_health_data():
    """Get health status for /healthz endpoint."""
    sources = check_data_sources()
    all_ok = sources.get('openclaw_cli', False) and sources.get('sessions', False)
    
    return {
        'status': 'ok' if all_ok else 'degraded',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'dataSources': sources
    }


@app.route('/healthz')
def healthz():
    """Health check endpoint."""
    return jsonify(get_health_data())


def print_startup_diagnostics():
    """Print startup diagnostics to console."""
    print("\n📊 Startup Diagnostics:")
    sources = check_data_sources()
    
    status_map = {True: '✅', False: '❌'}
    print(f"  {status_map[sources['openclaw_cli']]} OpenClaw CLI")
    print(f"  {status_map[sources['log_files']]} Log files in {LOG_DIR}")
    print(f"  {status_map[sources['sessions']]} Sessions API")
    print(f"  {status_map[sources['cron']]} Cron API")
    
    if not sources['openclaw_cli']:
        print("\n⚠️  Warning: OpenClaw CLI not found. Is OpenClaw installed?")
    print()


if __name__ == '__main__':
    import socket
    
    def find_free_port(start_port=5001, max_attempts=20):
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
    print_startup_diagnostics()
    print(f"📍 Open http://localhost:{port} in your browser")
    if port != 5000:
        print(f"⚠️  Port 5000 was in use, using port {port} instead")
    app.run(host='0.0.0.0', port=port, debug=False)
