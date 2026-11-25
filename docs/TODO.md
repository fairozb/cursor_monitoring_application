# TODO — Demo Infrastructure Monitoring Application

**Source:** [requirements.md](requirements.md) (Approved) · [implementation_plan.md](implementation_plan.md)  
**Runtime:** Local Linux Jumpbox · `127.0.0.1:5000`  
**Stack:** Python, Flask, SQLite, Bootstrap, Chart.js, psutil, Paramiko  

**Rules for every step:** no hardcoded credentials · no OS/firewall changes · keep increments small · docs + security notes + tests where listed

**Release:** implementation after the first `main` commit is prepared on branch `dev` for a pull request into `main`. The pull request is not merged from this workspace.  

---

## Progress legend

- `[ ]` not started · `[x]` done  
- Work top to bottom. Do not skip security/docs/tests sub-items for a major feature.

---

## 0. Prerequisites (lab)

- [x] Confirm Python 3 available on Jumpbox (`python3 --version`)
- [x] Confirm project path: `Monitoring_Application/`
- [x] Confirm docs present: `requirements.md`, `implementation_plan.md`, `TODO.md`
- [x] **Security:** Agree secrets only via env / `.env` (gitignored); never commit keys or passwords
- [x] **Docs:** Note in README that setup does not modify OS or firewall

---

## 1. Project initialization and basic UI

**Goal:** Empty Flask app with a simple Grafana-style shell page on port 5000.

- [x] Create directory layout (`app/`, `templates/`, `static/css`, `static/js`, `tests/`, `instance/` placeholder)
- [x] Add `.gitignore` (`.venv/`, `.env`, `instance/*.db`, `__pycache__/`, `.pytest_cache/`)
- [x] Add `requirements.txt` (minimal: Flask first; add others as features land)
- [x] Create venv and install Flask only
- [x] Add `app/__init__.py` app factory + `run.py` binding **`127.0.0.1:5000`**
- [x] Add `app/config.py` reading `SECRET_KEY` from environment (fail clearly if missing in later steps)
- [x] Add `templates/base.html` + `templates/dashboard.html` (Bootstrap CDN or static)
- [x] Add `static/css/dashboard.css` — dark panel look (Grafana-style shell, no live data yet)
- [x] Placeholder dashboard route `/` showing app title and empty panels
- [x] Add `.env.example` with placeholder keys only (no real secrets)
- [x] **Security:** No credentials in code; bind localhost only
- [x] **Docs:** README section — venv, `pip install`, `python run.py`, open `http://127.0.0.1:5000`
- [x] **Tests:** Smoke test — app factory creates app; `GET /` returns 200
- [x] **Acceptance:** App starts on Jumpbox; browser shows basic dashboard shell on port 5000
  - Note (lab): default remains `127.0.0.1:5000`; on this shared Jumpbox ports 5000–5001 were already in use by other users, so live HTTP validation used `FLASK_PORT=5002` without changing OS/firewall.

---

## 2. Sign-in functionality and unit tests

**Goal:** Single `admin` user, hashed password, session gate.

- [x] Add Werkzeug hashing helpers in `app/utils/security.py`
- [x] Add login/logout routes and `templates/login.html`
- [x] Bootstrap admin from `ADMIN_PASSWORD` env on first run (hash only in storage — DB may be stub/file until step 3)
- [x] Implement `@login_required`; protect dashboard route
- [x] Redirect unauthenticated users to `/login`
- [x] Add Flask-WTF CSRF on login form
- [x] **Security:** No plaintext password storage; generic login error; CSRF on POST; session cookie HttpOnly / SameSite=Lax
- [x] **Docs:** Document `SECRET_KEY` and `ADMIN_PASSWORD` in `.env.example` + README
- [x] **Unit tests:**
  - [x] Password hash verify succeeds / fails
  - [x] Login success sets session
  - [x] Login failure does not set session
  - [x] Protected route redirects when logged out
- [x] **Acceptance:** Only logged-in `admin` sees dashboard; wrong password denied; no secrets in repo

---

## 3. SQLite database integration

**Goal:** Persist `users` and `servers` in `instance/monitor.db`.

- [x] Add SQLite init (Flask path `instance/monitor.db`)
- [x] Create `users` table schema (username unique, `password_hash`, timestamps)
- [x] Create `servers` table schema (name, host, ssh_port, ssh_username, ssh_key_path, server_type, enabled)
- [x] Migrate admin bootstrap to create/read `users` row from DB
- [x] Ensure `instance/` created at runtime; DB file gitignored
- [x] **Security:** Store only password hashes; never store SSH private key material in DB (path reference only)
- [x] **Docs:** Document schema in README or `docs/schema.md` (short)
- [x] **Tests:** DB init creates tables; admin user inserted once; second boot does not duplicate admin
- [x] **Acceptance:** Restarting app keeps admin user; DB file under `instance/`

