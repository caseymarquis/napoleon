"""Napoleon — personal project intelligence. Strategy, not status.

A CLI and dashboard for managing complex projects with AI.
Break down work, estimate with confidence, track what matters.

Shorthand: nb (or napoleon if you like typing)

Getting started:
    cd my-project                       Navigate to any git repo
    nb projects new my-proj "My Project"  Create a project
    nb projects                         List projects (shows numeric IDs)
    nb projects 0 tasks add "First task"  Add a task
    nb open                             Open the dashboard

Napoleon auto-detects which repo you're in from the git remote URL.
Each repo gets its own isolated data store. Just cd into a repo and go.

Projects are referenced by number. Tasks are referenced by their
position in the list — task 0 is always what's next.

Projects:
    nb projects                         List all projects (with numbers)
    nb projects <N>                     Briefing for project N
    nb projects new <id> <title>        Create a new project
        [--deadline YYYY-MM-DD] [--priority N] [--committed-to WHO]
        [--description TEXT]

Tasks:
    nb projects <N> tasks               List tasks (numbered)
    nb projects <N> tasks add <title>   Add a task
        [--description TEXT] [--risk low|medium|high]
        [--est50 N] [--est90 N] [--atomic] [--at INDEX]
    nb projects <N> tasks <T> done      Mark task T complete
    nb projects <N> tasks <T> update    Update task T
        [--est50 N] [--est90 N] [--risk LEVEL] [--description TEXT]
        [--status STATUS] [--atomic true|false] [--title TEXT]
    nb projects <N> tasks <T> rm        Remove task T

Metadata:
    nb projects <N> unknowns            List unknowns
    nb projects <N> unknowns add <text> Add an unknown
    nb projects <N> unknowns <I> rm     Remove unknown I
    nb projects <N> constraints             List constraints
    nb projects <N> constraints add <text>  Add a constraint
    nb projects <N> constraints <I> rm      Remove constraint I

Repos:
    nb repos                            List all tracked repos with hashes

Server:
    nb serve                            Start the dashboard (daemonizes)
    nb serve --stop                     Stop the dashboard
    nb serve --fg                       Run in foreground (debugging)
    nb open                             Start server and open dashboard

Global flags:
    --repo <hash>                       Override auto-detected repo hash

Options:
    nb info                             Explain data layout and file structure
    nb help                             Show this help
    nb --version                        Show version
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
    # Write repo metadata if missing
    meta = NAPOLEON_DIR / "projects" / phash / "meta.json"
    if not meta.exists():
        try:
            url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        except Exception:
            url, name = "", phash
        meta.write_text(json.dumps({"url": url, "name": name}, indent=2) + "\n")
    return d


def load_all_projects(ddir):
    """Load all projects sorted by priority then deadline."""
    projects = []
    for f in sorted(ddir.glob("*.json")):
        data = json.loads(f.read_text())
        projects.append((f, data))
    projects.sort(key=lambda x: (x[1].get("priority", 99), x[1].get("deadline", "9999")))
    return projects


def resolve_project(ddir, index):
    """Get project by numeric index. Returns (filepath, data) or exits."""
    projects = load_all_projects(ddir)
    if index < 0 or index >= len(projects):
        print(f"Project {index} not found. Run 'napoleon projects' to see available projects.", file=sys.stderr)
        sys.exit(1)
    return projects[index]


def resolve_task(data, index):
    """Get task by numeric index. Returns task dict or exits."""
    if index < 0 or index >= len(data["tasks"]):
        print(f"Task {index} not found. Run 'napoleon projects <N> tasks' to see tasks.", file=sys.stderr)
        sys.exit(1)
    return data["tasks"][index]


def save_project(filepath, data):
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ── Commands ──

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
    projects = load_all_projects(ddir)
    if not projects:
        print("No projects yet. Run 'napoleon projects new <id> <title>' to create one.")
        return
    for i, (f, data) in enumerate(projects):
        total = len(data["tasks"])
        done = sum(1 for t in data["tasks"] if t["status"] == "completed")
        deadline = data.get("deadline")
        dl_str = f", deadline {deadline}" if deadline else ""
        print(f"  {i}  {data['title']}  ({done}/{total} done{dl_str})")


def cmd_project_show(phash, project_idx):
    """Context-rich briefing for a project."""
    from datetime import datetime, date

    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    tasks = data["tasks"]
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "completed")
    in_progress = [(i, t) for i, t in enumerate(tasks) if t["status"] == "in_progress"]
    not_started = [(i, t) for i, t in enumerate(tasks) if t["status"] == "not_started"]

    # Header
    print(f"  [{project_idx}] {data['title']}")
    if data.get("description"):
        print(f"  {data['description']}")
    print()

    # Deadline
    if data.get("deadline"):
        try:
            dl = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
            days_left = (dl - date.today()).days
            urgency = "OVERDUE" if days_left < 0 else f"{days_left}d left"
            print(f"  Deadline:  {data['deadline']} ({urgency})")
        except ValueError:
            print(f"  Deadline:  {data['deadline']}")

    # Progress
    print(f"  Progress:  {done}/{total} tasks done")

    # Estimates
    remaining = [t for t in tasks if t["status"] != "completed"]
    est50_total = sum(t.get("est50") or 0 for t in remaining)
    est90_total = sum(t.get("est90") or 0 for t in remaining)
    unestimated = sum(1 for t in remaining if t.get("est50") is None)
    if remaining:
        est_str = f"{est50_total:.1f}d / {est90_total:.1f}d remaining"
        if unestimated:
            est_str += f" ({unestimated} unestimated)"
        print(f"  Estimate:  {est_str}")
    print()

    # What's happening now
    if in_progress:
        print("  In progress:")
        for i, t in in_progress:
            print(f"    [{i}] {t['title']}")
        print()

    # What's next
    if not_started:
        i, nxt = not_started[0]
        print(f"  Next up:   [{i}] {nxt['title']}")
        if nxt.get("description"):
            print(f"             {nxt['description']}")
        print()

    # Warnings
    warnings = []
    if unestimated:
        warnings.append(f"{unestimated} task(s) have no estimates")
    high_risk = [t for t in remaining if t.get("risk") == "high"]
    if high_risk:
        warnings.append(f"{len(high_risk)} high-risk task(s)")
    if data.get("unknowns"):
        warnings.append(f"{len(data['unknowns'])} open unknown(s)")
    not_atomic = [t for t in remaining if not t.get("atomic")]
    if not_atomic:
        warnings.append(f"{len(not_atomic)} task(s) not yet atomic (may need breakdown)")

    if warnings:
        print("  Warnings:")
        for w in warnings:
            print(f"    ! {w}")
        print()


def cmd_tasks(phash, project_idx):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    if not data["tasks"]:
        print("  No tasks.")
        return
    title_w = max(len(t["title"]) for t in data["tasks"])
    title_w = min(title_w, 50)
    print(f"  {'#':>3}  {'Status':<12} {'Est50':>5} {'Est90':>5}  {'Risk':<6} Title")
    print(f"  {'---':>3}  {'-'*12} {'-'*5} {'-'*5}  {'-'*6} {'-'*20}")
    for i, t in enumerate(data["tasks"]):
        status = t["status"].replace("_", " ")
        est50 = str(t["est50"]) if t.get("est50") is not None else "-"
        est90 = str(t["est90"]) if t.get("est90") is not None else "-"
        risk = t.get("risk", "-")
        atomic = " [atomic]" if t.get("atomic") else ""
        print(f"  {i:>3}  {status:<12} {est50:>5} {est90:>5}  {risk:<6} {t['title']}{atomic}")


def cmd_task_add(phash, project_idx, title, kwargs):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    task_id = title.lower().replace(" ", "-").replace("/", "-")[:40]
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
    print(f"Added task {insert_idx}: {title}")


def cmd_task_update(phash, project_idx, task_idx, updates):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    task = resolve_task(data, task_idx)
    task.update(updates)
    save_project(filepath, data)
    print(f"Updated task {task_idx}: {task['title']}")


def cmd_task_done(phash, project_idx, task_idx):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    task = resolve_task(data, task_idx)
    task["status"] = "completed"
    save_project(filepath, data)
    print(f"Done: {task['title']}")


def cmd_task_remove(phash, project_idx, task_idx):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    task = resolve_task(data, task_idx)
    data["tasks"].pop(task_idx)
    save_project(filepath, data)
    print(f"Removed task {task_idx}: {task['title']}")


def cmd_project_new(phash, project_id, title, kwargs):
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
        "deadline": kwargs.get("deadline"),
        "minimumDelivery": kwargs.get("min_delivery"),
        "priority": int(kwargs.get("priority", 99)),
        "status": "planning",
        "constraints": [],
        "unknowns": [],
        "externalDeps": [],
        "tasks": [],
    }
    save_project(filepath, project)
    print(f"Created: {title} ({project_id})")


def cmd_list_field(phash, project_idx, field):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    items = data[field]
    if not items:
        print(f"  No {field}.")
        return
    for i, item in enumerate(items):
        print(f"  {i}: {item}")


def cmd_add_field(phash, project_idx, field, text):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    data[field].append(text)
    save_project(filepath, data)
    print(f"Added {field[:-1]} {len(data[field]) - 1}: {text}")


def cmd_rm_field(phash, project_idx, field, item_idx):
    ddir = data_dir(phash)
    filepath, data = resolve_project(ddir, project_idx)
    items = data[field]
    if item_idx < 0 or item_idx >= len(items):
        print(f"Invalid index: {item_idx}")
        return
    removed = items.pop(item_idx)
    save_project(filepath, data)
    print(f"Removed: {removed}")


def cmd_info():
    """Explain the data structure and file layout."""
    phash = get_phash()
    print(f"""Napoleon data layout
