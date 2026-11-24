# SQLite schema (demo)

Database file: `instance/monitor.db` (gitignored).

## `users`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| username | TEXT UNIQUE | Demo user: `admin` |
| password_hash | TEXT | Werkzeug hash only |
| created_at | TEXT | ISO-8601 UTC |

## `servers`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | Display name |
| host | TEXT | Hostname/IP |
| ssh_port | INTEGER | Default 22 (remote later) |
| ssh_username | TEXT | Remote later |
| ssh_key_path | TEXT | Path reference only — never key material |
| server_type | TEXT | `local` (Jumpbox via psutil); remote/demo later |
| enabled | INTEGER | 1/0 |
| created_at | TEXT | ISO-8601 UTC |

The local Jumpbox row is auto-registered on application start.
