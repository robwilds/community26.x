#!/usr/bin/env python3
import http.server
import json
import os
import shlex
import subprocess
import tempfile
import threading
import urllib.parse
import zipfile
from pathlib import Path

HOST = "0.0.0.0"
PORT = 9700
STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).parent.parent
COMPOSE_DIR = PROJECT_ROOT
TRACKED_JARS_FILE = Path(__file__).parent / "data" / "installed_jars.json"
ALFRESCO_GLOBAL_PROPERTIES = PROJECT_ROOT / "data" / "services" / "content" / "alfresco-global.properties"
DEFAULT_MMT_JAR = "/usr/local/tomcat/alfresco-mmt/alfresco-mmt-26.2.0.96.jar"

ALFRESCO_CONTAINER = None
SHARE_CONTAINER = None


def check_docker_status():
    r = run(["docker", "info"], timeout=5)
    if r.returncode == 0:
        return {"running": True, "installed": True}
    # Check if docker binary exists (command not found)
    which = run(["sh", "-c", "command -v docker"], timeout=5)
    installed = which.returncode == 0
    return {"running": False, "installed": installed}


def _parse_quay_images():
    """Extract all quay.io image references from the resolved compose config.

    Uses `docker compose config --images` which automatically excludes
    services gated behind profiles (donotstart, disabled, etc.) and
    commented-out image references.
    """
    r = run(["docker", "compose", "config", "--images"], cwd=str(COMPOSE_DIR), timeout=30)
    if r.returncode != 0:
        return []
    images = [line.strip() for line in r.stdout.strip().splitlines() if line.strip().startswith("quay.io/")]
    return sorted(set(images))


def check_quay_images():
    """Check which quay.io images are cached locally."""
    images = _parse_quay_images()
    missing = []
    for img in images:
        r = run(["docker", "image", "inspect", img])
        if r.returncode != 0:
            missing.append(img)
    return {"images": images, "missing": missing, "needs_login": len(missing) > 0}


def docker_login_quay(username, password):
    """Run docker login quay.io with the given credentials."""
    r = run(
        ["docker", "login", "quay.io", "--username", username, "--password-stdin"],
        input=password,
        timeout=30,
    )
    if r.returncode == 0:
        return {"success": True}
    error = (r.stderr.strip() or r.stdout.strip() or "login failed")
    return {"success": False, "error": error}


def run(cmd, **kwargs):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=kwargs.pop("timeout", 30), **kwargs
    )


# Pull progress tracking
_pull_state = {
    "running": False,
    "output": [],
    "complete": False,
    "error": None,
}
_pull_lock = threading.Lock()


