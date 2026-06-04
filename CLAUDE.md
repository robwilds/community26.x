# Alfresco Community 26.x — Project Guide

## Overview

Docker Compose-based Alfresco Community 26.1 with governance, LDAP, transform services, and a Python MCP server. Includes a web-based control plane for managing containers, JARs, and AMPs.

## Quick Commands

```bash
./start_mgr.sh              # Start control plane at http://localhost:9700
docker compose up -d        # Start all services
python3 mgr/server.py       # Start control plane manually
```

## Project Structure

```
.
├── docker-compose.yaml       # All service definitions
├── commons/base.yaml         # Shared Compose config (content-app, control-center, proxy)
├── mgr/
│   ├── server.py             # Control plane HTTP API (Python stdlib)
│   ├── static/index.html     # Control plane frontend (vanilla JS)
├── installs/
│   ├── content/              # Uploaded AMPs/JARs for alfresco
│   └── share/                # Uploaded AMPs/JARs for share
├── data/services/            # Service-specific configs
├── install_all.sh            # Install OOTBEE tools and extras
```

## Control Plane API

The server at `mgr/server.py` exposes REST endpoints under `/api/`. All responses are JSON. The frontend at `mgr/static/index.html` consumes these endpoints.

### Key Implementation Details

- `list_services()` — runs `docker compose config --services` then `docker compose ps --format json`; sorts with alfresco/share first
- `get_container_id(service)` — returns container ID via `docker compose ps -q`
- `fetch_logs(container_id)` — runs `docker logs --tail 20 --timestamps`
- File uploads use base64 in JSON body (not multipart, since http.server doesn't parse it well)
- Delete endpoint validates path is within `installs/` to prevent traversal
- Post-upload `confirm()` dialog asks to install AMPs/JARs immediately

## Docker Services

Key services: alfresco, share, postgres, solr6, activemq, transform-core-aio, content-app, control-center, proxy, dozzle, queryalfapi, open-webui, mcpo, wildsalfmcp, ldap, ldapadmin, email, webmail

Services with `profiles: [donotstart]` are excluded by default.

## Dozzle Integration

Dozzle runs on port 9999. The control plane shows a "Dozzle ↗" link per service and a collapsible log accordion that fetches the last 20 log lines via `docker logs`.
