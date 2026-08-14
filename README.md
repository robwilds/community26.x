# Alfresco Community 26.x

This is a build of Alfresco Community 26.x with LDAP, a Python MCP server, LDAP server, and other goodies.

https://connect.hyland.com/t5/alfresco-blog/alfresco-community-edition-26-1-release-notes/ba-p/497107

## Getting Started

### Quick Start

```bash
./start.sh
```

Opens http://localhost:9700 with a Hyland-branded header. On page load, Docker presence is checked. If Docker is unavailable, an overlay prompts accordingly:

- **Docker not installed** — shows a **Download Docker Desktop** link (opens docker.com) and a **Check Again** button.
- **Docker not running** — shows **Launch Docker** (opens Docker Desktop) and **Check Again** buttons, then polls until Docker is ready.

### Manual Start

```bash
python3 mgr/server.py
```

### Services Panel

Lists all services from `docker-compose.yaml` sorted with **alfresco** and **share** first, then alphabetically.

Per-service controls:

- **Start** / **Stop** / **Restart** buttons
- **"starting…" indicator** — when a service is starting (via bulk or per-service start), its status row shows an animated pulsing dot with "starting…" text that persists until the container reports healthy
- **▶ Show Logs** accordion — expands to show the last 20 log lines (fetched via `docker logs --tail 20 --timestamps`), collapsed by default
- **Dozzle ↗** link — opens that container's logs in Dozzle (http://localhost:9999)
- **▶ Edit Global Properties** button (alfresco only) — inline textarea editor for `alfresco-global.properties` with Save/Discard & Reload buttons and a status indicator

Global controls:

- **Start All** / **Stop All** / **Restart All** buttons
- **Refresh** button
- Status badge showing `X/Y running` — green when all running, red otherwise
- **Open Alfresco** / **Kibana** links — appear in the header when respective services are running (Alfresco on port 8080, Kibana on port 5601)
- Dark mode toggle button with moon/sun icon in the header

Services with `profiles: [donotstart]` are tagged with a badge and excluded from the default start.

### Available Files

Two tabs: **Content** (`installs/content/`) and **Share** (`installs/share/`).

Each file shows:

- **Install AMP** / **Install JAR** button — copies the file into the container and (for AMPs) runs `alfresco-mmt install`
  - Already-installed files show a disabled **(done)** button
  - Buttons are disabled when Docker is not running; a message indicates they will be enabled once Docker starts
- **Delete** button — removes the file from the directory, with a confirmation warning

- **Install All** button — batch-installs all uninstalled JARs and AMPs in sequence, with a progress counter (`X/Y`) shown on the button

Upload:

- **Upload File** button opens a file picker; any file type is accepted
- After upload, a `confirm()` dialog asks if you want to install `.jar` / `.amp` files immediately

### AMPs Panel

Alfresco and Share tabs, plus an **All Services** tab aggregating both. Each tab shows:

- **Installed** — modules in a table (Title, Version, ID) with a **Remove** button per module (MMT uninstall; the module then reappears in **Available** for reinstall)
- **Available (in installs/)** — AMP files from the local `installs/` directory not yet installed, with **Install** buttons
- **Pending** — AMP files in the container's `amps/` or `amps_share/` directory (filtered to exclude AMPs already installed via MMT)

### JARs Panel

Alfresco and Share tabs, plus an **All Services** tab with service badges. Each tab shows:

- **Installed** — `.jar` files in `WEB-INF/lib/` with a **Remove** button per file (deletes from the running container; only JARs installed through the UI are removable)
- **Available (in installs/)** — JAR files from the local `installs/` directory not yet deployed, with **Install** buttons

### Quay Login &amp; Pull Images

When the **Start All** button is clicked, the UI first checks for missing quay.io images:

- If images need to be pulled, a **Quay.io Login** overlay prompts for quay.io credentials (username + password/token). After successful login, a **Pull** overlay opens showing streaming `docker compose pull` output with a **Skip (start anyway)** button.
- If all images are cached, the pull step is skipped and containers start immediately.
- The **Quay** button in the header can manually trigger the login flow at any time.

The pull runs in a background thread (`_pull_images()`) on the Python server, streaming line-by-line to the `GET /api/pull-status` endpoint, which the frontend polls every 600ms.

### Restart Prompt

After installing an AMP, JAR, saving properties, or uninstalling an AMP, a **Restart Required** overlay appears asking to restart the container. Click **Restart Now** to restart immediately, or **Later** to dismiss. When restarting Alfresco, an animated wait banner appears at the top of the page with a spinning Alfresco logo.

## Auto-Refresh

