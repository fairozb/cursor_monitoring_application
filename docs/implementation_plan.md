# Technical Implementation Plan
## Demo Infrastructure Monitoring Application (Linux)

**Based on:** [docs/requirements.md](requirements.md) (Approved)  
**Environment:** Linux Jumpbox training lab  
**Application port:** 5000  
**Scope:** Simple local demo — no Docker, no OS/firewall changes, no application code in this document  

---

## 1. Project Directory Structure

```
Monitoring_Application/
├── docs/
│   ├── requirements.md
│   └── implementation_plan.md
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Settings from environment (no secrets in code)
│   ├── extensions.py            # db, csrf, login helpers
│   ├── models.py                # SQLite models (User, Server)
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py            # Login / logout
│   ├── servers/
│   │   ├── __init__.py
│   │   └── routes.py            # Inventory CRUD (CSRF-protected)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # JSON metrics endpoints
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── local_collector.py   # psutil (Jumpbox)
│   │   ├── remote_collector.py  # Paramiko SSH key
│   │   ├── demo_collector.py    # Simulated hosts (labelled)
│   │   └── collector.py         # Dispatcher by server type
│   └── utils/
│       ├── __init__.py
│       └── security.py          # Hashing, session helpers
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── server_detail.html
│   └── servers_manage.html
├── static/
│   ├── css/
│   │   └── dashboard.css        # Grafana-style theme
│   └── js/
│       └── dashboard.js         # Chart.js + 10s refresh
├── instance/                    # Created at runtime (gitignored)
│   └── monitor.db               # SQLite file
├── .env.example                 # Documented env vars only (no real secrets)
├── .gitignore
├── requirements.txt
├── run.py                       # Entry: bind 127.0.0.1:5000
└── README.md                    # Lab setup notes (optional later)
```

Keep modules thin: one responsibility per file. Suitable for a training lab walkthrough.

---

## 2. Python Virtual Environment (Linux Jumpbox)

Do **not** change system Python packages or OS configuration.

```bash
cd /home/jumpuser11/Desktop/Monitoring_Application
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

- Virtualenv stays inside the project (`.venv/`).
- Activate before every lab run: `source .venv/bin/activate`.
- Deactivate with `deactivate` when finished.

---

## 3. Required Python Packages

| Package | Purpose |
|---------|---------|
| `Flask` | Web framework |
| `Flask-WTF` / `WTForms` | Forms + **CSRF** for inventory actions |
| `Werkzeug` | Password hashing (`generate_password_hash` / `check_password_hash`) |
| `psutil` | Local Jumpbox metrics |
| `paramiko` | SSH client for remote Linux hosts (key-based) |
| `python-dotenv` | Load env vars from `.env` (local lab only; `.env` not committed) |

Pin versions in `requirements.txt` when coding begins (e.g. current stable Flask 3.x). No Docker packages.

Example env vars (documented in `.env.example` only):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session signing (required; random string) |
| `ADMIN_PASSWORD` | Bootstrap password for `admin` (hashed on first run; never stored plaintext) |
| `FLASK_ENV` | Optional; `development` for lab |
| `DATABASE_URL` | Optional; default `sqlite:///instance/monitor.db` |
| `SSH_CONNECT_TIMEOUT` | Seconds (e.g. `10`) |
| `DEMO_MODE` | `true`/`false` — enable simulated servers |

**Rule:** No passwords, private keys, or `SECRET_KEY` values in source or docs examples that look like real secrets.

---

## 4. Flask Application Architecture

**Pattern:** Application factory (`create_app()` in `app/__init__.py`).

```
Browser ──HTTP :5000──► run.py ──► Flask app
                                    ├── auth blueprint      /login, /logout
                                    ├── servers blueprint   /servers (CRUD UI)
                                    ├── api blueprint       /api/... (JSON, session-required)
                                    └── pages               / dashboard & detail
                                           │
                                           ▼
                                    monitoring.collector
                                       ├── local (psutil)
                                       ├── remote (Paramiko)
                                       └── demo (simulated)
                                           │
                                           ▼
                                        SQLite (instance/monitor.db)
```

**Blueprints**
- `auth` — login/logout
- `servers` — inventory management (HTML forms, CSRF)
- `api` — metrics JSON for dashboard polling
- Main/dashboard routes registered on app or a `main` blueprint