def _pull_images(services):
    """Run docker compose pull in a background thread, populating _pull_state."""
    global _pull_state
    with _pull_lock:
        _pull_state["running"] = True
        _pull_state["output"] = []
        _pull_state["complete"] = False
        _pull_state["error"] = None
    try:
        cmd = ["docker", "compose", "pull", "--policy", "missing"] + services
        proc = subprocess.Popen(
            cmd,
            cwd=str(COMPOSE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in iter(proc.stdout.readline, ""):
            with _pull_lock:
                _pull_state["output"].append(line)
        proc.wait()
        with _pull_lock:
            _pull_state["complete"] = True
            _pull_state["running"] = False
            if proc.returncode != 0:
                _pull_state["error"] = f"pull failed with code {proc.returncode}"
    except Exception as e:
        with _pull_lock:
            _pull_state["complete"] = True
            _pull_state["running"] = False
            _pull_state["error"] = str(e)


def _get_amp_module_id(local_path):
    """Extract module.id from an AMP (ZIP) file."""
    try:
        with zipfile.ZipFile(str(local_path)) as zf:
            with zf.open("module.properties") as f:
                for line in f.read().decode().splitlines():
                    if line.startswith("module.id="):
                        return line.split("=", 1)[1].strip()
    except Exception:
        return None
    return None


def _resolve_mmt_jar(container):
    """Locate the MMT jar in a running container (dynamic version detection).

    Probes /usr/local/tomcat/alfresco-mmt/*.jar so the version tracks whatever
    image is actually running; falls back to DEFAULT_MMT_JAR when unavailable.
    """
    if not container:
        return DEFAULT_MMT_JAR
    r = run(
        [
            "docker", "exec", "--user", "root", container,
            "sh", "-c", "ls /usr/local/tomcat/alfresco-mmt/*.jar 2>/dev/null",
        ],
        timeout=10,
    )
    matches = [line.strip() for line in r.stdout.splitlines() if line.strip().endswith(".jar")]
    return matches[0] if matches else DEFAULT_MMT_JAR


def _get_installed_amp_ids(container, svc):
    """Return set of installed AMP module IDs via MMT list."""
    if not container:
        return None
    webapp = "/usr/local/tomcat/webapps/alfresco" if svc == "alfresco" else "/usr/local/tomcat/webapps/share"
    r = run([
        "docker", "exec", container,
        "java", "-jar",
        _resolve_mmt_jar(container),
        "list", webapp,
    ], timeout=30)
    if r.returncode != 0:
        return set()
    ids = set()
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("Module"):
            try:
                ids.add(line.split("'")[1])
            except IndexError:
                pass
    return ids


def detect_containers():
    global ALFRESCO_CONTAINER, SHARE_CONTAINER
    r = run(
        ["docker", "compose", "ps", "-q", "alfresco"],
        cwd=str(COMPOSE_DIR),
    )
    if r.returncode == 0 and r.stdout.strip():
        cid = r.stdout.strip().splitlines()[0]
        r2 = run(["docker", "inspect", "--format", "{{.Name}}", cid])
        if r2.returncode == 0:
            ALFRESCO_CONTAINER = r2.stdout.strip().lstrip("/")
    r = run(
        ["docker", "compose", "ps", "-q", "share"],
        cwd=str(COMPOSE_DIR),
    )
    if r.returncode == 0 and r.stdout.strip():
        cid = r.stdout.strip().splitlines()[0]
        r2 = run(["docker", "inspect", "--format", "{{.Name}}", cid])
        if r2.returncode == 0:
            SHARE_CONTAINER = r2.stdout.strip().lstrip("/")
    backfill_tracked_jars()


def _ensure_tracked_jars_dir():
    TRACKED_JARS_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_tracked_jars():
    _ensure_tracked_jars_dir()
    if TRACKED_JARS_FILE.exists():
        try:
            return json.loads(TRACKED_JARS_FILE.read_text())
        except Exception:
            pass
    return {"alfresco": [], "share": []}

def save_tracked_jars(data):
    _ensure_tracked_jars_dir()
    TRACKED_JARS_FILE.write_text(json.dumps(data, indent=2))

def track_jar_install(svc, filename):
    data = load_tracked_jars()
    if filename not in data.setdefault(svc, []):
        data[svc].append(filename)
        save_tracked_jars(data)

def untrack_jar_remove(svc, filename):
    data = load_tracked_jars()
    if filename in data.get(svc, []):
        data[svc].remove(filename)
        save_tracked_jars(data)

def backfill_tracked_jars():
    """Check installs/ dir for JARs already present in containers and add to tracking."""
    data = load_tracked_jars()
    changed = False
    for svc, container, installs_key in [
        ("alfresco", ALFRESCO_CONTAINER, "content"),
        ("share", SHARE_CONTAINER, "share"),
    ]:
        if not container:
            continue
        installs_dir = PROJECT_ROOT / "installs" / installs_key
        if not installs_dir.exists():
            continue
        webapp = "alfresco" if svc == "alfresco" else "share"
        for f in sorted(installs_dir.iterdir()):
            if f.suffix != ".jar":
                continue
            if f.name in data.get(svc, []):
                continue
            r = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/webapps/{webapp}/WEB-INF/lib/{f.name}"])
            if r.returncode == 0:
                data.setdefault(svc, []).append(f.name)
                changed = True
    if changed:
        save_tracked_jars(data)

def get_container_id(service):
    r = run(["docker", "compose", "ps", "-q", service], cwd=str(COMPOSE_DIR))
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
    # Get all service names from the compose YAML (includes profile-gated services)
    all_services = _parse_all_service_names()
    # Also get services visible to docker compose with current profiles
    r = run(
        ["docker", "compose", "config", "--services"],
        cwd=str(COMPOSE_DIR),
    )
    if r.returncode == 0 and r.stdout.strip():
        config_services = r.stdout.strip().splitlines()
        # Merge: prefer all_services from YAML, but add any extras from config
        all_services = list(dict.fromkeys(all_services + config_services))

    # Get running status and container IDs from docker compose ps
    r2 = run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=str(COMPOSE_DIR),
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
    # Build a lookup: service -> profile name
    svc_profile = {}
    for pname, svcs in profiles.items():
        for s in svcs:
            svc_profile[s] = pname
    result = [
        {
            "name": s,
            "running": s in running,
            "profile_name": svc_profile.get(s),
            "container_id": cids.get(s, ""),
        }
        for s in all_services
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
        text = Path(COMPOSE_DIR / "docker-compose.yaml").read_text()
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


def _parse_all_service_names():
    """Parse docker-compose.yaml to extract ALL service names, including those in profiles."""
    names = []
    try:
        text = Path(COMPOSE_DIR / "docker-compose.yaml").read_text()
        import re
        in_services = False
        for line in text.splitlines():
            # Track top-level sections (no leading indent)
            top = re.match(r"^(\S+):", line)
            if top:
                in_services = top.group(1) == "services"
                continue
            # Inside services section, collect names with 2-space indent
            if in_services:
                m = re.match(r"^  (\S+):", line)
                if m and not line.startswith("   "):
                    names.append(m.group(1))
    except Exception:
        pass
    return names


def read_file(path):
    try:
        return Path(path).read_text()
    except Exception:
        return None


def _get_applied_amp_ids(container, svc):
    """Scan container's amps dir for .applied files and return their module IDs."""
    if not container:
        return set()
    amps_dir = "amps" if svc == "alfresco" else "amps_share"
    ls = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/{amps_dir}/"], timeout=10)
    if ls.returncode != 0:
        return set()
    ids = set()
    with tempfile.TemporaryDirectory() as tmp:
        for fname in ls.stdout.splitlines():
            if not fname.endswith(".applied"):
                continue
            local = Path(tmp) / fname
            cp = run(["docker", "cp", f"{container}:/usr/local/tomcat/{amps_dir}/{fname}", str(local)], timeout=10)
            if cp.returncode != 0 or not local.exists():
                continue
            try:
                with zipfile.ZipFile(str(local)) as zf:
                    with zf.open("module.properties") as f:
                        for line in f.read().decode().splitlines():
                            if line.startswith("module.id="):
                                ids.add(line.split("=", 1)[1].strip())
                                break
            except Exception:
                pass
    return ids


def api_list_amps(container, svc):
    if not container:
        return []
    r = run(
        [
            "docker",
            "exec",
            container,
            "java",
            "-jar",
            _resolve_mmt_jar(container),
            "list",
            "/usr/local/tomcat/webapps/alfresco"
            if svc == "alfresco"
            else "/usr/local/tomcat/webapps/share",
        ]
    )
    amps = []
    if r.returncode == 0:
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("Module"):
                mod_id = line.split("'")[1]
                amps.append({"id": mod_id, "status": "installed", "removable": True})
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


def api_list_jars(container, svc):
    if not container:
        return []
    webapp = "alfresco" if svc == "alfresco" else "share"
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
        tracked = load_tracked_jars().get(svc, [])
        return [{"name": j, "removable": j in tracked} for j in jars]
    return []


def api_pending_amps(container, svc):
    if not container:
        return []
    amps_dir = "amps" if svc == "alfresco" else "amps_share"
    r = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/{amps_dir}/"])
    if r.returncode == 0:
        amps = sorted(
            [a for a in r.stdout.splitlines() if a.endswith(".amp")]
        )
        return amps
    return []


def _filter_pending_not_installed(container, svc, pending):
    """Filter pending AMP list to exclude AMPs already installed via MMT."""
    if not container or not pending:
        return pending or []
    installed_ids = _get_installed_amp_ids(container, svc)
    if not installed_ids:
        return pending
    amps_dir = "amps" if svc == "alfresco" else "amps_share"
    filtered = []
    with tempfile.TemporaryDirectory() as tmp:
        for fname in pending:
            local = Path(tmp) / fname
            r = run(["docker", "cp", f"{container}:/usr/local/tomcat/{amps_dir}/{fname}", str(local)], timeout=10)
            if r.returncode != 0 or not local.exists():
                filtered.append(fname)
                continue
            mod_id = _get_amp_module_id(local)
            if mod_id and mod_id in installed_ids:
                continue
            filtered.append(fname)
    return filtered


def api_available_amps(container, svc):
    """Return AMP files from installs/ that are not yet installed or pending."""
    installs_dir = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share")
    if not installs_dir.exists():
        return []
    installed_ids = _get_installed_amp_ids(container, svc) if container else set()
    pending = api_pending_amps(container, svc) or []
    available = []
    for f in sorted(installs_dir.iterdir()):
        if f.suffix != ".amp":
            continue
        if f.name in pending:
            continue
        if installed_ids:
            mod_id = _get_amp_module_id(f)
            if mod_id and mod_id in installed_ids:
                continue
        available.append(f.name)
    return available


def api_available_jars(container, svc):
    """Return JAR files from installs/ that are not in WEB-INF/lib."""
    installs_dir = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share")
    if not installs_dir.exists():
        return []
    installed_jars = api_list_jars(container, svc) or []
    installed_names = {j["name"] for j in installed_jars if isinstance(j, dict)}
    available = []
    for f in sorted(installs_dir.iterdir()):
        if f.suffix == ".jar" and f.name not in installed_names:
            available.append(f.name)
    return available


def is_file_installed(container, filename, svc, installed_amp_ids=None):
    if not container:
        return False
    if filename.endswith(".amp"):
        # Prefer MMT-based check: extract module.id and compare against MMT list
        if installed_amp_ids is not None:
            local_path = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share") / filename
            if local_path.exists():
                mod_id = _get_amp_module_id(local_path)
                if mod_id:
                    return mod_id in installed_amp_ids
        # Fallback: check .applied file in the container's amps directory
        amps_dir = "amps" if svc == "alfresco" else "amps_share"
        base = filename.rsplit(".", 1)[0]
        r = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/{amps_dir}/"])
        if r.returncode == 0:
            return f"{base}.applied" in r.stdout.splitlines()
    elif filename.endswith(".jar"):
        webapp = "alfresco" if svc == "alfresco" else "share"
        r = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/webapps/{webapp}/WEB-INF/lib/"])
        if r.returncode == 0:
            return filename in r.stdout.splitlines()
    return False


def container_health(container, svc):
    if not container:
        return "not found"
    if svc == "alfresco":
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


def do_install_amp(container, filename, svc):
    if not container:
        return {"error": "container not found"}
    amps_dir = "amps" if svc == "alfresco" else "amps_share"
    webapp = "alfresco" if svc == "alfresco" else "share"
    # copy from local installs dir to container amps dir
    local_path = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share") / filename
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
            _resolve_mmt_jar(container),
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
        base = filename.rsplit(".", 1)[0]
        run(["docker", "exec", "--user", "root", container, "mv", f"/usr/local/tomcat/{amps_dir}/{filename}", f"/usr/local/tomcat/{amps_dir}/{base}.applied"])
        return {"success": True, "message": f"{filename} installed"}
    # check if already installed
    if "already installed" in r.stdout.lower() or "io error" in r.stdout.lower():
        base = filename.rsplit(".", 1)[0]
        run(["docker", "exec", "--user", "root", container, "mv", f"/usr/local/tomcat/{amps_dir}/{filename}", f"/usr/local/tomcat/{amps_dir}/{base}.applied"])
        return {"success": True, "message": f"{filename} already installed (applied)"}
    return {"error": f"install failed: {r.stderr or r.stdout}"}


def do_uninstall_amp(container, module_id, svc):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if svc == "alfresco" else "share"
    amps_dir = "amps" if svc == "alfresco" else "amps_share"
    # Uninstall the module from the WAR via MMT
    r = run([
        "docker", "exec", "--user", "root", container,
        "java", "-jar",
        _resolve_mmt_jar(container),
        "uninstall", module_id,
        f"/usr/local/tomcat/webapps/{webapp}",
    ], timeout=30)
    if r.returncode != 0:
        return {"error": f"uninstall failed: {r.stderr or r.stdout}"}
    # Remove the matching .applied marker from the container's amps dir so the
    # source AMP in installs/ shows up as available to install again. If no local
    # source exists, keep the file by reverting it to .amp (pending) to avoid
    # losing it.
    ls = run(["docker", "exec", container, "ls", f"/usr/local/tomcat/{amps_dir}/"], timeout=10)
    installs_dir = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share")
    action = ""
    if ls.returncode == 0:
        with tempfile.TemporaryDirectory() as tmp:
            for fname in ls.stdout.splitlines():
                if not fname.endswith(".applied"):
                    continue
                base = fname.rsplit(".", 1)[0]
                local = Path(tmp) / fname
                cp = run(["docker", "cp", f"{container}:/usr/local/tomcat/{amps_dir}/{fname}", str(local)], timeout=10)
                if cp.returncode != 0 or not local.exists():
                    continue
                try:
                    with zipfile.ZipFile(str(local)) as zf:
                        with zf.open("module.properties") as f:
                            for line in f.read().decode().splitlines():
                                if line.strip() == f"module.id={module_id}":
                                    if (installs_dir / f"{base}.amp").exists():
                                        run(["docker", "exec", "--user", "root", container,
                                             "rm", f"/usr/local/tomcat/{amps_dir}/{fname}"])
                                        action = " and available for reinstall"
                                    else:
                                        run(["docker", "exec", "--user", "root", container,
                                             "mv", f"/usr/local/tomcat/{amps_dir}/{fname}",
                                             f"/usr/local/tomcat/{amps_dir}/{base}.amp"])
                                        action = " (kept as pending .amp)"
                                    break
                except Exception:
                    pass
                if action:
                    break
    return {"success": True, "message": f"{module_id} removed{action}"}


def do_install_jar(container, filename, svc):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if svc == "alfresco" else "share"
    local_path = PROJECT_ROOT / "installs" / ("content" if svc == "alfresco" else "share") / filename
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
        track_jar_install(svc, filename)
        return {"success": True, "message": f"{filename} copied"}
    return {"error": f"copy failed: {r.stderr}"}


def do_remove_jar(container, filename, svc):
    if not container:
        return {"error": "container not found"}
    webapp = "alfresco" if svc == "alfresco" else "share"
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
        untrack_jar_remove(svc, filename)
        return {"success": True, "message": f"{filename} removed"}
    return {"error": f"remove failed: {r.stderr or r.stdout}"}


def do_start(containers):
    results = {}
    if containers:
        services = containers
        r = run(["docker", "compose", "up", "-d", "--pull", "missing"] + services, cwd=str(COMPOSE_DIR), timeout=360)
    else:
        # Start All: only non-profile-gated services
        services = [s["name"] for s in list_services() if not s.get("profile_name")]
        r = run(["docker", "compose", "up", "-d", "--pull", "missing"], cwd=str(COMPOSE_DIR), timeout=360)
    if r.returncode == 0:
        for c in services:
            results[c] = "started"
    else:
        error_msg = r.stderr.strip() or r.stdout.strip() or "unknown error"
        # Inspect post-start state to determine which services actually started
        ps_r = run(["docker", "compose", "ps", "--format", "json"], cwd=str(COMPOSE_DIR))
        running = set()
        if ps_r.returncode == 0 and ps_r.stdout.strip():
            import json as _json
            for line in ps_r.stdout.strip().splitlines():
                try:
                    info = _json.loads(line)
                    if info.get("State") == "running":
                        running.add(info.get("Service"))
                except Exception:
                    pass
        for c in services:
            if c in running:
                results[c] = "started"
            else:
                results[c] = f"failed: {error_msg}"
    return results


def do_stop(containers):
    results = {}
    if not containers:
        containers = [s["name"] for s in list_services()]
    cmd = ["docker", "compose", "stop"] + containers
    r = run(cmd, cwd=str(COMPOSE_DIR), timeout=60)
    status = "stopped" if r.returncode == 0 else f"failed: {r.stderr}"
    for c in containers:
        results[c] = status
    return results


def do_restart(containers):
    results = {}
    if not containers:
        containers = [s["name"] for s in list_services()]
    cmd = ["docker", "compose", "restart"] + containers
    r = run(cmd, cwd=str(COMPOSE_DIR), timeout=60)
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
            return send_html(self, str(STATIC_DIR / path.split("/", 2)[-1]))

        if path == "/api/properties":
            content = read_file(ALFRESCO_GLOBAL_PROPERTIES)
            if content is None:
                return send_json(self, {"error": "file not found"}, 404)
            return send_json(self, {"content": content})

        if path == "/api/status":
            detect_containers()
            return send_json(
                self,
                {
                    "alfresco": {
                        "container": ALFRESCO_CONTAINER,
                        "health": container_health(ALFRESCO_CONTAINER, "alfresco"),
                    },
                    "share": {
                        "container": SHARE_CONTAINER,
                        "health": container_health(SHARE_CONTAINER, "share"),
                    },
                },
            )

        if path == "/api/amps":
            detect_containers()
            alf_pending = _filter_pending_not_installed(
                ALFRESCO_CONTAINER, "alfresco",
                api_pending_amps(ALFRESCO_CONTAINER, "alfresco"),
            )
            shr_pending = _filter_pending_not_installed(
                SHARE_CONTAINER, "share",
                api_pending_amps(SHARE_CONTAINER, "share"),
            )
            return send_json(
                self,
                {
                    "alfresco": {
                        "installed": api_list_amps(ALFRESCO_CONTAINER, "alfresco"),
                        "pending": alf_pending,
                        "available": api_available_amps(ALFRESCO_CONTAINER, "alfresco"),
                    },
                    "share": {
                        "installed": api_list_amps(SHARE_CONTAINER, "share"),
                        "pending": shr_pending,
                        "available": api_available_amps(SHARE_CONTAINER, "share"),
                    },
                },
            )

        if path == "/api/jars":
            detect_containers()
            return send_json(
                self,
                {
                    "alfresco": {
                        "installed": api_list_jars(ALFRESCO_CONTAINER, "alfresco"),
                        "available": api_available_jars(ALFRESCO_CONTAINER, "alfresco"),
                    },
                    "share": {
                        "installed": api_list_jars(SHARE_CONTAINER, "share"),
                        "available": api_available_jars(SHARE_CONTAINER, "share"),
                    },
                },
            )

        if path == "/api/local-files":
            detect_containers()
            alfresco_amp_ids = _get_installed_amp_ids(ALFRESCO_CONTAINER, "alfresco")
            share_amp_ids = _get_installed_amp_ids(SHARE_CONTAINER, "share")
            files = {"content": [], "share": []}
            for f in sorted((PROJECT_ROOT / "installs/content").iterdir()):
                if f.is_file():
                    installed = is_file_installed(
                        ALFRESCO_CONTAINER, f.name, "alfresco", alfresco_amp_ids
                    )
                    files["content"].append(
                        {"name": f.name, "installed": installed}
                    )
            for f in sorted((PROJECT_ROOT / "installs/share").iterdir()):
                if f.is_file():
                    installed = is_file_installed(
                        SHARE_CONTAINER, f.name, "share", share_amp_ids
                    )
                    files["share"].append(
                        {"name": f.name, "installed": installed}
                    )
            return send_json(self, files)

        if path == "/api/services":
            try:
                return send_json(self, list_services())
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if path == "/api/docker-status":
            return send_json(self, check_docker_status())

        if path == "/api/docker/quay-status":
            try:
                return send_json(self, check_quay_images())
            except Exception as e:
                return send_json(self, {"error": str(e), "needs_login": False}, 500)

        if path == "/api/pull-status":
            with _pull_lock:
                return send_json(
                    self,
                    {
                        "running": _pull_state["running"],
                        "complete": _pull_state["complete"],
                        "output": "".join(_pull_state["output"]),
                        "error": _pull_state["error"],
                    },
                )

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

        if parsed.path == "/api/properties":
            new_content = body.get("content")
            if new_content is None:
                return send_json(self, {"error": "content required"}, 400)
            try:
                ALFRESCO_GLOBAL_PROPERTIES.write_text(new_content)
                return send_json(self, {"success": True})
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

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

        if parsed.path == "/api/pull":
            targets = body.get("containers", [])
            if not targets:
                targets = [s["name"] for s in list_services() if not s.get("profile_name")]
            thread = threading.Thread(target=_pull_images, args=(targets,), daemon=True)
            thread.start()
            return send_json(self, {"started": True})

        if parsed.path == "/api/start":
            targets = body.get("containers", [])
            try:
                result = do_start(targets)
                return send_json(self, result)
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if parsed.path == "/api/stop":
            targets = body.get("containers", [])
            try:
                result = do_stop(targets)
                return send_json(self, result)
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if parsed.path == "/api/restart":
            targets = body.get("containers", [])
            try:
                result = do_restart(targets)
                return send_json(self, result)
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

        if parsed.path == "/api/docker/login":
            username = body.get("username", "")
            password = body.get("password", "")
            if not username or not password:
                return send_json(self, {"error": "username and password required"}, 400)
            try:
                result = docker_login_quay(username, password)
                return send_json(self, result)
            except Exception as e:
                return send_json(self, {"error": str(e)}, 500)

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
            result = do_install_jar(cname, filename, container)
            return send_json(self, result)

        if parsed.path == "/api/install/amp":
            container = body.get("container")
            filename = body.get("filename")
            if not container or not filename:
                return send_json(self, {"error": "container and filename required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_install_amp(cname, filename, container)
            return send_json(self, result)

        if parsed.path == "/api/remove/jar":
            container = body.get("container")
            filename = body.get("filename")
            if not container or not filename:
                return send_json(self, {"error": "container and filename required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_remove_jar(cname, filename, container)
            return send_json(self, result)

        if parsed.path == "/api/uninstall/amp":
            container = body.get("container")
            module_id = body.get("module_id")
            if not container or not module_id:
                return send_json(self, {"error": "container and module_id required"}, 400)
            cname = ALFRESCO_CONTAINER if container == "alfresco" else SHARE_CONTAINER
            result = do_uninstall_amp(cname, module_id, container)
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

