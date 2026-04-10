#!/usr/bin/env python3
"""Napoleon dashboard server. One server, multiple projects via route prefix.

Usage:
    python serve.py                          # daemonize and exit
    python serve.py --fg                     # run in foreground
    python serve.py --stop                   # kill running instance
    python serve.py --register /path/to/proj # register a project and print its URL
"""

import hashlib
import json
import os
import signal
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8150
START_TIME = time.time()
PACKAGE_DIR = Path(__file__).parent
DASHBOARD_DIR = PACKAGE_DIR / "dashboard"
XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
NAPOLEON_DIR = XDG_DATA / "napoleon"
PIDFILE = NAPOLEON_DIR / "server.pid"
REGISTRY_FILE = NAPOLEON_DIR / "projects.json"


def project_hash(project_path):
    return hashlib.md5(str(project_path).encode()).hexdigest()[:12]


def data_dir(phash):
    return NAPOLEON_DIR / "projects" / phash / "data"


def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}


def save_registry(reg):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2) + "\n")


TEMPLATE_PROJECT = {
    "id": "getting-started",
    "title": "Getting Started",
    "description": "This is a sample project to show you how Napoleon works. Replace it with your own!",
    "committedTo": "You",
    "deadline": "2099-12-31",
    "minimumDelivery": "Whatever you decide.",
    "priority": 1,
    "status": "planning",
    "constraints": [
        "Example constraint: must use existing API"
    ],
    "unknowns": [
        "Example unknown: how long will the migration take?"
    ],
    "externalDeps": [
        {
            "description": "Example: waiting on API access from vendor",
            "resolved": False,
            "resolvedDate": None
        }
    ],
    "tasks": [
        {
            "id": "explore",
            "title": "Explore your project",
            "description": "Replace this file with a real project. Use this as a reference for the JSON format.",
            "status": "not_started",
            "risk": "low",
            "blockedBy": [],
            "est50": 0.25,
            "est90": 0.5,
            "atomic": True
        },
        {
            "id": "plan",
            "title": "Break down your first milestone",
            "description": "List the tasks needed for your first deliverable. Mark each as atomic once fully decomposed.",
            "status": "not_started",
            "risk": "low",
            "blockedBy": [],
            "est50": None,
            "est90": None,
            "atomic": False
        },
        {
            "id": "estimate",
            "title": "Add 50/90 estimates",
            "description": "est50 = 50% confident you'll finish in this time. est90 = 90% confident. Use the inline editors in the Planning tab.",
            "status": "not_started",
            "risk": "low",
            "blockedBy": [],
            "est50": None,
            "est90": None,
            "atomic": True
        }
    ]
}


def register_project(project_path):
    project_path = Path(project_path).resolve()
    phash = project_hash(project_path)
    ddir = data_dir(phash)
    ddir.mkdir(parents=True, exist_ok=True)

    # Seed with template if empty
    if not any(ddir.glob("*.json")):
        (ddir / "getting-started.json").write_text(
            json.dumps(TEMPLATE_PROJECT, indent=2, ensure_ascii=False) + "\n"
        )

    reg = load_registry()
    reg[phash] = {"path": str(project_path), "name": project_path.name}
    save_registry(reg)

    print(f"http://localhost:{PORT}/#{phash}")


