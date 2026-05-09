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
    local_path = Path("installs") / ("content" if "alfresco" in container else "share") / filename
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
    local_path = Path("installs") / ("content" if "alfresco" in container else "share") / filename
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


def do_restart(containers):
    results = {}
    for c in containers:
        if c in ("alfresco", "share"):
            cname = ALFRESCO_CONTAINER if c == "alfresco" else SHARE_CONTAINER
            if not cname:
                results[c] = "not found"
                continue
            r = run(["docker", "restart", cname], timeout=60)
            results[c] = "restarted" if r.returncode == 0 else f"failed: {r.stderr}"
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
                if f.suffix in (".jar", ".amp"):
                    files["content"].append(f.name)
            for f in sorted((PROJECT_ROOT / "installs/share").iterdir()):
                if f.suffix in (".jar", ".amp"):
                    files["share"].append(f.name)
            return send_json(self, files)

        send_json(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        detect_containers()

        if parsed.path == "/api/restart":
            targets = body.get("containers", ["alfresco", "share"])
            result = do_restart(targets)
            return send_json(self, result)

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


if __name__ == "__main__":
    detect_containers()
    server = http.server.HTTPServer((HOST, PORT), Handler)
    print(f"Alfresco Manager UI: http://localhost:{PORT}")
    print(f"  Alfresco: {ALFRESCO_CONTAINER}")
    print(f"  Share:    {SHARE_CONTAINER}")
    server.serve_forever()