**Config (`app/config.py`)**
- Read only from environment / `.env`
- Defaults: host `127.0.0.1`, port `5000`, SQLite path under `instance/`
- SSH timeout from env
- `DEMO_MODE` flag

**Sessions**
- Server-side signed cookie session (`SECRET_KEY`)
- Login required for all routes that expose server data or metrics
- Login page and static assets remain public

---

## 5. SQLite Database Schema

Database file: `instance/monitor.db` (create `instance/` at startup if missing).

### Table: `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `username` | TEXT UNIQUE NOT NULL | Fixed demo user: `admin` |
| `password_hash` | TEXT NOT NULL | Werkzeug hash only |
| `created_at` | TEXT | ISO timestamp |

### Table: `servers`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `name` | TEXT NOT NULL | Display name |
| `host` | TEXT | Hostname/IP; null/empty for pure local/demo if unused |
| `ssh_port` | INTEGER | Default `22` |
| `ssh_username` | TEXT | Remote only |
| `ssh_key_path` | TEXT | Absolute/relative path to private key on Jumpbox; never store key material |
| `server_type` | TEXT NOT NULL | `local` \| `remote` \| `demo` |
| `enabled` | INTEGER | 1/0 |
| `created_at` | TEXT | |

**Constraints / conventions**
- Target inventory size: **3–5** rows for the lab.
- At most one `local` server (the Jumpbox).
- `demo` rows are clearly named (e.g. `Simulated-Web-01`) and `server_type = 'demo'`.
- No password columns for SSH (key-based only).

**Bootstrap**
- On first start: if no `admin` user, create from `ADMIN_PASSWORD` env var, then rely on hash only.
- Optionally seed one `local` Jumpbox row and, if `DEMO_MODE=true`, two simulated servers so the dashboard always has content.

---

## 6. Admin Login, Password Hashing, Session Management

| Topic | Plan |
|-------|------|
| Username | `admin` only (single-user demo) |
| Password source | `ADMIN_PASSWORD` env at first bootstrap — **not hardcoded** |
| Hashing | `werkzeug.security.generate_password_hash` / `check_password_hash` |
| Login | POST form → verify → set `session['user_id']` / `session['username']` |
| Logout | Clear session |
| Protection | Decorator `@login_required` on dashboard, detail, inventory, and **all** `/api/*` metric routes |
| Cookie | `HttpOnly` session cookie; `SameSite=Lax`; lab may omit Secure (HTTP localhost only) |
| Failure | Generic “Invalid credentials” message; no user enumeration detail |

CSRF: login form should use Flask-WTF CSRF tokens as well as inventory forms.

---

## 7. Local Linux Monitoring (psutil)

**Module:** `app/monitoring/local_collector.py`  
**Target:** The Jumpbox itself (`server_type = local`).

| Metric | Approach |
|--------|----------|
| CPU % | `psutil.cpu_percent(interval=...)` |
| Memory | `psutil.virtual_memory()` (total, used, percent) |
| Disk | `psutil.disk_usage('/')` (or configurable mount) |
| Network | `psutil.net_io_counters()` (bytes sent/recv; rate optional via delta) |
| Listening ports | `psutil.net_connections(kind='inet')` filtered to LISTEN; return port + status (no process kill) |
| Uptime | Derived from `psutil.boot_time()` |
| Online status | Always online if collector runs successfully on local host |

**Security:** Read-only APIs only. No process termination, no service restarts, no writes to system config.

---

## 8. Remote Linux Monitoring (Paramiko + SSH Keys)

**Module:** `app/monitoring/remote_collector.py`

**Auth**
- Private key path from `servers.ssh_key_path` (file on Jumpbox)
- Username / host / port from inventory
- **No password auth** in this demo

**SSH host key verification**
- Use Paramiko with a known_hosts policy: load Jumpbox user `~/.ssh/known_hosts` (or project-configured known_hosts path via env)
- Reject unknown/changed host keys (e.g. `RejectPolicy` or explicit verify against known_hosts) — **do not** use `AutoAddPolicy` in the lab solution intended for “correct” security practice
- Document that lab users must have already accepted host keys via a normal `ssh` login once

**Connection hygiene**
- Connect timeout from `SSH_CONNECT_TIMEOUT` (default ~10s)
- Command/exec timeout so hung remotes do not block the request thread indefinitely
- Always close SSH client in `finally`