====================

Root:       {NAPOLEON_DIR}
Projects:   {NAPOLEON_DIR}/projects/<hash>/
Server PID: {NAPOLEON_DIR}/server.pid
Dashboard:  http://localhost:8150

Each git remote URL is hashed (MD5, first 12 chars) to create a project
directory. Inside each:

  projects/<hash>/
    meta.json              Repo metadata: {{"url": "...", "name": "..."}}
    data/<project-id>.json One file per project

Current repo hash: {phash or '(not in a git repo)'}
Current data dir:  {data_dir(phash) if phash else '(n/a)'}

Project JSON structure:
  id, title, description, committedTo, deadline, priority,
  minimumDelivery, status, constraints[], unknowns[],
  externalDeps[{{description, resolved, resolvedDate}}],
  tasks[{{id, title, description, status, risk, blockedBy[],
          est50, est90, atomic}}]

Task statuses: not_started, in_progress, completed
  (blocked is auto-calculated from blockedBy in the dashboard)

Available hashes:""")
    projects_root = NAPOLEON_DIR / "projects"
    if projects_root.exists():
        for d in sorted(projects_root.iterdir()):
            if not d.is_dir():
                continue
            meta_file = d / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    label = meta.get("name", d.name)
                    url = meta.get("url", "")
                    print(f"  {d.name}  {label}" + (f"  ({url})" if url else ""))
                except Exception:
                    print(f"  {d.name}  (meta.json unreadable)")
            else:
                print(f"  {d.name}  (no meta.json)")
    else:
        print("  (none)")


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


def cmd_repos():
    """List all known repos with metadata."""
    projects_root = NAPOLEON_DIR / "projects"
    if not projects_root.exists():
        print("No repos tracked yet.")
        return
    dirs = sorted(d for d in projects_root.iterdir() if d.is_dir())
    if not dirs:
        print("No repos tracked yet.")
        return
    for d in dirs:
        meta_file = d / "meta.json"
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
            except Exception:
                pass
        name = meta.get("name", d.name)
        url = meta.get("url", "")
        data_path = d / "data"
        project_count = len(list(data_path.glob("*.json"))) if data_path.exists() else 0
        print(f"  {d.name}  {name}")
        if url:
            print(f"           {url}")
        print(f"           {project_count} project(s)  {data_path}")
        print()


def main():
    args = sys.argv[1:]

    # Extract --repo flag before anything else
    repo_override = None
    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo_override = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

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
        return
    elif cmd == "open":
        cmd_open()
        return
    elif cmd == "info":
        cmd_info()
        return
    elif cmd == "repos":
        cmd_repos()
        return

    if cmd != "projects":
        print(f"Unknown command: {cmd}")
        print("Run 'napoleon help' for usage.")
        sys.exit(1)

    phash = repo_override or require_phash()

    # napoleon projects ...
    if not rest:
        cmd_projects(phash)
        return

    # napoleon projects new <id> <title> [--flags]
    if rest[0] == "new":
        if len(rest) < 3:
            print("Usage: napoleon projects new <id> <title> [--flags]")
            sys.exit(1)
        cmd_project_new(phash, rest[1], rest[2], parse_kv_args(rest[3:]))
        return

    # napoleon projects <N> ...
    try:
        project_idx = int(rest[0])
    except ValueError:
        print(f"Expected project number, got: {rest[0]}")
        print("Run 'napoleon projects' to see available projects.")
        sys.exit(1)

    rest = rest[1:]

    if not rest:
        # napoleon projects <N>
        cmd_project_show(phash, project_idx)
        return

    subcmd = rest[0]
    rest = rest[1:]

    if subcmd == "tasks":
        if not rest:
            # napoleon projects <N> tasks
            cmd_tasks(phash, project_idx)
            return

        if rest[0] == "add":
            # napoleon projects <N> tasks add <title> [--flags]
            if len(rest) < 2:
                print("Usage: napoleon projects <N> tasks add <title> [--flags]")
                sys.exit(1)
            cmd_task_add(phash, project_idx, rest[1], parse_kv_args(rest[2:]))
            return

        # napoleon projects <N> tasks <T> ...
        try:
            task_idx = int(rest[0])
        except ValueError:
            print(f"Expected task number, got: {rest[0]}")
            sys.exit(1)

        rest = rest[1:]

        if not rest:
            # napoleon projects <N> tasks <T> — could show task detail
            print("Specify an action: done, update, rm")
            sys.exit(1)

        action = rest[0]
        if action == "done":
            cmd_task_done(phash, project_idx, task_idx)
        elif action == "rm":
            cmd_task_remove(phash, project_idx, task_idx)
        elif action == "update":
            cmd_task_update(phash, project_idx, task_idx, parse_kv_args(rest[1:]))
        else:
            print(f"Unknown task action: {action}")
            sys.exit(1)

    elif subcmd in ("unknowns", "constraints"):
        if not rest:
            # napoleon projects <N> unknowns
            cmd_list_field(phash, project_idx, subcmd)
            return

        if rest[0] == "add":
            if len(rest) < 2:
                print(f"Usage: napoleon projects <N> {subcmd} add <text>")
                sys.exit(1)
            cmd_add_field(phash, project_idx, subcmd, rest[1])
            return

        # napoleon projects <N> unknowns <I> rm
        try:
            item_idx = int(rest[0])
        except ValueError:
            print(f"Expected index or 'add', got: {rest[0]}")
            sys.exit(1)

        if len(rest) >= 2 and rest[1] == "rm":
            cmd_rm_field(phash, project_idx, subcmd, item_idx)
        else:
            print(f"Usage: napoleon projects <N> {subcmd} <I> rm")
            sys.exit(1)

    else:
        print(f"Unknown subcommand: {subcmd}")
        print("Available: tasks, unknowns, constraints")
        sys.exit(1)


if __name__ == "__main__":
    main()
