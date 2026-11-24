# Product Requirements Document (PRD)
## Demo Infrastructure Monitoring Application (Linux)

**Version:** 1.0  
**Status:** Approved  
**Deployment:** Local Linux Jumpbox (demo)  
**Application port:** 5000  

---

## 1. Problem Statement

Teams currently log in to individual Linux servers to inspect real-time CPU, memory, disk, network, and port usage. This demo application provides a centralized, read-only monitoring dashboard so routine checks no longer require manual SSH logins.

---

## 2. Goals and Non-Goals

### Goals
- Central dashboard for **3–5 Linux servers**
- Real-time utilization and status views
- Local Jumpbox monitoring via **psutil**
- Remote Linux monitoring via **SSH (key-based)**
- Auto-refresh every **10 seconds**
- Single-admin sign-in with securely hashed password

### Non-Goals
- Historical metrics retention
- Alerting / notifications
- Multi-user or role-based access (L1/L2/L3 share one admin view)
- Docker / containers
- Agents on remote hosts
- Windows hosts
- HTTPS/TLS termination
- System or firewall configuration changes

---

## 3. Users

| Audience | Access |
|----------|--------|
| Internal L1 / L2 / L3 (infra & app teams) | Read-only monitoring via single shared admin account |

Demo mode: one admin user only.

---

## 4. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Modern Grafana-style UI; attractive, simple, **read-only** monitoring |
| FR-2 | Sign-in with username `admin` and a securely hashed password (no plaintext credentials in code or repo) |
| FR-3 | Add / list / remove Linux servers for monitoring (inventory of 3–5 hosts) |
| FR-4 | Show real-time **CPU, memory, disk, and network** utilization |
| FR-5 | Show **listening ports**, **uptime**, and **online/offline** status |
| FR-6 | Monitor **local** host with **psutil**; **remote** hosts with **Paramiko (SSH keys)** |
| FR-7 | Dashboard auto-refresh every **10 seconds** |
| FR-8 | On SSH/host failure: mark host **offline** and show a brief error reason |
| FR-9 | Run locally on the Jumpbox at **http://127.0.0.1:5000** (or localhost:5000) |

### Server inventory fields (FR-3)
- Display name
- Hostname or IP
- SSH port (default 22)
- SSH username
- Path to private key (or key reference via environment / config — **not hardcoded**)
- Flag: local (psutil) vs remote (SSH)

---

## 5. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Demo-scale only (3–5 servers); keep implementation minimal |
| NFR-2 | SQLite database file stored in the project directory |
| NFR-3 | Passwords hashed with a strong algorithm (e.g. Werkzeug / bcrypt); bootstrap password via env var or first-run setup — **never hardcode secrets** |
| NFR-4 | SSH uses key-based auth only for this demo |
| NFR-5 | Do not modify OS configs, services, or firewall rules |
| NFR-6 | App binds to localhost on port **5000** for local Jumpbox demo use |

---

## 6. Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python, Flask |
| Frontend | HTML, CSS, Bootstrap, Chart.js |
| Database | SQLite |
| Local metrics | psutil |
| Remote metrics | Paramiko (SSH) |
| Auth | Secure password hashing |

---

## 7. High-Level Architecture

```
Browser (Grafana-style dashboard)
        │  HTTP :5000
        ▼
Flask app (auth + API + templates)
        │
        ├── SQLite (users, server inventory)
        ├── Local collector (psutil) ──► Jumpbox metrics
        └── Remote collector (Paramiko + SSH key) ──► Remote Linux metrics
```

**Data flow (every 10s):** UI polls Flask → collectors gather live metrics → JSON/HTML response → charts update. No time-series store.

---

## 8. UI Outline (Grafana-style)

- Login page (admin only)
- Dashboard home: server cards with online/offline, CPU/mem/disk summary
- Server detail: charts (CPU, memory, disk, network), uptime, listening ports
- Server management: add / remove hosts (admin session required)
- Auto-refresh indicator (10s)

---

## 9. Installation (Local Jumpbox)

Minimal steps (no Docker, no system changes):

1. Use Python 3 on the Jumpbox.
2. Create a virtualenv in the project directory.
3. Install dependencies from `requirements.txt` (`flask`, `psutil`, `paramiko`, etc.).
4. Set admin password via environment variable (e.g. `ADMIN_PASSWORD`) or first-run prompt; app stores only the hash in SQLite.
5. Ensure SSH private keys for remote hosts are available to the Jumpbox user (paths configured in UI/config — not committed).
6. Run: `python app.py` (or equivalent) listening on **port 5000**.
7. Open `http://127.0.0.1:5000` and sign in as `admin`.

---

## 10. Implementation Steps (Minimal)

1. Scaffold Flask app, templates, static assets (Bootstrap + Chart.js).
2. Initialize SQLite schema: `users`, `servers`.
3. Implement admin auth (hashed password; session-protected routes).
4. Implement local metrics collector with psutil.
5. Implement remote metrics collector with Paramiko (SSH key).
6. Build server CRUD (add/list/remove) for 3–5 hosts.
7. Build dashboard + detail views with Chart.js; poll/refresh every 10s.
8. Handle unreachable hosts (offline + error message).
9. Smoke-test: Jumpbox (local) + at least one remote host over SSH.

---

## 11. Success Criteria

- [ ] Admin can sign in; unauthenticated users cannot view metrics
- [ ] Jumpbox appears with live psutil metrics
- [ ] At least one remote Linux host shows live metrics via SSH key auth
- [ ] Inventory supports 3–5 servers total
- [ ] CPU, memory, disk, network, listening ports, uptime, and online/offline are visible
- [ ] Dashboard refreshes every 10 seconds
- [ ] App runs locally on port 5000 without Docker or system/firewall changes
- [ ] No credentials hardcoded in source

---

## 12. Out of Scope (Explicit)

Alerting, historical graphs/retention, multi-user RBAC, Docker, HTTPS, remote agents, non-Linux hosts, and any OS/firewall reconfiguration.