---

## 4. CI/CD setup (GitHub Actions)

**Goal:** Automated test + validation on every push/PR. Do this early so later steps stay green.

- [x] Add `.github/workflows/ci.yml`
- [x] Job: checkout, setup Python, create venv, `pip install -r requirements.txt` + pytest
- [x] Run unit tests with env fixtures (`SECRET_KEY`, `ADMIN_PASSWORD` as CI secrets/env — dummy values OK)
- [x] Optional: lint step (e.g. `ruff` or `flake8`) — keep minimal
- [x] **Security:** No real credentials in workflow files; use GitHub Actions `env` dummy values only
- [x] **Docs:** README badge/section — how CI runs tests
- [x] **Acceptance:** Workflow runs on push/PR; tests must pass to be considered green

---

## 5. Local Linux monitoring (psutil)

**Goal:** Collect live metrics from the Jumpbox.

- [x] Add `psutil` to `requirements.txt`
- [x] Implement `app/monitoring/local_collector.py` (read-only)
- [x] Return normalized dict: cpu, memory, disk, network, listening ports, uptime, status
- [x] Wire a temporary authenticated API or page section showing local metrics
- [x] **Security:** Read-only psutil usage only; no process kill / service changes
- [x] **Docs:** Note local collector behaviour in README
- [x] **Tests:** Local collector returns required keys; values are numeric/sane; does not raise on Jumpbox
- [x] **Acceptance:** Logged-in user sees live Jumpbox CPU/memory (at least) from psutil

---

## 6. Metrics API and full local metric set

**Goal:** REST JSON for CPU, memory, disk, network, ports, uptime, online/offline.

- [x] Add `api` blueprint: `GET /api/servers/metrics` and `GET /api/servers/<id>/metrics`
- [x] Protect all metrics routes with `@login_required` (401/redirect)
- [x] Include listening ports + uptime + status in payload
- [x] Seed or ensure one `local` server row in inventory/DB
- [x] **Security:** Session required; do not expose SSH key paths in JSON if avoidable
- [x] **Docs:** Short API table in README
- [x] **Tests:** Unauthorized API access denied; authorized local metrics JSON shape valid
- [x] **Acceptance:** API returns full metric set for local server

---

## 7. Grafana-style dashboard UI (live local data)

**Goal:** Attractive read-only panels with Chart.js for local host.

- [x] Add Chart.js to dashboard
- [x] Server card/panel for local host: CPU, memory, disk, network charts
- [x] Tables/lists for listening ports and uptime
- [x] Online/offline badge styling
- [x] **Security:** UI is read-only (no mutate actions on metrics)
- [x] **Docs:** Screenshot or UI notes optional; keep README setup current
- [x] **Tests:** Dashboard route requires login; template renders when authenticated
- [x] **Acceptance:** Dashboard looks modern/Grafana-like and shows local live data

---

## 8. Dashboard auto-refresh (10 seconds)

**Goal:** Poll metrics every 10s without full page reload.

- [x] Add `static/js/dashboard.js` — `fetch` metrics every 10_000 ms
- [x] Update charts and status badges in place
- [x] Show last-updated time; skip overlapping requests
- [x] On 401, redirect to login
- [x] **Security:** `credentials: 'same-origin'`; no tokens in JS source
- [x] **Docs:** Document 10s refresh behaviour
- [x] **Tests:** JS interval constant documented/tested if extracted; API still covered by backend tests
- [x] **Acceptance:** Metrics visibly refresh ~every 10 seconds

---

## 9. Linux server inventory management

**Goal:** Add / list / remove servers (3–5 host demo).

- [x] Inventory UI page + forms (name, host, port, username, key path, type)
- [x] POST add / POST delete with **CSRF** protection
- [x] Soft cap messaging at 5 servers
- [x] Session required for all inventory routes
- [x] **Security:** CSRF on all state-changing routes; validate inputs; store key **path** only; no hardcoded creds
- [x] **Docs:** Inventory field meanings in README
- [x] **Tests:** Add server persists; delete removes; CSRF missing token fails; unauthenticated access denied
- [x] **Acceptance:** Admin can manage 3–5 servers from UI; data survives restart

---

## 10. Remote Linux monitoring (Paramiko, SSH keys)

**Goal:** Collect metrics from remote Linux hosts via SSH key auth.

