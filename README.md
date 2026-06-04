# Alfresco Community 26.x

This is a build of Alfresco Community 26.x with LDAP, a Python MCP server, LDAP server, and other goodies.

https://connect.hyland.com/t5/alfresco-blog/alfresco-community-edition-26-1-release-notes/ba-p/497107

## Getting Started

```bash
docker compose up -d
```

Login with **demo / demo**.

After services start, run `./install_all.sh` to install OOTBEE Support Tools (https://github.com/OrderOfTheBee/ootbee-support-tools), a mechanism to execute HTTPClient-style transactions from JavaScript in a rule, and a custom Hyland theme JAR (select from Admin → Theme).

## Alfresco Control Plane

A web-based management UI at `mgr/` for managing Docker services, JARs, and AMPs without the CLI.

### Quick Start

```bash
./start_mgr.sh
```

Opens http://localhost:9700. If Docker isn't running, a prompt appears with **Launch Docker** and **Check Again** buttons.

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
- **Delete** button — removes the file from the directory, with a confirmation warning

Upload:
- **Upload File** button opens a file picker; any file type is accepted
- After upload, a `confirm()` dialog asks if you want to install `.jar` / `.amp` files immediately

### AMPs Panel

Installed modules listed in a table (Title, Version, ID). Below that, **Pending** shows AMP files in the container's `amps/` or `amps_share/` directory.

### JARs Panel

Lists all `.jar` files in `WEB-INF/lib/` with a **Remove** button per file (deletes from the running container).

## Auto-Refresh

Container status refreshes every 10 seconds. Use the **Refresh** button to force-update all panels immediately.

## Technical Notes

- **Backend**: Single-file Python `http.server` (stdlib only). All Docker interaction via `subprocess.run`.
- **Frontend**: Single HTML file with inline CSS/JS. Zero dependencies. Uses `async/await`, Fetch API, `innerHTML` rendering.
- **Styling**: Dark theme via CSS variables, no frameworks.
- **File uploads**: Base64-encoded in JSON body (not multipart, since `http.server` has no multipart parser).
- **Service ordering**: `list_services()` sorts with alfresco (priority 0) and share (priority 1) first, then alphabetical.
- **Delete path validation**: `/api/delete-file` resolves the path and verifies it's within `installs/` to prevent directory traversal.

## MCP Server

The container `wildsalfmcp` starts an MCP server for use with Copilot or Claude Desktop.

For local models with a dedicated chat client, install [Ollama](https://ollama.com), pull a model (`ollama pull llama3`), restart Docker services, then access the **Open WebUI** interface at http://localhost:3000. Configure tools under Settings to point to http://localhost:8001.
