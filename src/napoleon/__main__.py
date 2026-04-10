"""Napoleon CLI — personal project intelligence.

Usage:
    napoleon serve              Start the dashboard server
    napoleon serve --stop       Stop the server
    napoleon serve --fg         Run server in foreground
    napoleon register <path>    Register a project
    napoleon list               List registered projects
    napoleon projects           List projects in current session
    napoleon tasks <project>    List tasks for a project
    napoleon task-add <project> <title> [--key value ...]
    napoleon task-done <project> <task>
    napoleon task-update <project> <task> --key value [...]
    napoleon task-remove <project> <task>
    napoleon project-add <id> <title> [--key value ...]
    napoleon unknowns <project> list|add|remove [text|index]
    napoleon constraints <project> list|add|remove [text|index]
    napoleon help               Show this help
"""

import json
import os
import sys
from pathlib import Path

XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
NAPOLEON_DIR = XDG_DATA / "napoleon"


def get_phash():
    """Get project hash from --phash flag, env var, or session file."""
    args = sys.argv
    if "--phash" in args:
        idx = args.index("--phash")
        if idx + 1 < len(args):
            return args[idx + 1]
    phash = os.environ.get("NAPOLEON_PHASH")
    if phash:
        return phash
    ppid = os.environ.get("PPID") or str(os.getppid())
    session_file = Path(f"/tmp/napoleon-{ppid}")
    if session_file.exists():
        return session_file.read_text().strip()
    return None


def data_dir(phash):
    return NAPOLEON_DIR / "projects" / phash / "data"


def load_project(ddir, project_id):
    for f in sorted(ddir.glob("*.json")):
        data = json.loads(f.read_text())
        if data["id"] == project_id:
            return f, data
    return None, None


def save_project(filepath, data):
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cmd_serve(args):
    from napoleon.serve import stop, run, list_projects, register_project
    if "--stop" in args:
        stop()
    elif "--list" in args:
        list_projects()
    elif "--register" in args:
        idx = args.index("--register")
        if idx + 1 < len(args):
            register_project(args[idx + 1])
        else:
            print("Usage: napoleon serve --register <path>", file=sys.stderr)
    elif "--fg" in args:
        run(foreground=True)
    else:
        run()


def cmd_projects(phash):
    ddir = data_dir(phash)
    if not ddir.exists():
        print("No data directory. Register a project first.")
        return
    for f in sorted(ddir.glob("*.json")):
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
    ddir.mkdir(parents=True, exist_ok=True)
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
        print("No project hash. Run 'napoleon register <path>' or set NAPOLEON_PHASH.", file=sys.stderr)
        sys.exit(1)
    return phash


def main():
    args = sys.argv[1:]

    # Strip --phash <val> from args for subcommand parsing
    clean = []
    i = 0
    while i < len(args):
        if args[i] == "--phash" and i + 1 < len(args):
            i += 2
        else:
            clean.append(args[i])
            i += 1
    args = clean

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    cmd = args[0]
    rest = args[1:]

    if cmd == "serve":
        cmd_serve(rest)
    elif cmd == "register" and rest:
        from napoleon.serve import register_project, run, is_running
        if not is_running():
            run()
        register_project(rest[0])
    elif cmd == "list":
        from napoleon.serve import list_projects
        list_projects()
    elif cmd == "projects":
        cmd_projects(require_phash())
    elif cmd == "tasks" and rest:
        cmd_tasks(require_phash(), rest[0])
    elif cmd == "task-add" and len(rest) >= 2:
        cmd_task_add(require_phash(), rest[0], rest[1], parse_kv_args(rest[2:]))
    elif cmd == "task-done" and len(rest) >= 2:
        cmd_task_done(require_phash(), rest[0], rest[1])
    elif cmd == "task-update" and len(rest) >= 2:
        cmd_task_update(require_phash(), rest[0], rest[1], parse_kv_args(rest[2:]))
    elif cmd == "task-remove" and len(rest) >= 2:
        cmd_task_remove(require_phash(), rest[0], rest[1])
    elif cmd == "project-add" and len(rest) >= 2:
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
