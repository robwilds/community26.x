# Project Context

Alfresco Community 26.x build with LDAP, Python MCP server, and additional services.

## Key Files

- `docker-compose.yaml` — All service definitions (Alfresco, Share, Solr6, Postgres, ActiveMQ, transform-core-aio, dozzle, etc.)
- `mgr/server.py` — Control plane HTTP server (Python stdlib http.server)
- `mgr/static/index.html` — Control plane frontend (vanilla JS, zero deps)
- `commons/base.yaml` — Shared Compose config

## Control Plane (`mgr/`)

Web UI at `http://localhost:9700` for managing Docker services without CLI.

### Backend (`mgr/server.py`)

- Single-file Python server using `http.server` (stdlib only)
- API endpoints:
  - `GET /api/services` — List Compose services with status, container_id, dozzle_url
  - `GET /api/status` — Container health for alfresco/share
  - `GET /api/amps` — Installed + pending + available AMPs (with module IDs)
  - `GET /api/available-amps` — AMPs in `installs/` not yet installed
  - `GET /api/jars` — Installed + available JARs per service
  - `GET /api/available-jars` — JARs in `installs/` not yet deployed
  - `GET /api/local-files` — Files in `installs/` directories
  - `GET /api/docker-status` — Docker daemon check
  - `GET /api/logs/<service>` — Last 20 log lines via `docker logs`
  - `POST /api/start|stop|restart` — Container lifecycle
  - `POST /api/install/jar|amp` — Install into container
  - `POST /api/remove/jar` — Remove JAR from container
  - `POST /api/upload` — Upload file (base64 JSON) to `installs/`
  - `POST /api/delete-file` — Delete file from `installs/`
  - `POST /api/launch-docker` — Launch Docker Desktop

### Frontend (`mgr/static/index.html`)

- Vanilla JS, single HTML file, zero dependencies
- **Services panel** — sorted with alfresco/share first, collapsible log accordion per service, Dozzle ↗ link
- **Available Files** — grouped by Content/Share tabs, Install AMP/JAR buttons, Upload File, Delete File with warning, post-upload install prompt
- **AMPs panel** — installed modules (title, version, ID) with Remove, Available (in installs/) with Install, Pending (filtered against MMT), plus an All Services tab
- **JARs panel** — installed JARs with Remove, Available (in installs/) with Install, all three tabs (Alfresco/Share/All Services) with service badges
- Auto-refresh services every 10s
- Uses `event.target` for button state in click handlers

### Conventions

- Python: stdlib only, `subprocess.run` wrapper for Docker commands
- JS: `async/await`, `fetch` API, `innerHTML` for rendering
- CSS: dark theme CSS variables, no frameworks
- Docker: `docker compose` v2 commands, `cwd=str(PROJECT_ROOT)`
