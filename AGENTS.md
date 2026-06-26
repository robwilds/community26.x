# Project Context

Alfresco Community 26.x build with LDAP, Python MCP server, and additional services.

## Key Files

- `docker-compose.yaml` — All service definitions (Alfresco, Share, Solr6, Postgres, ActiveMQ, transform-core-aio, dozzle, etc.)
- `mgr/server.py` — Control plane HTTP server (Python stdlib http.server)
- `mgr/static/index.html` — Control plane frontend (vanilla JS, zero deps)
- `commons/base.yaml` — Shared Compose config (traefik labels, proxy, content-app, control-center)
- `mgr/data/installed_jars.json` — Persisted tracking of JAR files installed via control plane
- `start.sh` — Launches control plane server and opens http://localhost:9700
- `installs/content/` — AMPs/JARs for alfresco service
- `installs/share/` — AMPs/JARs for share service

## Control Plane (`mgr/`)

Web UI at `http://localhost:9700` for managing Docker services without CLI.

### Backend (`mgr/server.py`)

- Single-file Python server using `http.server` (stdlib only)
- All Docker interaction via `subprocess.run` wrapper
- JAR tracking persisted to `mgr/data/installed_jars.json` — only tracked JARs show Remove button
- Image pull runs in background thread with streaming output via `_pull_images()` + `_pull_lock`
- YAML profile parsing (`_parse_compose_profiles`) detects `profiles: [donotstart]` for badge display
- Service name extraction (`_parse_all_service_names`) reads docker-compose.yaml directly
- Quay image extraction via `docker compose config --images`
- AMP module ID detection from zipfile `module.properties`
- `.applied` file renaming convention: after AMP install, file is renamed `name.applied`
- Pending AMP filtering: AMPs in container's amps dir are filtered against MMT-installed module IDs
- Delete path validation resolves path and verifies it's within `installs/` to prevent traversal
- CORS headers (`Access-Control-Allow-Origin: *`) on all JSON responses

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/services` | List all Compose services with status, container_id, dozzle_url, profile_name |
| `GET` | `/api/status` | Container health for alfresco/share (healthy/unhealthy) |
| `GET` | `/api/amps` | Installed + pending + available AMPs (alfresco + share, with module IDs) |
| `GET` | `/api/available-amps` | AMPs in `installs/` not yet installed |
| `GET` | `/api/jars` | Installed + available JARs per service (with removable flag) |
| `GET` | `/api/available-jars` | JARs in `installs/` not yet deployed |
| `GET` | `/api/local-files` | Files in `installs/` dirs with installed status |
| `GET` | `/api/docker-status` | Docker daemon check (running/installed) |
| `GET` | `/api/docker/quay-status` | Check which quay.io images are cached locally |
| `GET` | `/api/pull-status` | Background pull progress (running/complete/output/error) |
| `GET` | `/api/properties` | Read `alfresco-global.properties` |
| `GET` | `/api/logs/<service>` | Last 20 log lines via `docker logs --tail 20 --timestamps` |
| `POST` | `/api/start` | Start container(s) with `docker compose up -d`; on failure inspects post-start state via `docker compose ps` to report per-service success/failure |
| `POST` | `/api/stop` | Stop container(s) with `docker compose stop` |
| `POST` | `/api/restart` | Restart container(s) with `docker compose restart` |
| `POST` | `/api/properties` | Write `alfresco-global.properties` |
| `POST` | `/api/install/jar` | Copy JAR into container's `WEB-INF/lib` |
| `POST` | `/api/install/amp` | Copy AMP + MMT install into container |
| `POST` | `/api/uninstall/amp` | MMT uninstall + revert .applied → .amp |
| `POST` | `/api/remove/jar` | Delete JAR from container |
| `POST` | `/api/upload` | Upload file (base64 JSON) to `installs/` |
| `POST` | `/api/delete-file` | Delete file from `installs/` (path traversal safe) |
| `POST` | `/api/launch-docker` | Launch Docker Desktop via `open -a Docker` |
| `POST` | `/api/docker/login` | Login to quay.io (`docker login quay.io --password-stdin`) |
| `POST` | `/api/pull` | Start background `docker compose pull` |

### Frontend (`mgr/static/index.html`)

- Vanilla JS, single HTML file, zero dependencies (2394 lines)
- Global state in `state` object, install tracking in `installing` map
- Renders via `innerHTML` with `esc()` / `escAttr()` helpers for XSS safety

#### UI Panels

- **Services panel** — sorted with alfresco/share first, per-service Start/Stop/Restart buttons, collapsible log accordion, Dozzle ↗ link, profile badge for donotstart services, inline alfresco-global.properties editor, animated Alfresco wait banner; services transitioning to running show an animated "starting…" indicator with pulsing dot
- **Available Files** — grouped by Content/Share tabs, Install AMP/JAR buttons with (done) state, Delete with warning, Upload File, **Install All** button
- **AMPs panel** — installed modules (title, version, ID, service badge) with Remove, Available (in installs/) with Install, Pending (filtered against MMT), All Services/Alfresco/Share tabs
- **JARs panel** — installed JARs (only tracked ones show Remove), Available with Install, All Services tab with service badges

#### Overlays & Prompts

- **Docker overlay** — three states: not installed (Download Docker Desktop link), not running (Launch Docker + Check Again), waiting (polls every 500ms)
- **Quay login overlay** — username/password form, shows missing images count, error display
- **Pull overlay** — streaming `docker compose pull` output, Skip (start anyway) button
- **Restart prompt** — shows after install/AMP uninstall, "Restart Now" or "Later"
- **Alfresco ready overlay** — when alfresco health probe passes after transition from stopped
- **Start prompt** — "Docker is ready but no services running — Start All?"
- **Guided tour** — 6-step overlay tour on first visit (tracked via localStorage), restartable via `?` button

#### Auto-Refresh

- Services/AMPs/JARs/files refresh every 5 seconds
- During pending start/stop/restart actions, fast-refresh at 1s intervals via `startFastRefreshUntil()` — applies to both **Start All** and individual **Start/Restart** buttons
- A `startingServices` Set tracks per-service start requests and shows a "starting…" indicator on the service row until the container reports healthy
- Pending action completes when all (appropriate) services reach target state

#### Click Handler Pattern

- Uses `event.target` in `toggleLogs()` to find the toggle button
- Install buttons show "Installing..." state and are disabled during operation
- Creates and appends DOM nodes for toast dismiss buttons (not innerHTML)

### Conventions

- **Python:** stdlib only, `subprocess.run` wrapper for Docker commands, `http.server` with manual JSON serialization
- **JS:** `async/await`, `fetch` API, `innerHTML` for rendering, anonymous functions in render callbacks
- **CSS:** dark theme CSS variables (--bg, --card, --border, --text, --muted, --accent, etc.), no frameworks
- **Docker:** `docker compose` v2 commands, `cwd=str(PROJECT_ROOT)` for compose operations
- **AMP lifecycle:** copy to container → MMT install → rename .amp → .applied; uninstall reverses via MMT + renames back
- **JAR tracking:** only JARs installed through the UI are removable (stored in `mgr/data/installed_jars.json`)
- **Styling:** Hyland teal/gold brand colors, Inter font from Google Fonts, Hyland SVG logo in header
