# Demo Infrastructure Monitoring Application

Local demo dashboard for Linux Jumpbox monitoring.  
**Status:** Local psutil monitoring, inventory, optional SSH remotes, and labelled demo servers.

| Item | Value |
|------|--------|
| Bind | `127.0.0.1:5000` |
| Stack | Python, Flask, Flask-WTF, SQLite, Bootstrap, Chart.js, psutil, Paramiko |
| Deploy | Local Jumpbox only (`python run.py`). No Docker. |
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
- Dashboard and server detail poll every **10 seconds** (Chart.js); **Refresh now** for a manual update
- Threshold colours: green &lt; 70%, orange 70–85%, red ≥ 85%
- Click a server name to open its detail page
- Online when collection succeeds; a failed host stays offline and does not stop the others

## Inventory

Open **Servers** (`/inventory`) while signed in.

| Field | Meaning |
|-------|---------|
| Name | Display name |
| Type | `remote` (SSH) or `demo` (simulated, labelled) |
| Host | Hostname or IP |
| SSH port / username / key path | Remote only. The database stores the **path**, not the key |

The local Jumpbox is registered automatically and is not removed. The demo cap is **5** servers. Add and remove forms use CSRF.

## Remote SSH

Set a remote row with a private key path on this Jumpbox. Before it can come online:

1. The key file must exist and be readable by your user.
2. The host key must already be in `~/.ssh/known_hosts` (connect once with `ssh`). Unknown keys are rejected.
3. Optional env: `SSH_CONNECT_TIMEOUT` (default 10) and `SSH_COMMAND_TIMEOUT` (default 8).

Commands are read-only (`/proc`, `free`, `df`, `ss`). No password SSH.

### If a remote stays offline

| Message | What to check |
|---------|----------------|
| SSH connection timed out | Host, port, network path, timeout values |
| SSH private key file is missing | Key path on the Jumpbox |
| Host key verification failed | `known_hosts` entry for that host |
| SSH authentication failed | Username and key pair |

## Demo mode

Set `DEMO_MODE=true` to seed **Simulated-Web-01**, **Simulated-App-01**, and **Simulated-DB-01** when there is room under the 5-server cap. They are marked **Simulated** and do not use SSH. Set `DEMO_MODE=false` to stop seeding new ones (existing rows remain until removed).

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `pytest` on push and pull request with dummy `SECRET_KEY` and `ADMIN_PASSWORD`. It does not need a Jumpbox or real SSH keys. The job fails if tests fail.

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
