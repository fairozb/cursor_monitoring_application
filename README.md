# Demo Infrastructure Monitoring Application

Local demo dashboard for Linux Jumpbox monitoring.  
**Status:** Admin sign-in + **real-time local metrics (psutil)**. Remote SSH is not implemented yet.

| Item | Value |
|------|--------|
| Bind | `127.0.0.1:5000` |
| Stack | Python, Flask, Flask-WTF, SQLite, Bootstrap, Chart.js, psutil |
| Docs | [requirements](docs/requirements.md) · [plan](docs/implementation_plan.md) · [TODO](docs/TODO.md) · [schema](docs/schema.md) |

## Security notes

- No passwords or secret keys in source, HTML, or tracked config.
- Set credentials in **gitignored** `.env` (`ADMIN_PASSWORD`, `SECRET_KEY`).
- Only Werkzeug password **hashes** are stored in SQLite.
- Metric APIs require an authenticated session (JSON `401` if logged out).
- Collectors are **read-only**; no root/sudo; no OS/firewall changes.
- Binds to **localhost only**.

## Quick start (Linux Jumpbox)

```bash
cd /home/jumpuser11/Desktop/Monitoring_Application
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD (never commit .env)

set -a && source .env && set +a
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000), sign in as **`admin`** with the password from `.env`.

If port 5000 is already in use on a shared Jumpbox:

```bash
export FLASK_PORT=5002
python run.py
```

On startup, if `ADMIN_PASSWORD` is set, the admin password hash is created or **reset** securely in SQLite. The local Jumpbox is auto-registered as a `local` server.

## Local monitoring

- Collector: `app/monitoring/local_collector.py` (psutil, read-only)
- Dashboard polls `GET /api/servers/metrics` every **10 seconds** (Chart.js); **Refresh now** for manual update
- Threshold colours: green &lt; 70%, orange 70–85%, red ≥ 85%
- Online when local collection succeeds

### Authenticated API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/servers` | Inventory (no key paths) |
| GET | `/api/servers/metrics` | All enabled servers |
| GET | `/api/servers/<id>/metrics` | One server |

Unauthenticated callers receive `401`.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Project layout

```
app/monitoring/   local psutil collector
app/api/          session-protected metrics JSON
templates/        login + live dashboard
static/js/        10s refresh + Chart.js
instance/         SQLite + generated secret (runtime, gitignored)
```
