#!/usr/bin/env python3
import http.server
import json
import os
import shlex
import subprocess
import urllib.parse
from pathlib import Path

HOST = "0.0.0.0"
PORT = 9700
STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).parent.parent

ALFRESCO_CONTAINER = None
SHARE_CONTAINER = None


def docker_is_running():
    r = run(["docker", "info"], timeout=5)
    return r.returncode == 0


def run(cmd, **kwargs):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=kwargs.pop("timeout", 30), **kwargs
    )


def detect_containers():
    global ALFRESCO_CONTAINER, SHARE_CONTAINER
    r = run(
        ["docker", "compose", "ps", "-q", "alfresco"],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode == 0 and r.stdout.strip():
        cid = r.stdout.strip().splitlines()[0]
        r2 = run(["docker", "inspect", "--format", "{{.Name}}", cid])
        if r2.returncode == 0:
            ALFRESCO_CONTAINER = r2.stdout.strip().lstrip("/")
    r = run(
        ["docker", "compose", "ps", "-q", "share"],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode == 0 and r.stdout.strip():
        cid = r.stdout.strip().splitlines()[0]
        r2 = run(["docker", "inspect", "--format", "{{.Name}}", cid])
        if r2.returncode == 0:
            SHARE_CONTAINER = r2.stdout.strip().lstrip("/")


def get_container_id(service):
    r = run(["docker", "compose", "ps", "-q", service], cwd=str(PROJECT_ROOT))
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def fetch_logs(container_id, lines=20):
    r = run(
        ["docker", "logs", container_id, "--tail", str(lines), "--timestamps"],
        timeout=10,
    )
    if r.returncode != 0:
        return []
    return (r.stdout + r.stderr).rstrip("\n").splitlines()


def list_services():
    r = run(
        ["docker", "compose", "config", "--services"],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode != 0:
        return []
    services = r.stdout.strip().splitlines()
    r2 = run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=str(PROJECT_ROOT),
    )
    running = set()
    cids = {}
    if r2.returncode == 0 and r2.stdout.strip():
        import json as _json
        for line in r2.stdout.strip().splitlines():
            try:
                info = _json.loads(line)
                svc = info.get("Service")
                if info.get("State") == "running":
                    running.add(svc)
                if svc:
                    cids[svc] = info.get("ID") or info.get("Id") or ""
            except Exception:
                pass
    profiles = _parse_compose_profiles()
    result = [
        {
            "name": s,
            "running": s in running,
            "profile": s in profiles.get("donotstart", []),
            "container_id": cids.get(s, ""),
        }
        for s in services
    ]
    priority = {"alfresco": 0, "share": 1}
    result.sort(key=lambda x: (priority.get(x["name"], 2), x["name"]))
    for svc in result:
        if svc["container_id"]:
            svc["dozzle_url"] = f"http://localhost:9999/container/{svc['container_id']}"
        else:
            svc["dozzle_url"] = None
    return result


def _parse_compose_profiles():
    profiles = {}
    try:
        text = Path(PROJECT_ROOT / "docker-compose.yaml").read_text()
        import re
        current = None
        in_profiles = False
        for line in text.splitlines():
            m = re.match(r"^  (\S+):", line)
            if m and not line.startswith("   "):
                current = m.group(1)
                in_profiles = False
            if current and "profiles:" in line:
                in_profiles = True
                continue
            if in_profiles and re.match(r"^\s+- ", line):
                p = line.strip().lstrip("- ")
                profiles.setdefault(p, []).append(current)
            elif in_profiles and line.strip() and not line.startswith(" " * 6):
                in_profiles = False
    except Exception:
        pass
    return profiles


def read_file(path):
    try:
        return Path(path).read_text()
    except Exception:
        return None


def api_list_amps(container):
    if not container:
        return {"error": "container not found"}
    r = run(
        [
            "docker",
            "exec",
            container,
            "java",
            "-jar",
            "/usr/local/tomcat/alfresco-mmt/alfresco-mmt-26.1.0.61.jar",
            "list",
            "/usr/local/tomcat/webapps/alfresco"
            if "alfresco" in container
            else "/usr/local/tomcat/webapps/share",
        ]
    )
    amps = []
    if r.returncode == 0:
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("Module"):
                amps.append({"id": line.split("'")[1], "status": "installed"})
            elif line.startswith("Title:"):
                if amps:
                    amps[-1]["title"] = line.split(":", 1)[1].strip()
            elif line.startswith("Version:"):
                if amps:
                    amps[-1]["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("Install Date:"):
                if amps:
                    amps[-1]["installed"] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                if amps:
                    amps[-1]["description"] = line.split(":", 1)[1].strip()
    return amps


def api_list_jars(container):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if "alfresco" in container else "share"
    r = run(
        [
            "docker",
            "exec",
            container,
            "ls",
            f"/usr/local/tomcat/webapps/{webapp}/WEB-INF/lib/",
        ]
    )
    if r.returncode == 0:
        jars = sorted(
            [j for j in r.stdout.splitlines() if j.endswith(".jar")]
        )
        return jars
    return []


def api_pending_amps(container):
    if not container:
        return {"error": "container not found"}
    amps_dir = "amps" if "alfresco" in container else "amps_share"
    r = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/{amps_dir}/"])
    if r.returncode == 0:
        amps = sorted(
            [a for a in r.stdout.splitlines() if a.endswith(".amp")]
        )
        return amps
    return []


def container_health(container):
    if not container:
        return "not found"
    if "alfresco" in container:
        r = run(
            [
                "docker",
                "exec",
                container,
                "bash",
                "-c",
                "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/probes/-ready- 2>/dev/null || echo 'unhealthy'",
            ]
        )
    else:
        r = run(
            [
                "docker",
                "exec",
                container,
                "bash",
                "-c",
                "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8080/share 2>/dev/null || echo 'unhealthy'",
            ]
        )
    code = r.stdout.strip()
    return "healthy" if code in ("200", "302") else code


def do_install_amp(container, filename):
    if not container:
        return {"error": "container not found"}
    amps_dir = "amps" if "alfresco" in container else "amps_share"
    webapp = "alfresco" if "alfresco" in container else "share"
    # copy from local installs dir to container amps dir
    local_path = PROJECT_ROOT / "installs" / ("content" if "alfresco" in container else "share") / filename
    if not local_path.exists():
        return {"error": f"file not found: {local_path}"}
    r = run(["docker", "cp", str(local_path), f"{container}:/usr/local/tomcat/{amps_dir}/"])
    if r.returncode != 0:
        return {"error": f"copy failed: {r.stderr}"}
    r = run(
        [
            "docker",
            "exec",
            "--user",
            "root",
            container,
            "java",
            "-jar",
            "/usr/local/tomcat/alfresco-mmt/alfresco-mmt-26.1.0.61.jar",
            "install",
            f"/usr/local/tomcat/{amps_dir}",
            f"/usr/local/tomcat/webapps/{webapp}",
            "-directory",
            "-nobackup",
            "-force",
        ],
        timeout=60,
    )
    if r.returncode == 0:
        return {"success": True, "message": f"{filename} installed"}
    # check if already installed
    if "already installed" in r.stdout.lower() or "io error" in r.stdout.lower():
        return {"success": True, "message": f"{filename} already installed (skipped)"}
    return {"error": f"install failed: {r.stderr or r.stdout}"}


def do_install_jar(container, filename):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if "alfresco" in container else "share"
    local_path = PROJECT_ROOT / "installs" / ("content" if "alfresco" in container else "share") / filename
    if not local_path.exists():
        return {"error": f"file not found: {local_path}"}
    r = run(
        [
            "docker",
            "cp",
            str(local_path),
            f"{container}:/usr/local/tomcat/webapps/{webapp}/WEB-INF/lib/",
        ]
    )
    if r.returncode == 0:
        return {"success": True, "message": f"{filename} copied"}
    return {"error": f"copy failed: {r.stderr}"}


def do_remove_jar(container, filename):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if "alfresco" in container else "share"
    r = run(
        [
            "docker",
            "exec",
            "--user",
            "root",
            container,
            "rm",
            f"/usr/local/tomcat/webapps/{webapp}/WEB-INF/lib/{filename}",
        ]
    )
    if r.returncode == 0:
        return {"success": True, "message": f"{filename} removed"}
    return {"error": f"remove failed: {r.stderr or r.stdout}"}


def do_start(containers):
    results = {}
    cmd = ["docker", "compose", "up", "-d"]
    if containers:
        cmd += containers
    else:
        containers = [s["name"] for s in list_services()]
    r = run(cmd, cwd=str(PROJECT_ROOT), timeout=120)
    status = "started" if r.returncode == 0 else f"failed: {r.stderr}"
    for c in containers:
        results[c] = status
    return results


def do_stop(containers):
    results = {}
    if not containers:
        containers = [s["name"] for s in list_services()]
    cmd = ["docker", "compose", "stop"] + containers
    r = run(cmd, cwd=str(PROJECT_ROOT), timeout=60)
    status = "stopped" if r.returncode == 0 else f"failed: {r.stderr}"
    for c in containers:
        results[c] = status
    return results


def do_restart(containers):
    results = {}
    cmd = ["docker", "compose", "restart"] + containers
    r = run(cmd, cwd=str(PROJECT_ROOT), timeout=60)
    status = "restarted" if r.returncode == 0 else f"failed: {r.stderr}"
    for c in containers:
        results[c] = status
    return results


def send_json(handler, data, status=200):
    body = json.dumps(data, indent=2).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_html(handler, path):
    try:
        content = Path(path).read_bytes()
        ext = Path(path).suffix
        ct = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }.get(ext, "application/octet-stream")
        handler.send_response(200)
        handler.send_header("Content-Type", ct)
        handler.send_header("Content-Length", str(len(content)))
        handler.end_headers()
        handler.wfile.write(content)
    except FileNotFoundError:
        handler.send_response(404)
        handler.end_headers()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/" or path == "/index.html":
            return send_html(self, str(STATIC_DIR / "index.html"))
        if path.startswith("/static/"):
            return send_html(self, str(PROJECT_ROOT / path.lstrip("/")))

        if path == "/api/status":
            detect_containers()
            return send_json(
                self,
                {
                    "alfresco": {
                        "container": ALFRESCO_CONTAINER,
                        "health": container_health(ALFRESCO_CONTAINER),
                    },
                    "share": {
                        "container": SHARE_CONTAINER,
                        "health": container_health(SHARE_CONTAINER),
                    },
                },
            )

        if path == "/api/amps":
            detect_containers()
            return send_json(
                self,
                {
                    "alfresco": {
                        "installed": api_list_amps(ALFRESCO_CONTAINER),
                        "pending": api_pending_amps(ALFRESCO_CONTAINER),
                    },
                    "share": {
                        "installed": api_list_amps(SHARE_CONTAINER),
                        "pending": api_pending_amps(SHARE_CONTAINER),
                    },
                },
            )

        if path == "/api/jars":
            detect_containers()
            return send_json(
                self,
                {
                    "alfresco": api_list_jars(ALFRESCO_CONTAINER),
                    "share": api_list_jars(SHARE_CONTAINER),
                },
            )

        if path == "/api/local-files":
            files = {"content": [], "share": []}
            for f in sorted((PROJECT_ROOT / "installs/content").iterdir()):
                if f.is_file():
                    files["content"].append(f.name)
            for f in sorted((PROJECT_ROOT / "installs/share").iterdir()):
                if f.is_file():
                    files["share"].append(f.name)
            return send_json(self, files)

        if path == "/api/services":
            return send_json(self, list_services())

        if path == "/api/docker-status":
            return send_json(self, {"running": docker_is_running()})

        if path.startswith("/api/logs/"):
            service = path[len("/api/logs/"):]
            cid = get_container_id(service)
            if not cid:
                return send_json(self, {"error": "container not found"}, 404)
            lines = fetch_logs(cid)
            return send_json(self, {"service": service, "logs": lines})

        send_json(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        detect_containers()

        if parsed.path == "/api/upload":
            target = body.get("target")
            filename = body.get("filename")
            data_b64 = body.get("data")
            if not target or not filename or not data_b64:
                return send_json(self, {"error": "target, filename, and data required"}, 400)
            dest_dir = PROJECT_ROOT / "installs" / target
            dest_path = dest_dir / os.path.basename(filename)
            import base64
            try:
                dest_path.write_bytes(base64.b64decode(data_b64))
                return send_json(self, {"success": True, "filename": os.path.basename(filename)})
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if parsed.path == "/api/start":
            targets = body.get("containers", ["alfresco", "share"])
            result = do_start(targets)
            return send_json(self, result)

        if parsed.path == "/api/stop":
            targets = body.get("containers", [])
            result = do_stop(targets)
            return send_json(self, result)

        if parsed.path == "/api/restart":
            targets = body.get("containers", [])
            if not targets:
                return send_json(self, {"error": "containers required"}, 400)
            result = do_restart(targets)
            return send_json(self, result)

        if parsed.path == "/api/launch-docker":
            import shutil
            dockercmd = shutil.which("open") and "open -a Docker" or shutil.which("docker")
            if dockercmd:
                run(shlex.split(dockercmd), timeout=10)
                return send_json(self, {"success": True})
            return send_json(self, {"error": "no way to launch Docker found"}, 400)

        if parsed.path == "/api/delete-file":
            target = body.get("target")
            filename = body.get("filename")
            if not target or not filename:
                return send_json(self, {"error": "target and filename required"}, 400)
            file_path = PROJECT_ROOT / "installs" / target / os.path.basename(filename)
            try:
                file_path.resolve().relative_to((PROJECT_ROOT / "installs").resolve())
            except ValueError:
                return send_json(self, {"error": "invalid path"}, 400)
            if not file_path.exists():
                return send_json(self, {"error": "file not found"}, 404)
            try:
                file_path.unlink()
                return send_json(self, {"success": True, "filename": filename})
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if parsed.path == "/api/install/jar":
            container = body.get("container")
            filename = body.get("filename")
            if not container or not filename:
                return send_json(self, {"error": "container and filename required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_install_jar(cname, filename)
            return send_json(self, result)

        if parsed.path == "/api/install/amp":
            container = body.get("container")
            filename = body.get("filename")
            if not container or not filename:
                return send_json(self, {"error": "container and filename required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_install_amp(cname, filename)
            return send_json(self, result)

        if parsed.path == "/api/remove/jar":
            container = body.get("container")
            filename = body.get("filename")
            if not container or not filename:
                return send_json(self, {"error": "container and filename required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_remove_jar(cname, filename)
            return send_json(self, result)

        send_json(self, {"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass


import signal
import sys

# ... (lines 2-505) ...

def shutdown(signum, frame):
    print("\nShutting down server...")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    detect_containers()
    server = http.server.HTTPServer((HOST, PORT), Handler)
    server.serve_forever()