class Handler(BaseHTTPRequestHandler):
    CONTENT_TYPES = {
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
    }

    def do_GET(self):
        path, phash = self._parse_request()

        if path == "/api/projects":
            if not phash:
                self.send_error(400, "Missing ?p=<hash> parameter")
                return
            pdir = data_dir(phash)
            if not pdir.exists():
                self._send_json([])
                return
            projects = [
                json.loads(f.read_text())
                for f in sorted(pdir.glob("*.json"))
            ]
            self._send_json(projects)
        elif path == "/api/hash":
            if not phash:
                self.send_error(400, "Missing ?p=<hash> parameter")
                return
            pdir = data_dir(phash)
            self._send_json({
                "hash": self._dir_hash(pdir),
                "uiHash": self._dir_hash(DASHBOARD_DIR),
                "started": START_TIME,
            })
        elif path == "/api/registry":
            self._send_json(load_registry())
        else:
            # Static dashboard files
            file_path = self.path.lstrip("/") or "index.html"
            full_path = DASHBOARD_DIR / file_path
            if full_path.is_file() and (DASHBOARD_DIR in full_path.resolve().parents or full_path.resolve() == DASHBOARD_DIR):
                ct = self.CONTENT_TYPES.get(full_path.suffix, 'application/octet-stream')
                self._send_file(full_path, ct)
            else:
                self.send_error(404)

    def _parse_request(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        phash = qs.get("p", [None])[0]
        return parsed.path, phash

    def do_POST(self):
        if self.path == "/api/task/update":
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            phash = body.get('phash')
            project_id = body['project']
            task_id = body['task']
            updates = body['updates']

            if not phash:
                self.send_error(400, "Missing phash")
                return

            pdir = data_dir(phash)
            for f in pdir.glob("*.json"):
                fdata = json.loads(f.read_text())
                if fdata['id'] == project_id:
                    for task in fdata['tasks']:
                        if task['id'] == task_id:
                            task.update(updates)
                            f.write_text(json.dumps(fdata, indent=2, ensure_ascii=False) + "\n")
                            self._send_json({"ok": True})
                            return
                    self.send_error(404, "Task not found")
                    return
            self.send_error(404, "Project not found")
        else:
            self.send_error(404)

    @staticmethod
    def _dir_hash(directory):
        entries = []
        if directory.exists():
            for f in sorted(directory.rglob("*")):
                if f.is_file():
                    stat = f.stat()
                    entries.append(f"{f.relative_to(directory)}:{stat.st_size}:{stat.st_mtime_ns}")
        return hashlib.md5("\n".join(entries).encode()).hexdigest()

    def _send_json(self, data):
        self._send_bytes(json.dumps(data).encode(), "application/json")

    def _send_file(self, path, content_type):
        if not path.exists():
            self.send_error(404)
            return
        self._send_bytes(path.read_bytes(), content_type)

    def _send_bytes(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def is_running():
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ProcessLookupError, ValueError):
            PIDFILE.unlink(missing_ok=True)
    return None


def stop():
    if not PIDFILE.exists():
        print("No running dashboard found.")
        return
    pid = int(PIDFILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped dashboard (pid {pid}).")
    except ProcessLookupError:
        print(f"Stale pidfile (pid {pid} not running). Cleaning up.")
    PIDFILE.unlink(missing_ok=True)


def run(foreground=False):
    pid = is_running()
    if pid:
        print(f"Dashboard already running: http://localhost:{PORT}  (pid {pid})")
        return

    NAPOLEON_DIR.mkdir(parents=True, exist_ok=True)

    if not foreground:
        pid = os.fork()
        if pid > 0:
            PIDFILE.write_text(str(pid))
            print(f"Dashboard: http://localhost:{PORT}  (pid {pid})")
            return
        os.setsid()
        sys.stdin.close()
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        sys.stderr = devnull
    else:
        PIDFILE.write_text(str(os.getpid()))
        print(f"Dashboard: http://localhost:{PORT}")

    server = HTTPServer(("localhost", PORT), Handler)
    try:
        server.serve_forever()
    finally:
        PIDFILE.unlink(missing_ok=True)


def list_projects():
    reg = load_registry()
    if not reg:
        print("No projects registered.")
        return
    for phash, info in reg.items():
        print(f"{phash}  {info['name']}  ({info['path']})")


if __name__ == "__main__":
    if "--stop" in sys.argv:
        stop()
    elif "--list" in sys.argv:
        list_projects()
    elif "--register" in sys.argv:
        idx = sys.argv.index("--register")
        if idx + 1 < len(sys.argv):
            register_project(sys.argv[idx + 1])
        else:
            print("Usage: serve.py --register /path/to/project", file=sys.stderr)
            sys.exit(1)
    elif "--fg" in sys.argv:
        run(foreground=True)
    else:
        run()
