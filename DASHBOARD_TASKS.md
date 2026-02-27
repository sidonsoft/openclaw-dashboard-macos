# OpenClaw Dashboard – Improvement Tasks

Generated: 2026-02-28

## Findings from code review

1. `app.py` is now using `openclaw sessions --json` (good).
2. `app_stdlib.py` still uses `openclaw subagents list` (invalid on this CLI), so fallback mode can fail with:
   - `unknown command 'subagents'`
3. No automated tests yet for parsers/log summarization.
4. No simple health endpoint for uptime checks.
5. Flask and stdlib implementations are drifting (duplicate logic).

---

## Priority Task List

## P0 — Fix stdlib fallback command compatibility
- **Goal:** make `app_stdlib.py` use the same compatible sessions-based task source as `app.py`.
- **Changes:**
  - Replace `openclaw subagents list` calls with `openclaw sessions --active 180 --json`.
  - Apply same status heuristics (`pending/completed/failed`) and warning handling.
- **Acceptance:**
  - `python3 app_stdlib.py` starts.
  - Dashboard loads without command error warning.

## P1 — Add health endpoint + startup diagnostics
- **Goal:** improve observability and monitoring.
- **Changes:**
  - Add `/healthz` endpoint returning `{status, version, timestamp, dataSources}`.
  - Add startup check output listing which data sources are available.
- **Acceptance:**
  - `curl /healthz` returns `200` and JSON.

## P1 — Add parser tests
- **Goal:** prevent regressions in task/log parsing.
- **Changes:**
  - Add `tests/test_parsers.py` for:
    - sessions JSON -> task list/status mapping
    - concise log summarizer behavior
  - Include fixtures for noisy lines.
- **Acceptance:**
  - `python3 -m pytest -q` passes.

## P2 — De-duplicate logic between Flask + stdlib apps
- **Goal:** keep one parser implementation.
- **Changes:**
  - Create `dashboard_core.py` for shared collectors/parsers.
  - Import from both `app.py` and `app_stdlib.py`.
- **Acceptance:**
  - Both apps run and show same counts from same input.

## P2 — UX polish for activity feed
- **Goal:** make recent activity concise and scannable.
- **Changes:**
  - Add severity badges (error/warn/info/debug).
  - Group repeated lifecycle lines (`lane enqueue/dequeue/done`) into compact summaries.
- **Acceptance:**
  - Activity panel remains under ~80 lines and is human-readable.

## P3 — Run controls
- **Goal:** easier local operations.
- **Changes:**
  - Add `scripts/dashboard_ctl.sh start|stop|status|logs`.
  - PID file + port detection.
- **Acceptance:**
  - Can reliably stop old instance before restart with one command.

---

## Suggested execution order
1. P0 compatibility fix (stdlib)
2. P1 health endpoint
3. P1 parser tests
4. P2 shared core refactor
5. P2/P3 polish
