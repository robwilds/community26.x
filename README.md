# Alfresco Community 26.x

This is a build of Alfresco Community 26.x with LDAP, a Python MCP server, LDAP server, and other goodies.

https://connect.hyland.com/t5/alfresco-blog/alfresco-community-edition-26-1-release-notes/ba-p/497107

## Getting Started

### Quick Start

```bash
./start_mgr.sh
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
- **▶ Show Logs** accordion — expands to show the last 20 log lines (fetched via `docker logs --tail 20 --timestamps`), collapsed by default
- **Dozzle ↗** link — opens that container's logs in Dozzle (http://localhost:9999)

Global controls:

- **Start All** / **Stop All** / **Restart All** buttons
- **Refresh** button
- Status badge showing `X/Y running` — green when all running, red otherwise

Services with `profiles: [donotstart]` are tagged with a badge and excluded from the default start.

### Available Files

Two tabs: **Content** (`installs/content/`) and **Share** (`installs/share/`).

Each file shows:

- **Install AMP** / **Install JAR** button — copies the file into the container and (for AMPs) runs `alfresco-mmt install`
  - Already-installed files show a disabled **(done)** button
  - Buttons are disabled when Docker is not running; a message indicates they will be enabled once Docker starts
- **Delete** button — removes the file from the directory, with a confirmation warning

Upload:

- **Upload File** button opens a file picker; any file type is accepted
- After upload, a `confirm()` dialog asks if you want to install `.jar` / `.amp` files immediately

### AMPs Panel

Alfresco and Share tabs, each showing installed modules in a table (Title, Version, ID). Below that, **Pending** shows AMP files in the container's `amps/` or `amps_share/` directory.

### JARs Panel

Alfresco and Share tabs, each listing `.jar` files in `WEB-INF/lib/` with a **Remove** button per file (deletes from the running container).

## Auto-Refresh

Container status refreshes every 10 seconds. Use the **Refresh** button to force-update all panels immediately.

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

## Demo Materials

- **`DEMO_SCRIPT.md`** — step-by-step walkthrough script for recording a video demo (11 scenes, ~7 minutes)
- **`Alfresco_Control_Plane_Features.pptx`** — PowerPoint presentation covering all features (dark theme, 10 slides)

## Technical Notes

- **AI assistance**: This project was built with [opencode](https://opencode.ai) using the zen mode with the `big-pickle` model.

- **Backend**: Single-file Python `http.server` (stdlib only). All Docker interaction via `subprocess.run`.
- **Frontend**: Single HTML file with inline CSS/JS. Zero dependencies. Uses `async/await`, Fetch API, `innerHTML` rendering.
- **Styling**: Dark theme via CSS variables, no frameworks.
- **File uploads**: Base64-encoded in JSON body (not multipart, since `http.server` has no multipart parser).
- **Service ordering**: `list_services()` sorts with alfresco (priority 0) and share (priority 1) first, then alphabetical.
- **Delete path validation**: `/api/delete-file` resolves the path and verifies it's within `installs/` to prevent directory traversal.

## MCP Server

The container `wildsalfmcp` starts an MCP server for use with Copilot or Claude Desktop.

For local models with a dedicated chat client, install [Ollama](https://ollama.com), pull a model (`ollama pull llama3`), restart Docker services, then access the **Open WebUI** interface at http://localhost:3000. Configure tools under Settings to point to http://localhost:8001.