All panels (services, AMPs, JARs, files) refresh every 5 seconds. During a pending start, stop, or restart action (both **Start All** and individual **Start/Restart**), the refresh interval accelerates to 1 second via `startFastRefreshUntil()`. The pending action completes when all appropriate services (excluding `donotstart` profile) reach the target state. Use the **Refresh** button to force-update all panels immediately.

## Guided Tour

On first visit, a **guided tour** appears 2 seconds after data loads, walking through 6 areas of the UI:

1. **Service Controls** — Start All / Stop All / Restart All buttons
2. **Services Table** — per-service status and Start/Stop/Restart
3. **Logs &amp; Monitoring** — Show Logs accordion and Dozzle ↗ link
4. **File Management** — Upload, Install, and Delete
5. **Installed Modules** — AMPs panel with installed + pending lists
6. **Library JARs** — WEB-INF/lib listing with Remove

Each step dims the background, highlights the target element, and floats a tooltip with an **OK** button to advance. Click **Skip tour** at any point to dismiss. The tour runs only once per browser (tracked via `localStorage`).

To restart the tour on demand, click the **`?`** button in the top-right header next to Refresh.

## Alfresco Ready Prompt

When the Alfresco service transitions from stopped to running and its health probe returns healthy, a popup overlay asks if you'd like to open Alfresco at http://localhost:8080/alfresco. Click **Open Alfresco** to launch it in a new tab, or **Not now** to dismiss. The **Open Alfresco ↗** link in the header also appears whenever any services are running.

While waiting for Alfresco to become healthy (e.g., during start or restart), an animated Alfresco logo banner displays at the top of the page. The petals cycle through green, blue, orange, and yellow colors. The banner disappears once the health probe passes or the prompt is shown.

## Demo Materials

- **`DEMO_SCRIPT.md`** — step-by-step walkthrough script for recording a video demo (12 scenes, ~8 minutes) covering services, logs, Dozzle, guided tour, file upload/install/delete, AMPs, JARs, Alfresco ready prompt, and Docker startup flows
- **`Alfresco_Control_Plane_Features.pptx`** — PowerPoint presentation covering all features (dark theme)

## Technical Notes

- **AI assistance**: This project was built with [opencode](https://opencode.ai) using the zen mode with the `big-pickle` model.

- **Backend**: Single-file Python `http.server` (stdlib only). All Docker interaction via `subprocess.run`.
- **Frontend**: Single HTML file with inline CSS/JS. Zero dependencies (2394 lines). Uses `async/await`, Fetch API, `innerHTML` rendering.
- **Styling**: Dark theme via CSS variables (--bg, --card, --border, --text, --accent, etc.), Hyland brand colors (teal #13eac1, gold #f1cb61), Inter font.
- **File uploads**: Base64-encoded in JSON body (not multipart, since `http.server` has no multipart parser).
- **Service ordering**: `list_services()` sorts with alfresco (priority 0) and share (priority 1) first, then alphabetical.
- **Profile detection**: `_parse_compose_profiles()` uses regex to parse `profiles: [donotstart]` from the YAML directly for badge display.
- **Service name extraction**: `_parse_all_service_names()` reads `docker-compose.yaml` directly to capture all services (including profile-gated ones). Merged with `docker compose config --services` output.
- **AMP lifecycle**: Files are renamed `.amp` → `.applied` after MMT install. Uninstall runs MMT and removes the matching `.applied` marker from the container (or reverts it to `.amp` if no source exists in `installs/`), so the AMP shows up as **Available** again for reinstall.
- **JAR tracking**: Only JARs installed through the UI are removable. Persisted to `mgr/data/installed_jars.json`.
- **Background pull**: `docker compose pull` runs in a background threading with line-by-line streaming. State tracked via `_pull_state` dict protected by `_pull_lock`.
- **Delete path validation**: `/api/delete-file` resolves the path and verifies it's within `installs/` to prevent directory traversal.
- **Auto-refresh**: 5s cycle; accelerates to 1s during pending start/stop/restart actions via `startFastRefreshUntil()`; `pendingAction` resolves when all appropriate services reach target state.
- **Container detection**: `detect_containers()` uses `docker compose ps -q` + `docker inspect` to discover actual container names (project-name agnostic).
- **Start error reporting**: `do_start()` runs `docker compose up -d` as a batch, but on failure inspects `docker compose ps --format json` post-attempt to report per-service results — services that started are marked `"started"`, only failed services get the Docker error message.

## MCP Server

The container `wildsalfmcp` starts an MCP server for use with Copilot or Claude Desktop.

For local models with a dedicated chat client, install [Ollama](https://ollama.com), pull a model (`ollama pull llama3`), restart Docker services, then access the **Open WebUI** interface at http://localhost:3000. Configure tools under Settings to point to http://localhost:8001.
