# Info

This is a build of Alfresco community 26.x with ldap, a python mcp server and ldap server and other goodies.

https://connect.hyland.com/t5/alfresco-blog/alfresco-community-edition-26-1-release-notes/ba-p/497107

# Getting Started

Run "docker compose up -d" from command line within the root directory of this project.

Login with demo/demo.

After services start you can run ./install_all.sh in the root to load up
OOTBEE tools (https://github.com/OrderOfTheBee/ootbee-support-tools)
and a mechanism to execute httpclient style transactions from a javascript in a rule. There's also a custom hyland theme jar - select the theme from the admin view

Pretty straight forward...

## Alfresco Control Plane

A web UI at `mgr/` for managing Docker services, JARs, and AMPs without using the CLI.

### Quick Start

```
./start_mgr.sh
```

This launches the server at http://localhost:9700 and automatically opens your browser. The script waits for the server to be ready before opening the page.

If Docker is not running, the UI shows a prompt with a **Launch Docker** button. It then polls every 500ms and loads the dashboard once Docker is ready.

### Manual Start

```
python3 mgr/server.py
```

### Dashboard

- **Services panel** — health check for all docker compose services, with Start, Stop, and Restart per-service and global Start All / Stop All / Restart All / Refresh buttons
- **Available Files tab** — shows files in `installs/content/` and `installs/share/` with one-click Install AMP / Install JAR buttons. Already-installed files are shown with a disabled `(done)` button.
- **AMPs tab** — lists installed modules (with title, version, ID) and pending AMPs in the container's amps directory
- **JARs tab** — lists all JARs in WEB-INF/lib with per-file Remove button
- Auto-refreshes container status every 10 seconds. Uses zero dependencies (vanilla JS, Python stdlib only).

### note

There's a container called wildsalfmcp that will start up an MCP server for use with coPilot or Claude desktop etc.

If you want to run a local model with a dedicated chat client, you must install ollama on your computer. Once installed pull a model in terminal (ollama pull llama3). The start (or restart) the doocker services. You can access the open-webui interface with http://localhost:3000. Configure the tools under settings to point to http://localhost:8001