**Read-only remote commands** (examples — final set chosen at coding time; all non-mutating):

| Need | Example command family |
|------|------------------------|
| CPU | `grep 'cpu ' /proc/stat` or `top -bn1` parse / `nproc` + `/proc/loadavg` |
| Memory | `free -b` or read `/proc/meminfo` |
| Disk | `df -B1 /` |
| Network | Read `/proc/net/dev` |
| Listening ports | `ss -lntu` or `ss -lnt` |
| Uptime | `uptime -s` or `/proc/uptime` |

Normalize remote output into the **same JSON shape** as the local collector so the UI is identical.

---

## 9. Server Inventory Management

**UI:** `servers_manage.html` + `servers` blueprint  
**Operations:** List, Add, Remove (Edit optional for lab simplicity: edit = remove + re-add)

**Add form fields**
- Name, type (`local` / `remote` / `demo`), host, SSH port, SSH username, SSH key path (remote only)
- CSRF token required on POST

**Rules**
- Session required
- Cap soft-limit messaging at 5 servers for the demo
- `demo` type ignores SSH fields; collector returns simulated metrics
- Removing a server deletes inventory row only (no remote side effects)

**CSRF:** Flask-WTF `CSRFProtect` enabled app-wide; all state-changing inventory POSTs validated.

---

## 10. REST API Endpoints (Metrics)

All JSON endpoints require an authenticated session. Return consistent error bodies.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/health` | App up check (may be public or auth-gated; prefer auth for lab consistency) |
| `GET` | `/api/servers` | Inventory list (id, name, type, host, enabled) — no key paths in response if avoidable |
| `GET` | `/api/servers/<id>/metrics` | Live metrics for one server |
| `GET` | `/api/servers/metrics` | Live metrics for all enabled servers (dashboard poll) |

**Example metrics payload (conceptual)**
```json
{
  "server_id": 1,
  "name": "Jumpbox",
  "server_type": "local",
  "status": "online",
  "error": null,
  "simulated": false,
  "uptime_seconds": 123456,
  "cpu_percent": 12.5,
  "memory": { "total": 0, "used": 0, "percent": 0 },
  "disk": { "total": 0, "used": 0, "percent": 0 },
  "network": { "bytes_sent": 0, "bytes_recv": 0 },
  "listening_ports": [ { "port": 22, "proto": "tcp" } ],
  "collected_at": "ISO-8601"
}
```

For demo hosts: `"simulated": true` and `"server_type": "demo"`.

---

## 11. Grafana-Style Dashboard (Bootstrap + Chart.js)

**Look and feel**
- Dark theme, dense panels, clear status colors (green online / red offline / amber warning)
- Bootstrap grid for responsive layout (desktop + laptop lab screens)
- Chart.js line/gauge or doughnut panels for CPU, memory, disk, network

**Pages**
1. **Login** — centered form
2. **Dashboard** — cards/panels for each server (3–5); summary CPU/mem/disk; online/offline badge; **Simulated** badge for demo hosts
3. **Server detail** — larger charts + ports table + uptime
4. **Manage servers** — inventory table + add form

**Frontend assets**
- CDN or vendored Bootstrap + Chart.js (CDN acceptable for closed lab Jumpbox if network allows; otherwise vendor under `static/`)
- `static/js/dashboard.js` owns chart instances and poll loop
- `static/css/dashboard.css` for Grafana-like panel styling

---

## 12. Automatic Refresh (10 Seconds)

- Dashboard and detail pages: JavaScript `setInterval` / `fetch` every **10_000 ms** to `/api/servers/metrics` or `/api/servers/<id>/metrics`
- Use `credentials: 'same-origin'` so session cookie is sent
- On `401`, redirect to login
- Show last-updated timestamp and a subtle refreshing indicator
- Avoid overlapping requests: skip tick if previous fetch still in flight
- No WebSockets required for this lab

---

## 13. Error Handling (Unreachable Servers)

| Scenario | Behaviour |
|----------|-----------|
| SSH timeout / connection refused | `status: "offline"`, `error` short reason, empty/zero metrics safe for charts |
| Auth / key file missing | offline + clear error (e.g. “key not found”) |
| Host key verification failure | offline + “host key verification failed” |
| Remote command failure / parse error | offline or `degraded` + error string |
| Local psutil unexpected error | offline + error (rare) |
| Demo collector | always online unless explicitly disabled |

API still returns HTTP 200 with structured body for per-host failures so one bad host does not break the whole dashboard. Inventory/API auth failures remain 401/403.

Log errors server-side at warning level without printing secrets or private key contents.

---

## 14. Functional and Security Testing

### Functional (manual lab checklist)
- [ ] Login succeeds with env-bootstrapped password; fails with wrong password
- [ ] Unauthenticated access to dashboard/API redirects or 401
- [ ] Local Jumpbox metrics populate via psutil
- [ ] Remote host metrics via SSH key (if available)
- [ ] Demo hosts show metrics and **Simulated** labelling
- [ ] Inventory add/remove works; CSRF rejects missing token
- [ ] Dashboard refreshes ~every 10s
- [ ] Unreachable remote shows offline + error
- [ ] App listens on `127.0.0.1:5000`

### Security checklist
- [ ] No credentials or private keys in repo/source
- [ ] Password only stored as hash
- [ ] SSH host key verification enabled (no blind auto-add in final design)
- [ ] Remote commands are read-only
- [ ] All server-data routes session-protected
- [ ] CSRF on inventory (and login) POSTs
- [ ] SSH connect/exec timeouts configured
- [ ] No OS/firewall/sysctl changes performed by the app or setup docs

Optional light automated tests later: hash verify unit test; collector JSON shape test with demo collector (no real SSH required).

---

## 15. Local Deployment on Port 5000

**Bind:** `127.0.0.1:5000` only (local Jumpbox demo).

```bash
source .venv/bin/activate
export SECRET_KEY='...'          # lab-generated random value
export ADMIN_PASSWORD='...'      # used once to create admin hash
export DEMO_MODE=true            # recommended for training when remotes missing
python run.py
```

- `run.py` calls `app.run(host='127.0.0.1', port=5000, debug=False)` for demos (or debug only if instructor enables it).
- Open `http://127.0.0.1:5000`
- Do **not** open firewall ports or change system services
- Stop with Ctrl+C; database persists in `instance/monitor.db`

