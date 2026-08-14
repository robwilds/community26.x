# Alfresco Community 26.x — Agent Context

## Commands

```bash
./start.sh                         # Control plane at http://localhost:9700 + opens browser
python3 mgr/server.py              # Control plane only (no auto-open)
```

## Architecture

- **Python backend** (`mgr/server.py`): stdlib `http.server`, all Docker via `subprocess.run`. JSON responses use manual `json.dumps`; no framework.
- **JS frontend** (`mgr/static/index.html`): 2394 lines, vanilla JS, dark theme CSS vars, zero deps. Features a header with Alfresco/Kibana service links, global controls, and a dark/light mode toggle with moon/sun icon.
- AMP lifecycle: copy into container → MMT install with `--user root` → rename `.amp` → `.applied`. Uninstall via MMT + remove the `.applied` marker (falls back to renaming it back to `.amp` if no matching source exists in `installs/`), so the source AMP shows up as available again. Only JARs installed through the UI are removable (tracked in `mgr/data/installed_jars.json`).
- File upload is base64 JSON body (no multipart parser). Delete paths are resolved relative to `installs/*`.

## Service model

`docker-compose.yaml` defines 18 services; the default `docker compose up -d` (and the UI's **Start All**, which mirrors it via `do_start`) starts the 12 non-profile-gated ones. 6 services behind `profiles: [donotstart]` (`content-app`, `control-center`, `open-webui`, `wildsalfmcp`, `email`, `webmail`) are omitted by default but startable via the per-service button or CLI. Container names come from `docker compose ps`, not `docker-compose.yaml` service keys (project-name agnostic).

Service↔directory mapping for installs: `installs/content/` → alfresco (`amps/`, `webapps/alfresco`); `installs/share/` → share (`amps_share/`, `webapps/share`). The properties editor reads/writes `data/services/content/alfresco-global.properties` (bind-mounted into the container).

## Gotchas

- AMP install needs `--user root`; skipping it causes IO errors because webapps/WEB-INF belong to root, container runs as non-root.
- MMT jar path is resolved at runtime via `_resolve_mmt_jar()` (`docker exec ls /usr/local/tomcat/alfresco-mmt/*.jar`) so image upgrades are picked up automatically; `DEFAULT_MMT_JAR` is only a fallback.
- Start error reporting uses `docker compose ps --format json` post-attempt for per-service success/failure; don't assume the batch failed only if any single service reports error on this basis.
- Background pull (`docker compose pull`) streams line-by-line through a thread-safe `_pull_state` dict protected by lock.
