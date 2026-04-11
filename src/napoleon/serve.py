#!/usr/bin/env python3
"""Napoleon dashboard server.

Single aiohttp server on port 8150 handling HTTP API and WebSocket.
WebSocket clients at /api/ws get pushed {"type": "data-changed", "hash": "<phash>"}
when project data files change on disk.
"""

import asyncio
import collections
import hashlib
import json
import os
import signal
import sys
import time
import traceback
from pathlib import Path

from aiohttp import web

PORT = 8150
START_TIME = time.time()
PACKAGE_DIR = Path(__file__).parent
DASHBOARD_DIR = PACKAGE_DIR / "dashboard"
XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
NAPOLEON_DIR = XDG_DATA / "napoleon"
PIDFILE = NAPOLEON_DIR / "server.pid"

CONTENT_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
}

_errors: collections.deque = collections.deque(maxlen=5)
ws_clients: set[web.WebSocketResponse] = set()


def _capture_error():
    _errors.append({
        "time": time.strftime("%H:%M:%S"),
        "error": traceback.format_exc(),
    })


def data_dir(phash):
    return NAPOLEON_DIR / "projects" / phash / "data"


def dir_hash(directory):
    entries = []
    if directory.exists():
        for f in sorted(directory.rglob("*")):
            if f.is_file():
                stat = f.stat()
                entries.append(f"{f.relative_to(directory)}:{stat.st_size}:{stat.st_mtime_ns}")
    return hashlib.md5("\n".join(entries).encode()).hexdigest()


# ── HTTP routes ──

async def handle_repos(request):
    repos = []
    projects_root = NAPOLEON_DIR / "projects"
    if projects_root.exists():
        for d in sorted(projects_root.iterdir()):
            if not d.is_dir():
                continue
            meta_file = d / "meta.json"
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                except Exception:
                    pass
            label = meta.get("name", d.name)
            repos.append({"hash": d.name, "name": label, "url": meta.get("url", "")})
    return web.json_response(repos)


async def handle_projects(request):
    phash = request.query.get("p")
    if not phash:
        return web.json_response({"error": "Missing ?p=<hash>"}, status=400)
    pdir = data_dir(phash)
    if not pdir.exists():
        return web.json_response([])
    projects = [json.loads(f.read_text()) for f in sorted(pdir.glob("*.json"))]
    return web.json_response(projects)


async def handle_hash(request):
    phash = request.query.get("p")
    if not phash:
        return web.json_response({"error": "Missing ?p=<hash>"}, status=400)
    pdir = data_dir(phash)
    return web.json_response({
        "hash": dir_hash(pdir),
        "uiHash": dir_hash(DASHBOARD_DIR),
        "started": START_TIME,
    })


async def handle_task_update(request):
    body = await request.json()
    phash = body.get("phash")
    project_id = body["project"]
    task_id = body["task"]
    updates = body["updates"]

    if not phash:
        return web.json_response({"error": "Missing phash"}, status=400)

    pdir = data_dir(phash)
    for f in pdir.glob("*.json"):
        fdata = json.loads(f.read_text())
        if fdata["id"] == project_id:
            for task in fdata["tasks"]:
                if task["id"] == task_id:
                    task.update(updates)
                    f.write_text(json.dumps(fdata, indent=2, ensure_ascii=False) + "\n")
                    return web.json_response({"ok": True})
            return web.json_response({"error": "Task not found"}, status=404)
    return web.json_response({"error": "Project not found"}, status=404)


async def handle_errors(request):
    return web.json_response(list(_errors))


# ── WebSocket ──

async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    try:
        async for _ in ws:
            pass  # We don't expect messages from clients
    finally:
        ws_clients.discard(ws)
    return ws


async def data_watcher(app):
    """Poll data dirs and push changes to WebSocket clients."""
    known_hashes: dict[str, str] = {}
    while True:
        await asyncio.sleep(2)
        projects_root = NAPOLEON_DIR / "projects"
        if not projects_root.exists():
            continue
        try:
            for d in projects_root.iterdir():
                if not d.is_dir():
                    continue
                pdir = d / "data"
                if not pdir.exists():
                    continue
                phash = d.name
                h = dir_hash(pdir)
                if phash not in known_hashes:
                    known_hashes[phash] = h
                elif h != known_hashes[phash]:
                    known_hashes[phash] = h
                    msg = json.dumps({"type": "data-changed", "hash": phash})
                    dead = set()
                    for client in ws_clients:
                        try:
                            await client.send_str(msg)
                        except Exception:
                            dead.add(client)
                    for d in dead:
                        ws_clients.discard(d)
        except Exception:
            _capture_error()


async def start_watcher(app):
    app["watcher"] = asyncio.create_task(data_watcher(app))


async def stop_watcher(app):
    app["watcher"].cancel()
    try:
        await app["watcher"]
    except asyncio.CancelledError:
        pass


# ── Static files (fallback) ──

async def handle_static(request):
    file_path = request.path.lstrip("/") or "index.html"
    full_path = DASHBOARD_DIR / file_path
    if full_path.is_file() and (DASHBOARD_DIR in full_path.resolve().parents or full_path.resolve() == DASHBOARD_DIR):
        ct = CONTENT_TYPES.get(full_path.suffix, "application/octet-stream")
        return web.Response(body=full_path.read_bytes(), content_type=ct)
    raise web.HTTPNotFound()


# ── App factory ──

def create_app():
    app = web.Application()
    app.router.add_get("/api/repos", handle_repos)
    app.router.add_get("/api/projects", handle_projects)
    app.router.add_get("/api/hash", handle_hash)
    app.router.add_post("/api/task/update", handle_task_update)
    app.router.add_get("/api/errors", handle_errors)
    app.router.add_get("/api/ws", handle_ws)
    # Static fallback (must be last)
    app.router.add_get("/{path:.*}", handle_static)
    app.on_startup.append(start_watcher)
    app.on_cleanup.append(stop_watcher)
    return app


# ── Server lifecycle ──

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

    app = create_app()
    web.run_app(app, host="localhost", port=PORT, print=None)
    PIDFILE.unlink(missing_ok=True)


if __name__ == "__main__":
    if "--stop" in sys.argv:
        stop()
    elif "--fg" in sys.argv:
        run(foreground=True)
    else:
        run()
