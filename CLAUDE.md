# Alfresco Community 26.x — Project Guide

## Overview

Docker Compose-based Alfresco Community 26.1 with governance, LDAP, transform services, and a Python MCP server. Includes a web-based control plane for managing containers, JARs, and AMPs at http://localhost:9700.

## Quick Commands

```bash
./start.sh                    # Start control plane at http://localhost:9700
docker compose up -d          # Start all services
python3 mgr/server.py         # Start control plane manually
```

## Project Structure

```
.
├── docker-compose.yaml       # All service definitions
├── commons/base.yaml         # Shared Compose config (traefik, proxy, content-app, etc.)
├── mgr/
│   ├── server.py             # Control plane HTTP API (Python stdlib, 1080 lines)
│   ├── static/index.html     # Control plane frontend (vanilla JS, 2394 lines)
│   └── data/
│       └── installed_jars.json # Persisted JAR tracking (only tracked = removable)
├── installs/
│   ├── content/              # AMPs/JARs for alfresco
│   └── share/                # AMPs/JARs for share
├── data/services/content/    # alfresco-global.properties, index.jsp, etc.
├── start.sh                  # Starts control plane + opens browser
├── AGENTS.md                 # Full agent context (most comprehensive reference)
├── DEMO_SCRIPT.md            # 12-scene demo walkthrough
└── MEMORY.md                 # Session history
```

## Control Plane API (mgr/server.py)

Single-file Python server using `http.server` (stdlib only). All Docker via `subprocess.run`.

### Key implementation details

- `list_services()` — merges `_parse_all_service_names()` (YAML parse) + `docker compose config --services`, gets status from `docker compose ps --format json`; sorts alfresco(0)/share(1) first
- `detect_containers()` — discovers container names via `docker compose ps -q` + `docker inspect`, calls `backfill_tracked_jars()` to sync JAR tracking
- `do_start()` — `docker compose up -d --pull missing`; start-all excludes profile-gated services; on failure runs `docker compose ps --format json` post-attempt to report per-service success/failure
- `do_install_amp()` — copy to container → MMT install (`--user root`) → rename .amp → .applied
- `do_uninstall_amp()` — MMT uninstall → remove matching .applied marker (or rename back to .amp if no local source) so it shows available again
- `do_install_jar()` — copy to `WEB-INF/lib/` + persist to `installed_jars.json`
- `_pull_images()` — background thread via `subprocess.Popen` with line-by-line streaming; state tracked in `_pull_state` dict with `_pull_lock`
- `_parse_compose_profiles()` — regex-based YAML scanner for `profiles: [donotstart]`
- `check_quay_images()` — uses `docker compose config --images` filtered to quay.io, checks `docker image inspect`
- File upload: base64 in JSON body (no multipart — http.server has no parser)
- Delete path validation: `path.resolve().relative_to(installs_dir.resolve())` prevents traversal

### All API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/services | All services with status, container ID, dozzle URL, profile |
| GET | /api/status | alfresco/share health (healthy/unhealthy) |
| GET | /api/amps | Installed + pending + available AMPs per service |
| GET | /api/jars | Installed + available JARs per service (removable flag) |
| GET | /api/local-files | Files in installs/ dirs with installed status |
| GET | /api/docker-status | Docker daemon (running/installed) |
| GET | /api/docker/quay-status | Cached quay.io images check |
| GET | /api/pull-status | Background pull streaming output |
| GET | /api/properties | Read alfresco-global.properties |
| GET | /api/logs/\<service> | Last 20 container log lines |
| POST | /api/start|stop|restart | Container lifecycle; on start failure inspects post-start state via `docker compose ps` for per-service reporting |
| POST | /api/properties | Write alfresco-global.properties |
| POST | /api/install/jar|amp | Deploy to container |
| POST | /api/uninstall/amp | MMT uninstall + remove .applied marker so AMP is available again |
| POST | /api/remove/jar | Delete from WEB-INF/lib |
| POST | /api/upload | Base64 file upload to installs/ |
| POST | /api/delete-file | Remove from installs/ (traversal safe) |
| POST | /api/launch-docker | `open -a Docker` |
| POST | /api/docker/login | `docker login quay.io --password-stdin` |
| POST | /api/pull | Background `docker compose pull` |

## Frontend (mgr/static/index.html)

Vanilla JS, zero dependencies. Dark theme CSS variables. Renders via `innerHTML`.

### UI sections
- **Services** — table with per-service Start/Stop/Restart, log accordion, Dozzle link, properties editor for alfresco, profile badges for donotstart
- **Available Files** — Content/Share tabs, Install AMP/JAR with (done) state, Delete, Upload, **Install All** batch button
- **AMPs** — All Services / Alfresco / Share tabs with Installed (table), Available, Pending sections
- **JARs** — same tab structure, only tracked JARs show Remove button

### State & refresh
- Global `state` object + `installing` map for button state
- Auto-refresh every 5s; fast-refresh at 1s during pending start/stop/restart
- `pendingAction` tracks start/stop/restart — resolves when all appropriate services reach target state

### Overlays
Docker (not installed / not running / waiting), Quay login (username+password, error display), Pull (streaming output, Skip), Restart prompt (after install), Alfresco ready (health probe), Start prompt (no services running), Guided tour (6 steps, localStorage)

## Docker Services

Key services: alfresco, share, postgres, solr6, activemq, transform-core-aio, content-app, control-center, proxy, dozzle, open-webui, wildsalfmcp, ldap, ldapadmin, email, webmail
Services with `profiles: [donotstart]` excluded by default: content-app, control-center

## VSCode MCP

`.vscode/mcp.json` configures SSE MCP server at `http://localhost:8000/sse` (wildsalfmcp container).
