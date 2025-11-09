# SOC Dashboard (Team 42)

## Layout
- `app.py`                 : Flask/FastAPI app (entrypoint)
- `data/`                  : Canonical runtime data (alerts.json, services.json)
- `apps/`                  : Supporting scripts/apps
- `archive/`               : Old backups & legacy copies (not used at runtime)
- `apps/soc-dashboard/data` -> symlink to `data/` (compatibility)
- `DATA`                   -> symlink to `data/` (compatibility)

## Environment
- Use Python 3.10+ and a venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt` (if present)

## Data Files
- `data/alerts.json`    : SOC alerts feed (Suricata/auth/nftables correlation)
- `data/services.json`  : Service status for dashboard cards

## Notes
Do not write to `apps/soc-dashboard/data` or `DATA` directly—both link to `data/`.
