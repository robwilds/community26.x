# Session Memory

## Project
Alfresco Community 26.x local dev stack — Docker Compose with Alfresco, Share, Solr, ActiveMQ, PostgreSQL, LDAP, AI services.

## Prompts & Actions

### 1. Analyze the codebase
Explored the project structure — Docker Compose stack, installs directory, configs, custom services (wildsalfmcp, queryalfapi, Open WebUI).

### 2. Review install_all.sh
Identified issues: hardcoded container names, hardcoded MMT version, no container restart after install, no error handling, `--user root` missing for AMP install (webapps owned by root but container runs as `alfresco` user).

### 3. Fix install_all.sh
Rewrote script with:
- Dynamic container name discovery via `docker compose ps` + `docker inspect`
- Dynamic MMT version discovery via glob inside container
- `--user root` on MMT install command
- Container restart after install
- Health wait loop after restart
- `set -euo pipefail` and project root validation

### 4. Run install_all.sh
Ran the script — installed 3 JARs + 1 AMP to alfresco, 1 JAR + 1 AMP to share. Initial run revealed the `--user root` bug (IO error on AMP install). Fixed and re-ran successfully.

### 5. Create management UI
Created `mgr/server.py` (Python stdlib HTTP server) and `mgr/static/index.html` (vanilla JS) — a dark-themed web interface on port 9700 with:
- Container health status
- Installed AMPs + pending AMPs view (alfresco/share tabs)
- JAR listing with remove button
- Local files from `installs/` with one-click Install AMP / Install JAR
- Restart All button

### 6. Start manager
Ran server on localhost:9700.

### 7. Update README
Added "Alfresco Manager" section documenting the mgr/ tool, its features, and how to start it.

### 8. Add start option to mgr
Added `/api/start` POST endpoint and "Start All" button to the manager UI.

### 9. Reference docker-compose.yaml for start
Changed `do_start` to run `docker compose up -d` (no service filter) so all compose services start, not just alfresco/share.

### 10. Services panel with per-container control
Added `/api/services` endpoint that lists all services from `docker-compose.yaml` with running status and donotstart profile info. New Services card in UI shows every container with Start/Stop/Restart buttons. Header shows running/total summary.

### 11. Stop + Restart per service
Added `do_stop()` (`docker compose stop`) and switched `do_restart()` to `docker compose restart` so any service can be controlled. Added `/api/stop` endpoint. UI now shows Start (stopped) or Restart+Stop (running) per service row.

### 12. Updated agent guide files (this session)
Rewrote AGENTS.md, CLAUDE.md, and README.md with comprehensive documentation of all API endpoints, frontend features, overlays/quay-login/pull, properties editor, restart prompt, auto-refresh with fast-refresh, batch "Install All", AMP lifecycle, JAR tracking, background pull threading, YAML profile parsing, and container detection.

## Files Created/Modified
- `install_all.sh` — rewritten (dynamic container/MMT detection, root user, restart, health wait)
- `mgr/server.py` — management API server
- `mgr/static/index.html` — management UI
- `README.md` — comprehensive rewrite covering all features
- `AGENTS.md` — rewritten with full API/UI/implementation documentation
- `CLAUDE.md` — rewritten with accurate structure, commands, all endpoints
- `MEMORY.md` — this file

## Key Decisions
- Management server uses Python stdlib only (zero dependencies)
- UI uses vanilla JS (no framework)
- Manager runs outside Docker (talks to Docker socket via CLI)
- AMP install requires `--user root` due to filesystem ownership in containers
- Script auto-discovers container names to be project-name agnostic
- Services panel reads compose file directly via `docker compose config --services` + YAML profile parsing
- Service control uses `docker compose` subcommands (up/stop/restart) rather than raw `docker` commands for compose-aware orchestration