- [x] Add `paramiko` to `requirements.txt`
- [x] Implement `remote_collector.py` — key-based auth only
- [x] Enforce **SSH host key verification** (known_hosts; reject unknown)
- [x] Set **connect and command timeouts** from config/env
- [x] Run **read-only** remote commands only (`/proc`, `ss`/`df`/`free`-style)
- [x] Normalize output to same JSON shape as local collector
- [x] Dispatcher selects local vs remote by `server_type`
- [x] **Security:** No password SSH; no `AutoAddPolicy`; always close clients; timeouts; read-only commands
- [x] **Docs:** Document prerequisite: user must `ssh` once so host key exists; key path configuration
- [x] **Tests:** Mock Paramiko — success path JSON shape; timeout/unreachable → offline + error; host key failure → offline + error; reject password-auth code paths
- [x] **Acceptance:** With a reachable remote + key + known_hosts, dashboard shows remote metrics; failures show offline + reason

---

## 11. Unreachable server error handling

**Goal:** One bad host must not break the dashboard.

- [x] Per-server `status: offline` + short `error` string in API
- [x] UI badge + error text on card/detail
- [x] Aggregate metrics endpoint continues for other hosts
- [x] **Security:** Do not leak key material or full exception secrets in UI
- [x] **Docs:** Troubleshooting short list (timeout, key missing, host key)
- [x] **Tests:** Simulated failure returns structured offline payload; HTTP 200 for aggregate with mixed results
- [x] **Acceptance:** Unreachable host shows offline; others keep updating every 10s

---

## 12. Demo mode (simulated servers)

**Goal:** Labelled simulated hosts when remotes are unavailable.

- [x] `DEMO_MODE` env flag
- [x] `demo_collector.py` with plausible changing metrics
- [x] Seed 2–3 demo servers when enabled and inventory empty/sparse
- [x] API `simulated: true`; UI **Simulated** badge
- [x] **Security:** Demo path performs no SSH; still behind login
- [x] **Docs:** How to enable/disable demo mode
- [x] **Tests:** Demo metrics include `simulated: true`; names/type distinguishable
- [x] **Acceptance:** With `DEMO_MODE=true` and no remotes, dashboard still shows 3–5 hosts clearly marked simulated

---

## 13. Server detail view and polish

**Goal:** Per-server detail page with charts, ports, uptime.

- [x] `templates/server_detail.html` + route
- [x] Larger Chart.js panels; ports table; uptime; status
- [x] 10s refresh on detail page
- [x] **Security:** Login required; read-only
- [x] **Docs:** Navigation notes in README
- [x] **Tests:** Detail requires auth; 404 for unknown id
- [x] **Acceptance:** Clicking a server opens detail with full metric set

---

## 14. End-to-end lab validation (Jumpbox)

**Goal:** Manual acceptance against approved PRD.

- [x] Fresh venv install from `requirements.txt`
- [x] Set `SECRET_KEY`, `ADMIN_PASSWORD`, optional `DEMO_MODE` via env (not hardcoded)
- [x] Start app on `127.0.0.1:5000`
  - Note: default bind remains `127.0.0.1:5000`. On this shared Jumpbox that port was already taken, so this validation used `FLASK_PORT=5004`.
- [x] Login as admin
- [x] Confirm local psutil metrics
- [x] Confirm demo and/or remote SSH metrics
- [x] Confirm inventory add/remove + CSRF
- [x] Confirm 10s auto-refresh
- [x] Confirm offline error behaviour
- [x] **Security:** Re-check no secrets in git; localhost bind; no OS/firewall changes made
- [x] **Docs:** Final README quick-start accurate
- [x] **Acceptance:** All PRD success criteria checked

---

## 15. CI/CD hardening and release checklist

- [x] Ensure GitHub Actions runs full pytest suite (auth, DB, local collector, remote mocks, inventory CSRF, demo mode)
- [x] Fail CI if tests fail
- [x] Confirm workflow does not need Jumpbox SSH (mocks only)
- [x] Tag/docs note: deploy method is local Jumpbox `python run.py` only (no Docker)
- [x] **Security:** CI uses dummy env vars; repository secret scanning awareness (no real keys)
- [x] **Acceptance:** Green CI on main/PR; local demo still runs on port 5000
  - Note: `pytest` is green locally (38 tests). GitHub Actions runs that suite on the next push. Default port is 5000; this host used 5004 because 5000 was busy.

---

## Cross-cutting reminders (every PR / increment)

- [x] No hardcoded credentials or private keys
- [x] No OS configuration or firewall rule changes
- [x] Session protection on any route exposing server data
- [x] CSRF on inventory (and auth) POSTs
- [x] SSH: key-only, host key verify, timeouts, read-only commands
- [x] Update README/docs for the increment
- [x] Add/adjust unit tests + meet that step’s acceptance criteria

---

## Suggested AI-assisted increment size

Prefer one checkbox group (or even a single checkbox) per AI coding session.  
Order is intentional: **UI shell → auth + tests → SQLite → CI → local metrics → API/UI → refresh → inventory → remote SSH → errors → demo → polish → lab validation**.
