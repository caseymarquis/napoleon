# My Process

## Repo Structure

Napoleon lives at `/home/casey/code/napoleon/`. It's a haiv project — orphan branch for mind state, main branch for code.

```
/home/casey/code/napoleon/              # haiv-hq (orphan branch)
├── CLAUDE.md
├── src/haiv_project/commands/          # haiv commands (e.g. napoleon_sync)
├── users/casey/state/minds/napoleon/   # my mind files
└── worktrees/main/                     # main branch = the actual code
    ├── .gitignore
    ├── pyproject.toml                  # Python package (editable install)
    ├── src/napoleon/                   # CLI + server + dashboard
    │   ├── __main__.py                 # CLI entry point + all commands
    │   ├── serve.py                    # Dashboard server (daemonizes)
    │   └── dashboard/                  # HTML/JS frontend
    │       ├── index.html              # Tab shell, shared CSS, data layer
    │       ├── overview.js             # Capacity, next-up, readiness
    │       └── planning.js             # Single-project focus, inline editing
    ├── .claude-plugin/marketplace.json
    └── plugins/napoleon/               # Thin Claude Code plugin shell
        ├── .claude-plugin/plugin.json
        └── commands/napoleon.md

GitHub: https://github.com/caseymarquis/napoleon
```

## How it works

**Two deliverables, one repo:**
1. **Python package** — `uv tool install --editable .` puts `napoleon` on PATH. The real tool.
2. **Claude Code plugin** — thin shell for `/napoleon` slash command. Installs the package.

**Project detection:** Hash of `git remote get-url origin`. No registration, no config. `cd` into a repo and go.

**Data isolation:** `~/.local/share/napoleon/projects/<hash>/data/` — one JSON file per project per repo.

## Development Workflow

**Editable install** — changes to source take effect immediately:
```bash
cd /home/casey/code/napoleon/worktrees/main
uv tool install --editable .
```

**Test:**
```bash
napoleon help
napoleon projects
napoleon open
```

**Push:**
```bash
cd /home/casey/code/napoleon/worktrees/main && git add -A && git commit -m "description" && git push origin main
```

**Plugin sync** (only needed for plugin command changes):
```bash
hv napoleon_sync
/reload-plugins
```

## CLI Reference

```
napoleon open                       Start server + open dashboard in browser
napoleon serve [--stop|--fg]        Manage the dashboard server
napoleon projects                   List projects in current repo
napoleon tasks <project>            List tasks
napoleon add <project> <title>      Add a task [--id --description --risk --est50 --est90 --atomic --at]
napoleon done <project> <task>      Mark complete
napoleon update <project> <task>    Update fields [--est50 --est90 --risk --status --atomic --description]
napoleon rm <project> <task>        Remove a task
napoleon new <id> <title>           Create a project [--deadline --priority --committed-to --description]
napoleon unknowns <project> list|add|remove [text|index]
napoleon constraints <project> list|add|remove [text|index]
napoleon help                       Show full help
napoleon --version                  Show version
```

## Dashboard

Port **8150**. URL: `http://localhost:8150/#<hash>`

**Two tabs:**
- **Overview** — capacity timeline, next-up per project, readiness scores, collapsible project details
- **Planning** — single-project focus, inline est50/est90 editing, atomic checkboxes, gaps analysis, critical path

**Auto-refresh:** Polls every 2s. Data changes soft-refresh. JS/CSS changes trigger full reload. Server restart detected automatically.