---

## Security Requirements (Summary)

| Requirement | Implementation approach |
|-------------|-------------------------|
| No hardcoded credentials | Env vars + hashed DB storage; `.env` gitignored; `.env.example` placeholders only |
| SSH host key verification | Paramiko + known_hosts / reject unknown keys |
| Read-only Linux monitoring | psutil read APIs; remote read-only `/proc`/`ss`/`df`/`free`-style commands |
| Session protection | `@login_required` on all server data & metric routes |
| CSRF protection | Flask-WTF `CSRFProtect` on inventory (and auth) forms |
| SSH timeouts | Configurable connect + command timeouts |
| No OS/firewall changes | Documented and enforced as non-goals; app never invokes privileged config tools |

---

## Demo Mode (Simulated Servers)

**Purpose:** Training labs where only the Jumpbox (or no remotes) is available still show a full 3–5 server dashboard.

| Item | Plan |
|------|------|
| Flag | `DEMO_MODE=true` |
| Seeding | Create 2–3 `server_type=demo` inventory rows on first run if none exist |
| Collector | `demo_collector.py` generates plausible CPU/mem/disk/network/ports/uptime with light random walk |
| Labelling | API `simulated: true`; UI badge **Simulated** on cards and detail header; names like `Simulated-App-01` |
| Safety | No SSH; no network calls; cannot be confused with `local`/`remote` in API `server_type` |

Instructors can set `DEMO_MODE=false` and add real remotes when keys and known_hosts are ready.

---

## Suggested Build Order (When Coding Begins)

1. Scaffold structure, `requirements.txt`, config, app factory, SQLite models  
2. Auth bootstrap + login/logout + `@login_required`  
3. Local psutil collector + one dashboard panel  
4. API metrics endpoints + 10s JS refresh  
5. Inventory CRUD + CSRF  
6. Remote Paramiko collector + host key verify + timeouts  
7. Demo mode collector + labelling  
8. Grafana-style polish + error/offline states  
9. Walk through functional/security checklist on Jumpbox  

---

## Out of Scope (Reaffirmed)

Historical retention, alerting, Docker, multi-user RBAC, HTTPS termination, remote agents, Windows hosts, and any OS or firewall reconfiguration.

---

## Deliverable Note

This document is the **implementation plan only**. Application source code is intentionally not generated at this stage.
