"""Napoleon — personal project intelligence. Strategy, not status.

A dashboard and CLI for managing complex projects with AI.
Break down work, estimate with confidence, track what matters.

Getting started:
    cd my-project                   Navigate to any git repo
    napoleon open                   Open the dashboard in your browser
    napoleon new my-project "My Project"  Create your first project
    napoleon add my-project "First task"  Add a task to it

Napoleon auto-detects which project you're in from the git remote URL.
Each repo gets its own isolated data store. Just cd into a repo and go.

Server:
    napoleon serve                  Start the dashboard (daemonizes)
    napoleon serve --stop           Stop the dashboard
    napoleon serve --fg             Run in foreground (debugging)
    napoleon open                   Start server and open dashboard in browser

Projects:
    napoleon projects               List projects in current repo
    napoleon new <id> <title>       Create a new project
        [--deadline YYYY-MM-DD] [--priority N] [--committed-to WHO]
        [--description TEXT]

Tasks:
    napoleon tasks <project>        List tasks for a project
    napoleon add <project> <title>  Add a task
        [--id ID] [--description TEXT] [--risk low|medium|high]
        [--est50 N] [--est90 N] [--atomic] [--at INDEX]
    napoleon done <project> <task>  Mark a task complete
    napoleon update <project> <task>  Update task fields
        [--est50 N] [--est90 N] [--risk LEVEL] [--description TEXT]
        [--status STATUS] [--atomic true|false]
    napoleon rm <project> <task>    Remove a task

Metadata:
    napoleon unknowns <project> list|add|remove [text|index]
    napoleon constraints <project> list|add|remove [text|index]

Options:
    napoleon help                   Show this help
    napoleon --version              Show version
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
NAPOLEON_DIR = XDG_DATA / "napoleon"


def get_phash():
    """Compute project hash from git remote URL."""
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return hashlib.md5(url.encode()).hexdigest()[:12]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def data_dir(phash):
    d = NAPOLEON_DIR / "projects" / phash / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_project(ddir, project_id):
    for f in sorted(ddir.glob("*.json")):
        data = json.loads(f.read_text())
        if data["id"] == project_id:
            return f, data
    return None, None


def save_project(filepath, data):
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cmd_open():
    import webbrowser
    from napoleon.serve import run, is_running, PORT
    phash = require_phash()
    if not is_running():
        run()
    url = f"http://localhost:{PORT}/#{phash}"
    webbrowser.open(url)
    print(url)


def cmd_serve(args):
    from napoleon.serve import stop, run
    if "--stop" in args:
        stop()
    elif "--fg" in args:
        run(foreground=True)
    else:
        run()


def cmd_projects(phash):
    ddir = data_dir(phash)
    files = sorted(ddir.glob("*.json"))
    if not files:
        print("No projects yet. Run 'napoleon new <id> <title>' to create one.")
        return
    for f in files:
        data = json.loads(f.read_text())
        total = len(data["tasks"])
        done = sum(1 for t in data["tasks"] if t["status"] == "completed")
        deadline = data.get("deadline", "?")
        priority = data.get("priority", "?")
        print(f"[P{priority}] {data['id']}  {data['title']}  ({done}/{total} done, deadline {deadline})")


def cmd_tasks(phash, project_id):
    ddir = data_dir(phash)
    _, data = load_project(ddir, project_id)
    if not data:
        print(f"Project '{project_id}' not found.")
        return
    for t in data["tasks"]:
        est = f"{t.get('est50', '?')}/{t.get('est90', '?')}" if t.get("est50") is not None else "unset"
        atomic = "A" if t.get("atomic") else " "
        status = t["status"][:4]
        risk = t.get("risk", "?")[0].upper()
        print(f"  [{status:4}] {atomic} {t['id']:40} {est:10} R:{risk}  {t['title']}")


def cmd_task_add(phash, project_id, title, kwargs):
    ddir = data_dir(phash)
    filepath, data = load_project(ddir, project_id)
    if not data:
        print(f"Project '{project_id}' not found.")
        return
    task_id = kwargs.get("id") or title.lower().replace(" ", "-").replace("/", "-")[:40]
    task = {
        "id": task_id,
        "title": title,
        "description": kwargs.get("description", ""),
        "status": "not_started",
        "risk": kwargs.get("risk", "low"),
        "blockedBy": [],
        "est50": kwargs.get("est50"),
        "est90": kwargs.get("est90"),
        "atomic": kwargs.get("atomic", False),
    }
    insert_idx = int(kwargs["at"]) if kwargs.get("at") is not None else len(data["tasks"])
    data["tasks"].insert(insert_idx, task)
    save_project(filepath, data)
    print(f"Added: {task_id}")


def cmd_task_update(phash, project_id, task_id, updates):
    ddir = data_dir(phash)
    filepath, data = load_project(ddir, project_id)
    if not data:
        print(f"Project '{project_id}' not found.")
        return
    for task in data["tasks"]:
        if task["id"] == task_id:
            task.update(updates)
            save_project(filepath, data)
            print(f"Updated: {task_id}")
            return
    print(f"Task '{task_id}' not found in '{project_id}'.")


def cmd_task_done(phash, project_id, task_id):
    cmd_task_update(phash, project_id, task_id, {"status": "completed"})


def cmd_task_remove(phash, project_id, task_id):
    ddir = data_dir(phash)
    filepath, data = load_project(ddir, project_id)
    if not data:
        print(f"Project '{project_id}' not found.")
        return
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) == before:
        print(f"Task '{task_id}' not found.")
        return
    save_project(filepath, data)
    print(f"Removed: {task_id}")


def cmd_project_add(phash, project_id, title, kwargs):
    ddir = data_dir(phash)
    filepath = ddir / f"{project_id}.json"
    if filepath.exists():
        print(f"Project file already exists: {filepath}")
        return
    project = {
        "id": project_id,
        "title": title,
        "description": kwargs.get("description", ""),
        "committedTo": kwargs.get("committed_to", ""),
        "deadline": kwargs.get("deadline", "2099-12-31"),
        "minimumDelivery": kwargs.get("min_delivery"),
        "priority": int(kwargs.get("priority", 99)),
        "status": "planning",
        "constraints": [],
        "unknowns": [],
        "externalDeps": [],
        "tasks": [],
    }
    save_project(filepath, project)
    print(f"Created: {project_id}")


def cmd_list_field(phash, project_id, field, action, text=None):
    ddir = data_dir(phash)
    filepath, data = load_project(ddir, project_id)
    if not data:
        print(f"Project '{project_id}' not found.")
        return
    items = data[field]
    if action == "list":
        for i, item in enumerate(items):
            print(f"  {i}: {item}")
    elif action == "add" and text:
        items.append(text)
        save_project(filepath, data)
        print(f"Added {field} #{len(items) - 1}")
    elif action == "remove" and text is not None:
        idx = int(text)
        if 0 <= idx < len(items):
            removed = items.pop(idx)
            save_project(filepath, data)
            print(f"Removed: {removed}")
        else:
            print(f"Invalid index: {idx}")


def parse_kv_args(args):
    result = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                val = args[i + 1]
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except ValueError:
                    pass
                if val == "true":
                    val = True
                elif val == "false":
                    val = False
                result[key] = val
                i += 2
            else:
                result[key] = True
                i += 1
        else:
            i += 1
    return result


def require_phash():
    phash = get_phash()
    if not phash:
        print("Not in a git repo with a remote. Run 'napoleon help' for setup instructions.", file=sys.stderr)
        sys.exit(1)
    return phash


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    if args[0] == "--version":
        print("napoleon 0.1.0")
        return

    cmd = args[0]
    rest = args[1:]

    if cmd == "serve":
        cmd_serve(rest)
    elif cmd == "open":
        cmd_open()
    elif cmd == "projects":
        cmd_projects(require_phash())
    elif cmd == "tasks" and rest:
        cmd_tasks(require_phash(), rest[0])
    elif cmd == "add" and len(rest) >= 2:
        cmd_task_add(require_phash(), rest[0], rest[1], parse_kv_args(rest[2:]))
    elif cmd == "done" and len(rest) >= 2:
        cmd_task_done(require_phash(), rest[0], rest[1])
    elif cmd == "update" and len(rest) >= 2:
        cmd_task_update(require_phash(), rest[0], rest[1], parse_kv_args(rest[2:]))
    elif cmd == "rm" and len(rest) >= 2:
        cmd_task_remove(require_phash(), rest[0], rest[1])
    elif cmd == "new" and len(rest) >= 2:
        cmd_project_add(require_phash(), rest[0], rest[1], parse_kv_args(rest[2:]))
    elif cmd == "unknowns" and len(rest) >= 2:
        cmd_list_field(require_phash(), rest[0], "unknowns", rest[1], rest[2] if len(rest) > 2 else None)
    elif cmd == "constraints" and len(rest) >= 2:
        cmd_list_field(require_phash(), rest[0], "constraints", rest[1], rest[2] if len(rest) > 2 else None)
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'napoleon help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
